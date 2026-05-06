from __future__ import annotations

import asyncio
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from src.schemas.agent import AgentCitation, AgentFallback
from src.services.agent_graph_contracts import ToolResult


@dataclass(frozen=True)
class ExternalResearchDocument:
    title: str
    url: str
    snippet: str
    source: str


class AgentExternalResearchService:
    def __init__(self, *, timeout_s: float = 8.0, max_retries: int = 2, responder=None):
        self.timeout_s = timeout_s
        self.max_retries = max(1, max_retries)
        self.responder = responder

    async def answer(self, *, message: str, recent_messages: list[dict] | None = None) -> ToolResult:
        queries = self._plan_queries(message)
        documents = await self._act(queries)
        observed = self._observe(message, documents)
        return self._respond(message, observed, recent_messages or [])

    def _plan_queries(self, message: str) -> list[str]:
        normalized = re.sub(r"\s+", " ", message).strip()
        if not normalized:
            return []
        cleaned = re.sub(
            r"^(explain|find|search|look up|what is|giải thích|tìm|tìm kiếm)\s+",
            "",
            normalized,
            flags=re.IGNORECASE,
        ).strip(" ?.")
        queries = [normalized]
        if cleaned and cleaned.lower() != normalized.lower():
            queries.append(cleaned)
        return list(dict.fromkeys(queries))[:2]

    async def _act(self, queries: list[str]) -> list[ExternalResearchDocument]:
        if not queries:
            return []
        tasks = []
        for query in queries:
            tasks.append(self._with_retry(lambda q=query: self._search_web(q)))
            tasks.append(self._with_retry(lambda q=query: self._search_papers(q)))
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        documents: list[ExternalResearchDocument] = []
        seen: set[str] = set()
        for response in responses:
            if isinstance(response, Exception):
                continue
            for document in response:
                key = document.url or document.title
                if key in seen:
                    continue
                seen.add(key)
                documents.append(document)
        return documents

    async def _with_retry(self, operation):
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                return await operation()
            except Exception as exc:  # pragma: no cover - exercised by integration/runtime failures
                last_error = exc
                if attempt + 1 < self.max_retries:
                    await asyncio.sleep(0.2 * (attempt + 1))
        if last_error is not None:
            raise last_error
        return []

    async def _search_web(self, query: str) -> list[ExternalResearchDocument]:
        payload = await asyncio.to_thread(
            self._fetch_json,
            "https://api.duckduckgo.com/?"
            + urlencode(
                {
                "q": query,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1",
                }
            ),
        )
        documents: list[ExternalResearchDocument] = []
        title = str(payload.get("Heading") or "").strip()
        snippet = str(payload.get("AbstractText") or "").strip()
        url = str(payload.get("AbstractURL") or "").strip()
        if title and snippet and url:
            documents.append(ExternalResearchDocument(title=title, url=url, snippet=snippet, source="web"))
        for topic in payload.get("RelatedTopics") or []:
            if "Topics" in topic:
                nested = topic.get("Topics") or []
            else:
                nested = [topic]
            for item in nested:
                text = str(item.get("Text") or "").strip()
                first_url = str(item.get("FirstURL") or "").strip()
                if text and first_url:
                    documents.append(
                        ExternalResearchDocument(
                            title=text.split(" - ", 1)[0][:120],
                            url=first_url,
                            snippet=text,
                            source="web",
                        )
                    )
                if len(documents) >= 4:
                    return documents
        return documents

    async def _search_papers(self, query: str) -> list[ExternalResearchDocument]:
        text = await asyncio.to_thread(
            self._fetch_text,
            f"https://export.arxiv.org/api/query?search_query=all:{quote_plus(query)}&start=0&max_results=4",
        )
        root = ET.fromstring(text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        documents: list[ExternalResearchDocument] = []
        for entry in root.findall("atom:entry", ns):
            title = self._xml_text(entry.find("atom:title", ns))
            summary = self._xml_text(entry.find("atom:summary", ns))
            link = self._xml_text(entry.find("atom:id", ns))
            if title and link:
                documents.append(
                    ExternalResearchDocument(
                        title=title,
                        url=link,
                        snippet=summary,
                        source="paper",
                    )
                )
        return documents

    def _fetch_json(self, url: str) -> dict:
        return json.loads(self._fetch_text(url))

    def _fetch_text(self, url: str) -> str:
        request = Request(url, headers={"User-Agent": "AI-Learning-Copilot/1.0"})
        with urlopen(request, timeout=self.timeout_s) as response:
            return response.read().decode("utf-8", errors="replace")

    def _observe(self, message: str, documents: list[ExternalResearchDocument]) -> list[ExternalResearchDocument]:
        tokens = {
            token
            for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{2,}", message.lower())
            if token not in {"explain", "search", "find", "about", "what", "papers"}
        }

        def score(document: ExternalResearchDocument) -> tuple[int, int]:
            text = f"{document.title} {document.snippet}".lower()
            token_hits = sum(1 for token in tokens if token in text)
            source_bonus = 1 if document.source == "paper" else 0
            return token_hits, source_bonus

        ranked = sorted(documents, key=score, reverse=True)
        return ranked[:6]

    def _respond(
        self,
        message: str,
        documents: list[ExternalResearchDocument],
        recent_messages: list[dict],
    ) -> ToolResult:
        if not documents:
            return ToolResult(
                kind="find_content",
                answer_markdown="I could not find reliable web or paper sources for that request.",
                citations=[],
                fallback=AgentFallback(
                    reason="no_external_sources",
                    message="Web and paper search returned no usable sources.",
                ),
                requires_evidence=True,
                metadata={"tool_mode": "web_papers", "pipeline": ["plan", "act", "observe", "respond"]},
            )
        citations = self._citations(documents)
        synthesized_answer = self._synthesize_answer(
            message=message,
            documents=documents,
            citations=citations,
            recent_messages=recent_messages,
        )
        if synthesized_answer:
            synthesized_answer = self._with_numeric_source_links(synthesized_answer, citations)
            return ToolResult(
                kind="find_content",
                answer_markdown=synthesized_answer,
                citations=citations,
                requires_evidence=False,
                metadata={
                    "tool_mode": "web_papers",
                    "answer_confidence": "grounded",
                    "pipeline": ["plan", "act", "observe", "respond"],
                    "external_source_count": len(documents),
                    "response_synthesized": True,
                },
            )
        source_lines = [
            f"{index}. **{document.title}** ({'paper' if document.source == 'paper' else 'web'}): "
            f"{self._shorten(document.snippet)}"
            for index, document in enumerate(documents[:4], start=1)
        ]
        return ToolResult(
            kind="find_content",
            answer_markdown=(
                f"I searched web and paper sources for: **{message.strip()}**\n\n"
                "Most relevant evidence:\n"
                + "\n".join(source_lines)
                + "\n\nUse the source cards to inspect the original source before relying on it."
            ),
            citations=citations,
            requires_evidence=False,
            metadata={
                "tool_mode": "web_papers",
                "answer_confidence": "grounded",
                "pipeline": ["plan", "act", "observe", "respond"],
                "external_source_count": len(documents),
                "response_synthesized": False,
            },
        )

    def _citations(self, documents: list[ExternalResearchDocument]) -> list[AgentCitation]:
        return [
            AgentCitation(
                canonical_unit_id=f"external::{document.source}::{index}",
                course_id="PAPER" if document.source == "paper" else "WEB",
                unit_name=document.title,
                lecture_title="External paper" if document.source == "paper" else "Web source",
                learn_href=document.url,
                quote=document.snippet[:700],
                source=document.source,
            )
            for index, document in enumerate(documents[:5], start=1)
        ]

    def _synthesize_answer(
        self,
        *,
        message: str,
        documents: list[ExternalResearchDocument],
        citations: list[AgentCitation],
        recent_messages: list[dict],
    ) -> str | None:
        responder = self.responder
        rag_respond = getattr(responder, "rag_respond", None)
        if rag_respond is None:
            return None
        observation = {
            "tool": "search_web_papers",
            "success": True,
            "evidence_status": "grounded",
            "result": {
                "kind": "find_content",
                "external_sources": [
                    {
                        "title": document.title,
                        "source": document.source,
                        "url": document.url,
                        "snippet": self._shorten(document.snippet, limit=900),
                    }
                    for document in documents[:6]
                ],
                "citations": [citation.model_dump(mode="json") for citation in citations],
            },
        }
        base_thought = {
            "user_goal": message,
            "evidence_need": "external_web_and_papers",
            "tool_plan": ["search_web", "search_papers", "synthesize_answer"],
            "answer_requirements": (
                "Produce a complete user-facing answer before the backend appends sources. "
                "Prefer 2-4 short paragraphs or 3-5 complete bullets. Do not use a numbered "
                "section heading unless the answer contains more than one numbered section."
            ),
        }
        final = rag_respond(
            message=message,
            thought=base_thought,
            observations=[observation],
            route_context=None,
            recent_messages=recent_messages,
        )
        answer = str(getattr(final, "answer_markdown", "") or "").strip()
        if self._looks_like_incomplete_synthesis(answer):
            retry_final = rag_respond(
                message=message,
                thought={
                    **base_thought,
                    "quality_retry": "complete_external_answer",
                    "previous_draft": answer,
                    "retry_instruction": (
                        "The previous draft looked truncated or like an unfinished outline. "
                        "Rewrite it as a complete answer and finish the explanation before sources."
                    ),
                },
                observations=[observation],
                route_context=None,
                recent_messages=recent_messages,
            )
            retry_answer = str(getattr(retry_final, "answer_markdown", "") or "").strip()
            if retry_answer:
                answer = retry_answer
        if not answer:
            return None
        return answer

    def _looks_like_incomplete_synthesis(self, answer: str) -> bool:
        cleaned = re.sub(r"\s*\[\^[^\]]+\]", "", answer).strip()
        if not cleaned:
            return False
        word_count = len(re.findall(r"\w+", cleaned, flags=re.UNICODE))
        has_first_heading = re.search(r"(?m)^\s*1[.)]\s+\S", cleaned) is not None
        has_second_heading = re.search(r"(?m)^\s*2[.)]\s+\S", cleaned) is not None
        if has_first_heading and not has_second_heading and word_count < 160:
            return True
        if word_count < 70 and cleaned.endswith((",", ":", ";", "và", "hoặc", "and", "or")):
            return True
        return False

    def _with_numeric_source_links(self, answer: str, citations: list[AgentCitation]) -> str:
        cleaned = re.sub(r"\s*\[\^[^\]]+\]", "", answer).strip()
        links = []
        for index, citation in enumerate(citations[:5], start=1):
            if citation.learn_href:
                title = self._markdown_link_label(f"{index}. {citation.unit_name}")
                links.append(f"[{title}]({citation.learn_href})")
        if not links:
            return cleaned
        if any(f"[{index}](" in cleaned for index in range(1, len(links) + 1)):
            return cleaned
        return f"{cleaned}\n\nSources: {' | '.join(links)}"

    @staticmethod
    def _markdown_link_label(value: str) -> str:
        cleaned = re.sub(r"\s+", " ", value).strip()
        return cleaned.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")

    @staticmethod
    def _xml_text(element) -> str:
        if element is None or element.text is None:
            return ""
        return re.sub(r"\s+", " ", element.text).strip()

    @staticmethod
    def _shorten(value: str, limit: int = 260) -> str:
        cleaned = re.sub(r"\s+", " ", value).strip()
        if len(cleaned) <= limit:
            return cleaned
        return f"{cleaned[: limit - 3].rstrip()}..."
