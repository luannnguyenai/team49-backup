from __future__ import annotations

import asyncio
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from urllib.parse import quote_plus

import httpx

from src.schemas.agent import AgentCitation, AgentFallback
from src.services.agent_graph_contracts import ToolResult


@dataclass(frozen=True)
class ExternalResearchDocument:
    title: str
    url: str
    snippet: str
    source: str


class AgentExternalResearchService:
    def __init__(self, *, timeout_s: float = 8.0, max_retries: int = 2):
        self.timeout_s = timeout_s
        self.max_retries = max(1, max_retries)

    async def answer(self, *, message: str, recent_messages: list[dict] | None = None) -> ToolResult:
        queries = self._plan_queries(message)
        documents = await self._act(queries)
        observed = self._observe(message, documents)
        return self._respond(message, observed)

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
        async with httpx.AsyncClient(timeout=self.timeout_s, follow_redirects=True) as client:
            tasks = []
            for query in queries:
                tasks.append(self._with_retry(lambda q=query: self._search_web(client, q)))
                tasks.append(self._with_retry(lambda q=query: self._search_papers(client, q)))
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

    async def _search_web(self, client: httpx.AsyncClient, query: str) -> list[ExternalResearchDocument]:
        response = await client.get(
            "https://api.duckduckgo.com/",
            params={
                "q": query,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1",
            },
        )
        response.raise_for_status()
        payload = response.json()
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

    async def _search_papers(self, client: httpx.AsyncClient, query: str) -> list[ExternalResearchDocument]:
        response = await client.get(
            f"https://export.arxiv.org/api/query?search_query=all:{quote_plus(query)}&start=0&max_results=4"
        )
        response.raise_for_status()
        root = ET.fromstring(response.text)
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

    def _respond(self, message: str, documents: list[ExternalResearchDocument]) -> ToolResult:
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
        citations = [
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
            },
        )

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
