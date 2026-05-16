from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import ClassVar
from urllib.parse import parse_qs, quote_plus, unquote, urlencode, urlsplit
from urllib.request import Request, urlopen

from src.config import settings
from src.schemas.agent import AgentCitation, AgentFallback
from src.services.agent_external_citation_manager import ExternalCitationManager
from src.services.agent_graph_contracts import ToolResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExternalResearchDocument:
    title: str
    url: str
    snippet: str
    source: str
    citation_count: int | None = None
    year: int | None = None
    authors: tuple[str, ...] = field(default_factory=tuple)
    venue: str | None = None
    doi: str | None = None


@dataclass(frozen=True)
class SearchPlan:
    tools: tuple[str, ...]
    queries: tuple[str, ...]


class _DuckDuckGoHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._capture: str | None = None
        self._href = ""
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        if tag != "a":
            return
        attr_map = {name: value or "" for name, value in attrs}
        classes = set(attr_map.get("class", "").split())
        if "result__a" in classes:
            self._capture = "title"
            self._href = attr_map.get("href", "")
            self._text_parts = []
        elif "result__snippet" in classes:
            self._capture = "snippet"
            self._text_parts = []

    def handle_data(self, data: str):
        if self._capture:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str):
        if tag != "a" or not self._capture:
            return
        text = re.sub(r"\s+", " ", "".join(self._text_parts)).strip()
        if self._capture == "title" and text and self._href:
            self.results.append({"title": text, "url": self._href, "snippet": ""})
        elif self._capture == "snippet" and text and self.results:
            self.results[-1]["snippet"] = text
        self._capture = None
        self._href = ""
        self._text_parts = []


