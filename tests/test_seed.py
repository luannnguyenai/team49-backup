from pathlib import Path
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

import scripts.seed as seed_module


class RunSeedInputDirTests(IsolatedAsyncioTestCase):
    async def test_validate_only_passes_input_dir_to_product_shell(self) -> None:
        canonical_report = {"rows": 1, "_loaded_rows": [1]}
        recorded: dict[str, Path] = {}
        tmp_path = Path("/tmp/canonical-bundle")

        def fake_build_product_shell_bundle(
            *,
            canonical_units_path: Path,
            courses_path: Path | None = None,
            overviews_path: Path | None = None,
        ):
            recorded["canonical_units_path"] = canonical_units_path
            return {
                "courses": [],
                "course_overviews": [],
                "course_sections": [],
                "learning_units": [],
            }

        with (
            patch.object(
                seed_module,
                "validate_canonical_artifacts",
                side_effect=lambda input_dir: canonical_report,
            ),
            patch.object(
                seed_module,
                "build_product_shell_bundle",
                side_effect=fake_build_product_shell_bundle,
            ),
        ):
            report = await seed_module.run_seed(input_dir=tmp_path, validate_only=True)

        self.assertEqual(report["mode"], "validate_only")
        self.assertEqual(report["canonical"], {"rows": 1})
        self.assertEqual(recorded["canonical_units_path"], tmp_path / "units.jsonl")

    async def test_import_passes_input_dir_to_product_shell(self) -> None:
        canonical_report = {"imported": 10}
        product_report = {"counts": {"learning_units": 3}}
        parity_report = {"ok": True}
        tmp_path = Path("/tmp/canonical-bundle")

        session = AsyncMock()

        class FakeSessionContext:
            async def __aenter__(self):
                return session

            async def __aexit__(self, exc_type, exc, tb):
                return False

        import_canonical = AsyncMock(return_value=canonical_report)
        import_product = AsyncMock(return_value=product_report)
        seed_lectures = AsyncMock()
        build_parity = AsyncMock(return_value=parity_report)

        with (
            patch.object(seed_module, "async_session", return_value=FakeSessionContext()),
            patch.object(seed_module, "import_canonical_artifacts", import_canonical),
            patch.object(seed_module, "import_product_shell", import_product),
            patch.object(seed_module, "seed_lectures_runtime", seed_lectures),
            patch.object(seed_module, "build_parity_report", build_parity),
        ):
            report = await seed_module.run_seed(input_dir=tmp_path, validate_only=False)

        self.assertEqual(report["mode"], "import")
        import_canonical.assert_awaited_once_with(session=session, input_dir=tmp_path)
        import_product.assert_awaited_once_with(
            session=session,
            canonical_units_path=tmp_path / "units.jsonl",
        )
