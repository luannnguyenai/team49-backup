import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


def _load_module():
    module_path = (
        Path(__file__).resolve().parent.parent
        / "scripts"
        / "prepare_eduvidqa_ft_dataset.py"
    )
    spec = importlib.util.spec_from_file_location("prepare_eduvidqa_ft_dataset", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class EduVidQAFTDatasetTests(unittest.TestCase):
    def test_parse_timestamp_supports_mm_ss_and_hh_mm_ss(self):
        module = _load_module()

        self.assertEqual(module.parse_timestamp_seconds("3:54"), 234.0)
        self.assertEqual(module.parse_timestamp_seconds("2:06:36"), 7596.0)
        self.assertEqual(module.parse_timestamp_seconds("0:0"), 0.0)
        self.assertEqual(
            module.parse_eduvidqa_timestamp_seconds("25:59:00", "synthetic_train"),
            1559.0,
        )
        self.assertEqual(
            module.parse_eduvidqa_timestamp_seconds("1:42:18", "real_world_test"),
            6138.0,
        )

    def test_transcript_window_keeps_overlapping_segments_and_formats_context(self):
        module = _load_module()
        rows = [
            {"text": "too early", "start": 5.0, "duration": 2.0},
            {"text": "left edge", "start": 29.0, "duration": 5.0},
            {"text": "middle", "start": 60.0, "duration": 2.0},
            {"text": "right edge", "start": 90.0, "duration": 1.0},
            {"text": "too late", "start": 95.1, "duration": 1.0},
        ]

        context = module.build_transcript_context(rows, center_seconds=60, window_seconds=30)

        self.assertIn("[00:29] left edge", context)
        self.assertIn("[01:00] middle", context)
        self.assertIn("[01:30] right edge", context)
        self.assertNotIn("too early", context)
        self.assertNotIn("too late", context)

    def test_load_qa_rows_supports_all_eduvidqa_csv_schemas(self):
        module = _load_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            synthetic_train = root / "synthetic_train.csv"
            with synthetic_train.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "vid_id",
                        "vid_url",
                        "vid_title",
                        "timestamp",
                        "final_answer",
                        "final_question",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "vid_id": "abcdefghijk",
                        "vid_url": "https://youtube.com/watch?v=abcdefghijk",
                        "vid_title": "Lecture",
                        "timestamp": "3:54",
                        "final_answer": "answer",
                        "final_question": "At <timestamp>, why?",
                    }
                )

            real_world = root / "real_world_test.csv"
            with real_world.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["url", "id", "question", "answer", "timestamp"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "url": "https://youtube.com/watch?v=zzzzzzzzzzz",
                        "id": "zzzzzzzzzzz",
                        "question": "How?",
                        "answer": "Because.",
                        "timestamp": "2:06:36",
                    }
                )

            rows = module.load_qa_rows([synthetic_train, real_world])

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].video_id, "abcdefghijk")
        self.assertEqual(rows[0].question, "At 3:54, why?")
        self.assertEqual(rows[0].answer, "answer")
        self.assertEqual(rows[0].timestamp_seconds, 234.0)
        self.assertEqual(rows[0].split, "synthetic_train")
        self.assertEqual(rows[1].video_id, "zzzzzzzzzzz")
        self.assertEqual(rows[1].timestamp_seconds, 7596.0)
        self.assertEqual(rows[1].split, "real_world_test")

    def test_load_qa_rows_can_recover_missing_synthetic_test_timestamp_from_answer(self):
        module = _load_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            synthetic_test = root / "synthetic_test.csv"
            with synthetic_test.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["vid_id", "vid_title", "vid_url", "question", "answer", "timestamp"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "vid_id": "abcdefghijk",
                        "vid_title": "Lecture",
                        "vid_url": "https://youtube.com/watch?v=abcdefghijk",
                        "question": "At <timestamp>, why does this work?",
                        "answer": "At 10:41, the lecture explains the key step.",
                        "timestamp": "",
                    }
                )

            rows = module.load_qa_rows([synthetic_test], recover_answer_timestamps=True)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].timestamp, "10:41")
        self.assertEqual(rows[0].timestamp_seconds, 641.0)
        self.assertEqual(rows[0].timestamp_source, "answer_text_recovered")
        self.assertEqual(rows[0].original_timestamp, "")
        self.assertEqual(rows[0].question, "At 10:41, why does this work?")

    def test_quality_flags_drop_meta_rewrite_and_short_answer_but_not_docs_reference(self):
        module = _load_module()

        self.assertIn(
            "synthetic_rewrite_style",
            module.classify_quality_flags(
                "To improve the clarity of this answer, I will rephrase it clearly.",
                question="Why?",
            ),
        )
        self.assertIn(
            "short_answer",
            module.classify_quality_flags("Too short.", question="Why is the algorithm correct?"),
        )
        self.assertNotIn(
            "short_answer",
            module.classify_quality_flags(
                "Flask uses Jinja templates for placeholders, so the rendered name comes from the context passed by app.py. Refer to the Jinja documentation for API details.",
                question="Why does {{show}} work?",
            ),
        )

    def test_build_dataset_record_has_image_text_and_answer_fields(self):
        module = _load_module()
        row = module.QARow(
            row_id="synthetic_train_000001",
            split="synthetic_train",
            video_id="abcdefghijk",
            video_url="https://youtube.com/watch?v=abcdefghijk",
            title="Lecture",
            timestamp="3:54",
            timestamp_seconds=234.0,
            timestamp_source="csv",
            original_timestamp="3:54",
            question="What is happening?",
            answer="An explanation.",
            source="synthetic_train.csv:2",
        )

        record = module.build_dataset_record(
            row=row,
            image_path=Path("frames/synthetic_train/abcdefghijk_000234_000001.jpg"),
            transcript_context="[03:50] hello",
            output_root=Path("data/eduvidqa/ft_context_vlm"),
        )

        self.assertEqual(record["image"], "frames/synthetic_train/abcdefghijk_000234_000001.jpg")
        self.assertEqual(record["timestamp_source"], "csv")
        self.assertEqual(record["original_timestamp"], "3:54")
        self.assertIn("Transcript window", record["text_input"])
        self.assertIn("[03:50] hello", record["text_input"])
        self.assertIn("Student question:", record["text_input"])
        self.assertEqual(record["answer"], "An explanation.")
        self.assertEqual(record["messages"][0]["content"][0]["type"], "image")
        self.assertEqual(record["messages"][1]["content"], "An explanation.")


if __name__ == "__main__":
    unittest.main()