class AgentExternalResearchService:
    _semantic_scholar_lock: ClassVar[asyncio.Lock] = asyncio.Lock()
    _semantic_scholar_last_request_at: ClassVar[float] = 0.0

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
        tools = self._select_tools(message)
        queries = tuple(self._plan_queries(message, tools=tools))
        if not queries:
            return SearchPlan(tools=(), queries=())
        return SearchPlan(tools=tools, queries=queries)

    def _plan_queries(self, message: str, *, tools: tuple[str, ...] | None = None) -> list[str]:
        normalized = re.sub(r"\s+", " ", message).strip()
        if not normalized:
            return []
        cleaned = self._clean_query(normalized)
        if "web" in (tools or ()):
            cleaned = self._with_domain_context(cleaned)
        queries = [cleaned]
        if normalized.casefold() != cleaned.casefold() and not self._looks_like_noisy_query(
            normalized
        ):
            queries.append(normalized)
        return list(dict.fromkeys(queries))[:2]

    def _with_domain_context(self, query: str) -> str:
        if self._has_domain_context(query):
            return query
        tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9+-]*", query)
        if len(tokens) <= 2:
            return f"{query} machine learning"
        return query

    @staticmethod
    def _has_domain_context(query: str) -> bool:
        return re.search(
            r"\b(ai|artificial intelligence|machine learning|deep learning|ml|"
            r"neural network|computer vision|nlp|natural language processing|"
            r"model|models|training|inference)\b",
            query,
            flags=re.IGNORECASE,
        ) is not None

    def _select_tools(self, message: str) -> tuple[str, ...]:
        return ("web", "paper")

    def _clean_query(self, message: str) -> str:
        cleaned = message.strip(" ?.")
        for _ in range(3):
            previous = cleaned
            cleaned = re.sub(
                r"^(please\s+)?(explain|find|search|look up|what is|tell me about|"
                r"give me information about|giải thích|tìm kiếm|tìm|"
                r"tôi\s+muốn\s+tìm|tôi\s+cần\s+tìm|hãy\s+tìm)\s+",
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
                r"^(thông tin|nội dung|kiến thức|bài báo|các\s+paper|"
                r"các\s+bài\s+báo|papers?|information|content)"
                r"(\s+(liên\s+quan\s+)?(về\s+chủ\s+đề|về|about|đến|tới|cho))?\s+",
                "",
                cleaned,
                flags=re.IGNORECASE,
            ).strip(" ?.")
            cleaned = re.sub(
                r"^(liên\s+quan\s+)?(về\s+chủ\s+đề|về|about|đến|tới)\s+",
                "",
                cleaned,
                flags=re.IGNORECASE,
            ).strip(" ?.")
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
        web_documents: list[ExternalResearchDocument] = []
        paper_documents: list[ExternalResearchDocument] = []
        seen: set[str] = set()
        for response in responses:
            if isinstance(response, Exception):
                continue
            for document in response:
                key = document.url or document.title
                if key in seen:
                    continue
                seen.add(key)
                if document.source == "paper":
                    paper_documents.append(document)
                else:
                    web_documents.append(document)
        return paper_documents[:2] + web_documents[:3]

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
        instant_url = "https://api.duckduckgo.com/?" + urlencode(
            {
                "q": query,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1",
            }
        )
        payload = await self._fetch_web_json(instant_url)
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
        if documents:
            return documents
        return await self._search_web_html(query)

    async def _fetch_web_json(self, url: str) -> dict:
        return await asyncio.to_thread(self._fetch_json, url)

    async def _search_web_html(self, query: str) -> list[ExternalResearchDocument]:
        text = await self._fetch_web_html_text(
            "https://html.duckduckgo.com/html/?" + urlencode({"q": query})
        )
        parser = _DuckDuckGoHTMLParser()
        parser.feed(text)
        documents: list[ExternalResearchDocument] = []
        for item in parser.results:
            title = item.get("title", "").strip()
            url = self._resolve_duckduckgo_result_url(item.get("url", ""))
            snippet = item.get("snippet", "").strip()
            if title and url:
                documents.append(
                    ExternalResearchDocument(
                        title=title,
                        url=url,
                        snippet=snippet or title,
                        source="web",
                    )
                )
            if len(documents) >= 4:
                break
        if text.strip() and not documents:
            logger.warning("duckduckgo_html_parse_empty")
        return documents

    async def _fetch_web_html_text(self, url: str) -> str:
        return await asyncio.to_thread(self._fetch_text, url)

    @staticmethod
    def _resolve_duckduckgo_result_url(value: str) -> str:
        if not value:
            return ""
        if value.startswith("//"):
            value = f"https:{value}"
        parsed = urlsplit(value)
        if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
            target = parse_qs(parsed.query).get("uddg", [""])[0]
            return unquote(target)
        return value

    async def _search_papers(self, query: str) -> list[ExternalResearchDocument]:
        if settings.semantic_scholar_api_key.strip():
            try:
                documents = await self._search_semantic_scholar_papers(query)
                if documents:
                    return documents
            except Exception:
                pass
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

    async def _search_semantic_scholar_papers(
        self, query: str
    ) -> list[ExternalResearchDocument]:
        await self._wait_for_semantic_scholar_slot()
        fields = ",".join(
            (
                "paperId",
                "title",
                "year",
                "citationCount",
                "authors",
                "venue",
                "url",
                "abstract",
                "openAccessPdf",
                "externalIds",
            )
        )
        url = "https://api.semanticscholar.org/graph/v1/paper/search/bulk?" + urlencode(
            {
                "query": query,
                "limit": "8",
                "fields": fields,
                "sort": "citationCount:desc",
            }
        )
        payload = await self._fetch_semantic_scholar_json(
            url,
            {
                "User-Agent": "AI-Learning-Copilot/1.0",
                "x-api-key": settings.semantic_scholar_api_key.strip(),
            },
        )
        return self._semantic_scholar_documents(query, payload)

    async def _fetch_semantic_scholar_json(
        self, url: str, headers: dict[str, str]
    ) -> dict:
        return await asyncio.to_thread(self._fetch_json_with_headers, url, headers)

    async def _wait_for_semantic_scholar_slot(self) -> None:
        cls = type(self)
        async with cls._semantic_scholar_lock:
            elapsed = time.monotonic() - cls._semantic_scholar_last_request_at
            if elapsed < 1.0:
                await asyncio.sleep(1.0 - elapsed)
            cls._semantic_scholar_last_request_at = time.monotonic()

    def _semantic_scholar_documents(
        self, query: str, payload: dict
    ) -> list[ExternalResearchDocument]:
        query_terms = self._distinctive_query_terms(query)
        documents: list[ExternalResearchDocument] = []
        for item in payload.get("data") or []:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            abstract = str(item.get("abstract") or "").strip()
            text = f"{title} {abstract}".casefold()
            if query_terms and not any(term in text for term in query_terms):
                continue
            authors = tuple(
                str(author.get("name") or "").strip()
                for author in item.get("authors") or []
                if isinstance(author, dict) and str(author.get("name") or "").strip()
            )
            year = item.get("year")
            citation_count = item.get("citationCount")
            venue = str(item.get("venue") or "").strip() or None
            doi = (item.get("externalIds") or {}).get("DOI")
            metadata_bits = []
            if isinstance(year, int):
                metadata_bits.append(str(year))
            if isinstance(citation_count, int):
                metadata_bits.append(f"{citation_count} citations")
            if venue:
                metadata_bits.append(venue)
            if authors:
                metadata_bits.append(", ".join(authors[:3]))
            snippet = abstract or title
            if metadata_bits:
                snippet = f"{' | '.join(metadata_bits)}. {snippet}"
            if title and url:
                documents.append(
                    ExternalResearchDocument(
                        title=title,
                        url=url,
                        snippet=snippet,
                        source="paper",
                        citation_count=citation_count if isinstance(citation_count, int) else None,
                        year=year if isinstance(year, int) else None,
                        authors=authors,
                        venue=venue,
                        doi=str(doi).strip() if doi else None,
                    )
                )
            if len(documents) >= 4:
                break
        return documents

    @staticmethod
    def _distinctive_query_terms(query: str) -> set[str]:
        stop_terms = {
            "ai",
            "artificial",
            "deep",
            "learning",
            "machine",
            "ml",
            "model",
            "models",
            "network",
            "neural",
        }
        return {
            token.casefold()
            for token in re.findall(r"[A-Za-z][A-Za-z0-9+-]{2,}", query)
            if token.casefold() not in stop_terms
        }

    def _fetch_json(self, url: str) -> dict:
        return json.loads(self._fetch_text(url))

    def _fetch_json_with_headers(self, url: str, headers: dict[str, str]) -> dict:
        return json.loads(self._fetch_text_with_headers(url, headers))

    def _fetch_text(self, url: str) -> str:
        return self._fetch_text_with_headers(url, {"User-Agent": "AI-Learning-Copilot/1.0"})

    def _fetch_text_with_headers(self, url: str, headers: dict[str, str]) -> str:
        request = Request(url, headers=headers)
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
        observation = self._build_external_observation(documents, citations)
        base_thought = self._build_external_thought(message)
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

    def _synthesize_answer_stream(
        self,
        *,
        message: str,
        documents: list[ExternalResearchDocument],
        citations: list[AgentCitation],
        recent_messages: list[dict],
    ):
        from collections.abc import Generator

        responder = self.responder
        rag_respond_stream = getattr(responder, "rag_respond_stream", None)
        if rag_respond_stream is None:
            return None
        observation = self._build_external_observation(documents, citations)
        base_thought = self._build_external_thought(message)

        def _generate() -> Generator[str, None, None]:
            yield from rag_respond_stream(
                message=message,
                thought=base_thought,
                observations=[observation],
                route_context=None,
                recent_messages=recent_messages,
            )

        return _generate()

    def _build_external_observation(
        self,
        documents: list[ExternalResearchDocument],
        citations: list[AgentCitation],
    ) -> dict:
        return {
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

    @staticmethod
    def _build_external_thought(message: str) -> dict:
        return {
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

    async def answer_stream(
        self, *, message: str, recent_messages: list[dict] | None = None
    ):
        import json as _json
        from collections.abc import AsyncGenerator

        async def _generate() -> AsyncGenerator[str, None]:
            plan = self._plan_search(message)

            yield _json.dumps({"status": "Searching web and papers"}) + "\n"
            documents = await self._act(plan)

            pipeline = ["plan", "search", "consolidate", "respond"]
            if not documents:
                result = ToolResult(
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
                        "selected_tools": list(plan.tools),
                    },
                )
                yield _json.dumps({"done": result.model_dump(mode="json")}) + "\n"
                return

            citations = self._citations(documents)
            yield _json.dumps({"status": "Composing answer"}) + "\n"

            stream = self._synthesize_answer_stream(
                message=message,
                documents=documents,
                citations=citations,
                recent_messages=recent_messages or [],
            )

            answer = ""
            if stream is not None:
                accumulated: list[str] = []
                for token in stream:
                    accumulated.append(token)
                    yield _json.dumps({"chunk": token}) + "\n"
                answer = "".join(accumulated).strip()
            else:
                answer = self._synthesize_answer(
                    message=message,
                    documents=documents,
                    citations=citations,
                    recent_messages=recent_messages or [],
                ) or ""

            if answer:
                answer = self._with_numeric_source_links(answer, citations)
                result = ToolResult(
                    kind="find_content",
                    answer_markdown=answer,
                    citations=citations,
                    requires_evidence=False,
                    metadata={
                        "tool_mode": "web_papers",
                        "answer_confidence": "grounded",
                        "pipeline": pipeline,
                        "selected_tools": list(plan.tools),
                        "external_source_count": len(documents),
                        "response_synthesized": stream is not None,
                    },
                )
            else:
                source_lines = [
                    f"{index}. **{document.title}** ({'paper' if document.source == 'paper' else 'web'}): "
                    f"{self._shorten(document.snippet)}"
                    for index, document in enumerate(documents[:4], start=1)
                ]
                result = ToolResult(
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
                        "selected_tools": list(plan.tools),
                        "external_source_count": len(documents),
                        "response_synthesized": False,
                    },
                )

            yield _json.dumps({"done": result.model_dump(mode="json")}) + "\n"

        return _generate()

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
