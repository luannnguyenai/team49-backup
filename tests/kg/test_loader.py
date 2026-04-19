"""Integration tests for src.kg.loader."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from src.kg.loader import load_sources


class TestLoadSourcesHappyPath:
    async def test_counts_match_seed(self, db_with_seed, mini_bridges_path: Path) -> None:
        """load_sources returns correct counts for a known DB seed."""
        sources = await load_sources(db_with_seed, mini_bridges_path)

        assert len(sources.topics) == 6
        assert len(sources.kcs) == 12
        assert len(sources.questions) == 12
        assert len(sources.bridges.concepts) == 1
        assert len(sources.bridges.instance_of) == 2
        assert len(sources.bridges.transfers_to) == 1


class TestIntegrityErrors:
    async def test_invalid_kc_slug_raises_validation_error(
        self, db_with_seed, tmp_path: Path
    ) -> None:
        """instance_of referencing a missing kc_slug raises ValidationError."""
        (tmp_path / "kg_bridges.yaml").write_text(
            "concepts:\n"
            "  - id: CON-x\n"
            "    name: X\n"
            "    canonical_kc_slug: KC-mini-nlp-t1-kc1\n"
            "instance_of:\n"
            "  - kc_slug: KC-DOES-NOT-EXIST\n"
            "    concept_id: CON-x\n"
            "transfers_to: []\n",
            encoding="utf-8",
        )

        with pytest.raises(ValidationError, match="instance_of.*kc_slug"):
            await load_sources(db_with_seed, tmp_path)

    async def test_invalid_topic_slug_raises_validation_error(
        self, db_with_seed, tmp_path: Path
    ) -> None:
        """transfers_to referencing a missing topic slug raises ValidationError."""
        (tmp_path / "kg_bridges.yaml").write_text(
            "concepts: []\n"
            "instance_of: []\n"
            "transfers_to:\n"
            "  - from_topic: TOPIC-NONEXISTENT\n"
            "    to_topic: mini_cv_t1\n"
            "    weight: 0.5\n"
            "    reason: test\n",
            encoding="utf-8",
        )

        with pytest.raises(ValidationError, match="transfers_to.*from_topic"):
            await load_sources(db_with_seed, tmp_path)


class TestYAMLErrors:
    async def test_malformed_yaml_raises_clear_error(
        self, db_with_seed, tmp_path: Path
    ) -> None:
        """A YAML syntax error bubbles up as yaml.YAMLError."""
        (tmp_path / "kg_bridges.yaml").write_text(
            "concepts: [\n  - id: broken\n    name: [missing close\n",
            encoding="utf-8",
        )

        with pytest.raises(yaml.YAMLError, match="expected|while parsing"):
            await load_sources(db_with_seed, tmp_path)
