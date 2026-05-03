from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


class AgentPromptManager:
    def __init__(self, base_dir: Path | str | None = None):
        if base_dir is None:
            base_dir = Path(__file__).resolve().parents[1] / "prompts" / "agent"
        self.base_dir = Path(base_dir)

    def get(self, prompt_name: str, key: str) -> str:
        value: Any = self._load(prompt_name)
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                raise KeyError(f"Missing prompt key: {prompt_name}.{key}")
            value = value[part]
        if not isinstance(value, str):
            raise KeyError(f"Prompt key is not text: {prompt_name}.{key}")
        return value

    def render(self, prompt_name: str, key: str, **kwargs: Any) -> str:
        template = self.get(prompt_name, key)
        return template.format(**kwargs) if kwargs else template

    @lru_cache(maxsize=16)
    def _load(self, prompt_name: str) -> dict[str, Any]:
        path = self.base_dir / f"{prompt_name}.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"Prompt file must contain a mapping: {path}")
        return data


_default_agent_prompt_manager: AgentPromptManager | None = None


def get_agent_prompt_manager() -> AgentPromptManager:
    global _default_agent_prompt_manager
    if _default_agent_prompt_manager is None:
        _default_agent_prompt_manager = AgentPromptManager()
    return _default_agent_prompt_manager
