import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import scripts.assert_init_inputs as module


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class AssertInitInputsTests(TestCase):
    def test_assert_canonical_bundle_requires_manifest_and_all_import_files(self) -> None:
        with TemporaryDirectory() as tmp:
            canonical_dir = Path(tmp)
            _write(canonical_dir / "manifest.json", "{}")
            for spec in module.IMPORT_SPECS.values():
                _write(canonical_dir / spec.filename, "{}\n")

            report = module.assert_canonical_bundle(canonical_dir)

            self.assertIn("manifest", report)
            self.assertEqual(set(report["tables"].keys()), set(module.IMPORT_SPECS.keys()))

    def test_assert_bootstrap_metadata_requires_image_baked_json_files(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            courses = root / "data/bootstrap/courses.json"
            overviews = root / "data/bootstrap/overviews.json"
            _write(courses, "[]")
            _write(overviews, "[]")

            with (
                patch.object(module, "COURSES_FILE", courses),
                patch.object(module, "OVERVIEWS_FILE", overviews),
            ):
                report = module.assert_bootstrap_metadata()

            self.assertEqual(report["courses"]["path"], str(courses))
            self.assertEqual(report["overviews"]["path"], str(overviews))

    def test_assert_runtime_lecture_inputs_require_bundle_transcript_paths_in_image(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            canonical_dir = root / "canonical"
            _write(canonical_dir / "units.jsonl", "")
            transcript_224n = root / "data/courses/CS224n/transcripts/lecture-01.txt"
            transcript_231n = root / "data/courses/CS231n/transcripts/lecture-01.txt"
            _write(transcript_224n, "00:00\nhello")
            _write(transcript_231n, "00:00\nworld")
            _write(
                canonical_dir / "units.jsonl",
                "\n".join(
                    [
                        json.dumps(
                            {
                                "course_id": "CS224n",
                                "lecture_order": 1,
                                "transcript_path": transcript_224n.as_posix(),
                            }
                        ),
                        json.dumps(
                            {
                                "course_id": "CS231n",
                                "lecture_order": 1,
                                "transcript_path": transcript_231n.as_posix(),
                            }
                        ),
                    ]
                ),
            )

            with patch.object(
                module,
                "_course_specs",
                return_value=[("cs224n", root / "data/courses/CS224n"), ("cs231n", root / "data/courses/CS231n")],
            ):
                report = module.assert_runtime_lecture_inputs(canonical_dir)

            self.assertEqual(report["cs224n"]["lecture_count"], 1)
            self.assertEqual(report["cs231n"]["lecture_count"], 1)

    def test_assert_runtime_lecture_inputs_fail_when_transcript_missing(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            canonical_dir = root / "canonical"
            transcript_224n = root / "data/courses/CS224n/transcripts/lecture-01.txt"
            _write(transcript_224n, "00:00\nhello")
            _write(
                canonical_dir / "units.jsonl",
                "\n".join(
                    [
                        json.dumps(
                            {
                                "course_id": "CS224n",
                                "lecture_order": 1,
                                "transcript_path": transcript_224n.as_posix(),
                            }
                        ),
                        json.dumps(
                            {
                                "course_id": "CS231n",
                                "lecture_order": 1,
                                "transcript_path": (root / "missing.txt").as_posix(),
                            }
                        ),
                    ]
                ),
            )

            with patch.object(
                module,
                "_course_specs",
                return_value=[("cs224n", root / "data/courses/CS224n"), ("cs231n", root / "data/courses/CS231n")],
            ):
                with self.assertRaises(FileNotFoundError):
                    module.assert_runtime_lecture_inputs(canonical_dir)
