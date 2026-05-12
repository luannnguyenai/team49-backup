from __future__ import annotations

import asyncio
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from urllib.parse import quote_plus, urlencode
from urllib.request import Request, urlopen

from src.schemas.agent import AgentCitation, AgentFallback
from src.services.agent_external_citation_manager import ExternalCitationManager
from src.services.agent_graph_contracts import ToolResult


@dataclass(frozen=True)
class ExternalResearchDocument:
    title: str
    url: str
    snippet: str
    source: str


@dataclass(frozen=True)
class SearchPlan:
    tools: tuple[str, ...]
    queries: tuple[str, ...]


class AgentExternalResearchService:
    def __init__(self, *, timeout_s: float = 8.0, max_retries: int = 2, responder=None):
        self.timeout_s = timeout_s
        self.max_retries = max(1, max_retries)
        self.responder = responder
        self.citation_manager = ExternalCitationManager()

    async def answer(
        self, *, message: str, recent_messages: list[dict] | None = None
    ) -> ToolResult:
        plan = self._plan_search(message)
        documents = await self._act(plan)
        observed = self._observe(message, documents)
        return self._respond(message, observed, recent_messages or [], plan=plan)

    def _plan_search(self, message: str) -> SearchPlan:
        queries = tuple(self._plan_queries(message))
        if not queries:
            return SearchPlan(tools=(), queries=())
        return SearchPlan(tools=self._select_tools(message), queries=queries)

    def _plan_queries(self, message: str) -> list[str]:
        normalized = re.sub(r"\s+", " ", message).strip()
        if not normalized:
            return []
        cleaned = self._clean_query(normalized)
        queries = [cleaned]
        if normalized.casefold() != cleaned.casefold() and not self._looks_like_noisy_query(
            normalized
        ):
            queries.append(normalized)
        return list(dict.fromkeys(queries))[:2]

    def _select_tools(self, message: str) -> tuple[str, ...]:
        lowered = message.casefold()
        wants_web = re.search(r"\b(web|website|internet|online|news)\b", lowered) is not None
        wants_paper = re.search(
            r"\b(arxiv|paper|papers|publication|publications|research|survey|literature)\b",
            lowered,
        ) is not None or any(
            phrase in lowered
            for phrase in ("bài báo", "nghiên cứu", "khảo sát", "tài liệu học thuật")
        )
        if wants_web and wants_paper:
            return ("web", "paper")
        if wants_paper:
            return ("paper",)
        return ("web",)

    def _clean_query(self, message: str) -> str:
        cleaned = message.strip(" ?.")
        for _ in range(3):
            previous = cleaned
            cleaned = re.sub(
                r"^(please\s+)?(explain|find|search|look up|what is|tell me about|"
                r"give me information about|giải thích|tìm kiếm|tìm)\s+",
                "",
                cleaned,
                flags=re.IGNORECASE,
            ).strip(" ?.")
            cleaned = re.sub(
                r"^(web\s+and\s+papers?|papers?\s+and\s+web|arxiv\s+papers?|"
                r"papers?|publications?|research|survey|literature|web|online)"
                r"(\s+(about|on|for|về))?\s+",
                "",
                cleaned,
                flags=re.IGNORECASE,
            ).strip(" ?.")
            cleaned = re.sub(
                r"^(thông tin|nội dung|kiến thức|bài báo|papers?|information|content)"
                r"(\s+(về|about))?\s+",
                "",
                cleaned,
                flags=re.IGNORECASE,
            ).strip(" ?.")
            cleaned = re.sub(r"^(về|about)\s+", "", cleaned, flags=re.IGNORECASE).strip(" ?.")
            if cleaned == previous:
                break
        return cleaned or message.strip(" ?.")

    def _looks_like_noisy_query(self, query: str) -> bool:
        lowered = query.casefold()
        return any(
            phrase in lowered
            for phrase in (
                "thông tin",
                "nội dung",
                "kiến thức",
                "tìm ",
                "tìm kiếm",
                "arxiv",
                "paper",
                "papers",
                "publication",
                "publications",
                "research",
                "survey",
                "literature",
                "web",
                "online",
            )
        )

    async def _act(self, plan: SearchPlan) -> list[ExternalResearchDocument]:
        if not plan.queries or not plan.tools:
            return []
        tasks = []
        for query in plan.queries:
            if "web" in plan.tools:
                tasks.append(self._with_retry(lambda q=query: self._search_web(q)))
            if "paper" in plan.tools:
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
            documents.append(
                ExternalResearchDocument(title=title, url=url, snippet=snippet, source="web")
            )
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

    def _observe(
        self, message: str, documents: list[ExternalResearchDocument]
    ) -> list[ExternalResearchDocument]:
        return list(self.citation_manager.select_sources(documents))

    def _respond(
        self,
        message: str,
        documents: list[ExternalResearchDocument],
        recent_messages: list[dict],
        *,
        plan: SearchPlan | None = None,
    ) -> ToolResult:
        pipeline = ["plan", "search", "consolidate", "respond"]
        if not documents:
            return ToolResult(
                kind="find_content",
                answer_markdown="I could not find reliable web or paper sources for that request.",
                citations=[],
                fallback=AgentFallback(
                    reason="no_retrieval_result",
                    message="Web and paper search returned no usable sources.",
                ),
                requires_evidence=True,
                metadata={
                    "tool_mode": "web_papers",
                    "pipeline": pipeline,
                    "selected_tools": list(plan.tools) if plan else [],
                },
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
                    "pipeline": pipeline,
                    "selected_tools": list(plan.tools) if plan else [],
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
            answer_markdown=self._with_numeric_source_links(
                (
                    f"I searched web and paper sources for: **{message.strip()}**\n\n"
                    "Most relevant evidence:\n"
                    + "\n".join(source_lines)
                    + "\n\nUse the linked sources below to inspect the original material before relying on it."
                ),
                citations,
            ),
            citations=citations,
            requires_evidence=False,
            metadata={
                "tool_mode": "web_papers",
                "answer_confidence": "grounded",
                "pipeline": pipeline,
                "selected_tools": list(plan.tools) if plan else [],
                "external_source_count": len(documents),
                "response_synthesized": False,
            },
        )

    def _citations(self, documents: list[ExternalResearchDocument]) -> list[AgentCitation]:
        return self.citation_manager.build_citations(documents)

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
                        "source_index": index,
                        "title": document.title,
                        "source": document.source,
                        "url": document.url,
                        "snippet": self._shorten(document.snippet, limit=900),
                    }
                    for index, document in enumerate(documents[:6], start=1)
                ],
                "citations": [citation.model_dump(mode="json") for citation in citations],
            },
        }
        base_thought = {
            "user_goal": message,
            "evidence_need": "external_web_and_papers",
            "tool_plan": ["search_web_or_papers", "consolidate_sources", "synthesize_answer"],
            "answer_requirements": (
                "Produce a complete user-facing answer before the backend appends sources. "
                "Prefer 2-4 short paragraphs or 3-5 complete bullets. Do not use a numbered "
                "section heading unless the answer contains more than one numbered section. "
                "When a claim comes from an external source, cite it with bracketed source "
                "numbers like [1] or [2]. Use only citation numbers that appear in the provided "
                "citations list and match source_index exactly. Every answer using external "
                "sources must include at least one inline citation marker in [N] format. "
                "Do not write raw URLs or a Sources section."
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
        return self.citation_manager.render_answer(answer, citations)

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
