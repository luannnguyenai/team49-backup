from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from src.schemas.agent import AgentCitation


class ExternalSource(Protocol):
    title: str
    url: str
    snippet: str
    source: str


@dataclass(frozen=True)
class ExternalCitationManager:
    top_k: int = 5

    def select_sources(self, documents: list[ExternalSource]) -> list[ExternalSource]:
        selected: list[ExternalSource] = []
        seen: set[tuple[str, str]] = set()
        for document in documents:
            key = self._dedupe_key(document)
            if key in seen:
                continue
            seen.add(key)
            selected.append(document)
            if len(selected) >= self.top_k:
                break
        return selected

    def build_citations(self, documents: list[ExternalSource]) -> list[AgentCitation]:
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
            for index, document in enumerate(documents[: self.top_k], start=1)
        ]

    def render_answer(self, answer: str, citations: list[AgentCitation]) -> str:
        cleaned = self._strip_existing_source_section(
            re.sub(r"\s*\[\^[^\]]+\]", "", answer)
        ).strip()
        indexed_citations = [
            (index, citation)
            for index, citation in enumerate(citations[: self.top_k], start=1)
            if citation.learn_href
        ]
        if not indexed_citations:
            return cleaned

        linked_answer = self._link_numeric_citation_markers(cleaned, indexed_citations)
        linked_answer = self._ensure_first_source_marker(linked_answer, indexed_citations)
        return f"{linked_answer}\n\n{self._source_reference_section(indexed_citations)}"

    def _dedupe_key(self, document: ExternalSource) -> tuple[str, str]:
        source = str(document.source or "web").casefold()
        if source == "paper":
            title = self._normalize_title(document.title)
            if title:
                return source, title
        normalized_url = self._normalize_url(document.url)
        if normalized_url:
            return source, normalized_url
        return source, self._normalize_title(document.title)

    @staticmethod
    def _normalize_url(value: str) -> str:
        if not value:
            return ""
        parsed = urlsplit(value.strip())
        query = urlencode(
            [
                (key, item)
                for key, item in parse_qsl(parsed.query, keep_blank_values=True)
                if not key.lower().startswith("utm_")
            ]
        )
        path = re.sub(r"/+$", "", parsed.path)
        return urlunsplit(
            (
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                path,
                query,
                "",
            )
        )

    @staticmethod
    def _normalize_title(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()

    def _link_numeric_citation_markers(
        self,
        answer: str,
        indexed_citations: list[tuple[int, AgentCitation]],
    ) -> str:
        href_by_index = {
            index: citation.learn_href
            for index, citation in indexed_citations
            if citation.learn_href
        }

        def replace(match: re.Match[str]) -> str:
            index = int(match.group(1))
            href = href_by_index.get(index)
            if not href:
                return ""
            return f"[{index}]({href})"

        return re.sub(r"(?<!\[)\[(\d{1,2})\](?!\()", replace, answer)

    def _ensure_first_source_marker(
        self,
        answer: str,
        indexed_citations: list[tuple[int, AgentCitation]],
    ) -> str:
        if not answer.strip() or re.search(r"\[\d{1,2}\]\([^)]+\)", answer):
            return answer
        first_index, first_citation = indexed_citations[0]
        if not first_citation.learn_href:
            return answer
        marker = f"[{first_index}]({first_citation.learn_href})"
        paragraphs = answer.split("\n\n", 1)
        first = paragraphs[0].rstrip()
        if first.endswith((".", "!", "?", "。", "！", "？")):
            first = f"{first} {marker}"
        else:
            first = f"{first}. {marker}"
        if len(paragraphs) == 1:
            return first
        return f"{first}\n\n{paragraphs[1]}"

    def _source_reference_section(self, indexed_citations: list[tuple[int, AgentCitation]]) -> str:
        lines = ["## Sources"]
        for index, citation in indexed_citations:
            title = self._markdown_link_label(citation.unit_name)
            source = "Paper" if str(citation.source or "").lower() == "paper" else "Web"
            summary = self._shorten(citation.quote or "", limit=180)
            line = f"{index}. [{title}]({citation.learn_href}) - {source}"
            if summary:
                line = f"{line}. {summary}"
            lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def _strip_existing_source_section(answer: str) -> str:
        return re.split(
            r"\n\s*(?:#{1,6}\s*)?Sources\s*:?\s*\n", answer, maxsplit=1, flags=re.IGNORECASE
        )[0]

    @staticmethod
    def _markdown_link_label(value: str) -> str:
        cleaned = re.sub(r"\s+", " ", value).strip()
        return cleaned.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")

    @staticmethod
    def _shorten(value: str, limit: int = 260) -> str:
        cleaned = re.sub(r"\s+", " ", value).strip()
        if len(cleaned) <= limit:
            return cleaned
        return f"{cleaned[: limit - 3].rstrip()}..."
