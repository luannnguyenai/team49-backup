from pathlib import Path

import pytest

from src.services.agent_prompt_manager import AgentPromptManager


def test_prompt_manager_loads_yaml_prompt_and_renders_variables(tmp_path: Path):
    prompt_file = tmp_path / "agentic_rag.yaml"
    prompt_file.write_text(
        """
thinking:
  system: "Think about {topic} with {tool_list}."
acting:
  notices:
    missing: "Missing {name}"
""",
        encoding="utf-8",
    )

    manager = AgentPromptManager(base_dir=tmp_path)

    assert manager.render("agentic_rag", "thinking.system", topic="YOLO", tool_list="RAG") == (
        "Think about YOLO with RAG."
    )
    assert manager.render("agentic_rag", "acting.notices.missing", name="query") == "Missing query"


def test_prompt_manager_fails_fast_for_missing_prompt_key(tmp_path: Path):
    (tmp_path / "agentic_rag.yaml").write_text("thinking:\n  system: hello\n", encoding="utf-8")
    manager = AgentPromptManager(base_dir=tmp_path)

    with pytest.raises(KeyError):
        manager.get("agentic_rag", "acting.system")
