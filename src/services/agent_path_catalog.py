from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentPathCatalogEntry:
    path_id: str
    label: str
    selected_course_ids: tuple[str, ...]


AGENT_PATH_CATALOG: dict[str, AgentPathCatalogEntry] = {
    "computer_vision": AgentPathCatalogEntry(
        path_id="computer_vision",
        label="Computer Vision",
        selected_course_ids=("CS230", "CS231n"),
    ),
    "nlp": AgentPathCatalogEntry(
        path_id="nlp",
        label="Natural Language Processing",
        selected_course_ids=("CS230", "CS224n"),
    ),
}


def get_agent_path(path_id: str | None) -> AgentPathCatalogEntry | None:
    if not path_id:
        return None
    return AGENT_PATH_CATALOG.get(path_id)


def fallback_path_label(path_id: str) -> str:
    return path_id.replace("_", " ").title()
