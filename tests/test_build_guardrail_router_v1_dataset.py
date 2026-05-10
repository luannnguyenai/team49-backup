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
        / "build_guardrail_router_v1_dataset.py"
    )
    spec = importlib.util.spec_from_file_location("build_guardrail_router_v1_dataset", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class GuardrailRouterV1DatasetTests(unittest.TestCase):
    def test_router_target_is_label_only_and_validates_invariants(self):
        module = _load_module()

        on_topic = module.build_target(
            safety_label="SAFE",
            topic_label="ON_TOPIC",
            action="ALLOW_LESSON_ANSWER",
            attack_type="none",
            selected_kp_ids=["kp_a"],
        )
        self.assertEqual(
            on_topic,
            {
                "safety_label": "SAFE",
                "topic_label": "ON_TOPIC",
                "action": "ALLOW_LESSON_ANSWER",
                "attack_type": "none",
                "selected_kp_ids": ["kp_a"],
            },
        )
        self.assertNotIn("answer", on_topic)
        self.assertNotIn("confidence", on_topic)

        unsafe = module.build_target(
            safety_label="JAILBREAK",
            topic_label="OFF_TOPIC",
            action="SOFT_REFUSE_REDIRECT",
            attack_type="prompt_injection",
            selected_kp_ids=["kp_a"],
        )
        self.assertEqual(unsafe["topic_label"], "N_A")
        self.assertEqual(unsafe["action"], "SAFETY_REFUSE")
        self.assertEqual(unsafe["selected_kp_ids"], [])

    def test_write_jsonl_and_manifest_preserve_requested_counts(self):
        module = _load_module()

        samples = [
            module.RouterSample(
                sample_id="a",
                source="unit",
                split="train",
                input_text="### TASK\nReturn only valid JSON.",
                target={
                    "safety_label": "SAFE",
                    "topic_label": "ON_TOPIC",
                    "action": "ALLOW_LESSON_ANSWER",
                    "attack_type": "none",
                    "selected_kp_ids": ["kp_a"],
                },
                metadata={"route_group": "ON_TOPIC"},
            ),
            module.RouterSample(
                sample_id="b",
                source="unit",
                split="validation",
                input_text="### TASK\nReturn only valid JSON.",
                target={
                    "safety_label": "SAFE",
                    "topic_label": "OFF_TOPIC",
                    "action": "SOFT_REFUSE_REDIRECT",
                    "attack_type": "none",
                    "selected_kp_ids": [],
                },
                metadata={"route_group": "OFF_TOPIC"},
            ),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir)
            manifest = module.write_outputs(samples, output)

            train_rows = [
                json.loads(line)
                for line in (output / "train.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            val_rows = [
                json.loads(line)
                for line in (output / "validation.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            manifest_file = json.loads((output / "manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(len(train_rows), 1)
        self.assertEqual(len(val_rows), 1)
        self.assertEqual(train_rows[0]["output"], samples[0].target)
        self.assertEqual(manifest["counts_by_split"]["train"], 1)
        self.assertEqual(manifest_file["counts_by_route_group"]["ON_TOPIC"], 1)

    def test_build_input_text_excludes_answer_payload(self):
        module = _load_module()

        text = module.build_input_text(
            scope={
                "scope_level": "unit",
                "scope_id": "unit-1",
                "out_of_scope_policy": "strict",
                "allowed_scope_summary": "Gradient descent basics.",
            },
            candidate_kps=[{"kp_id": "kp_gd", "description": "Gradient descent updates."}],
            user_query="Why does gradient descent update weights?",
            recent_context="",
            selected_text="",
        )

        self.assertIn("### TASK", text)
        self.assertIn("Return only valid JSON", text)
        self.assertIn("### USER_QUERY", text)
        self.assertIn("Why does gradient descent update weights?", text)
        self.assertNotIn("answer_text", text)
        self.assertNotIn("reference", text)

    def test_split_eduvidqa_text_input_extracts_student_question(self):
        module = _load_module()

        context, question = module.split_eduvidqa_text_input(
            "Transcript window:\n[00:01] lecture content\n\nStudent question:\nWhy does this work?"
        )

        self.assertEqual(context, "Transcript window: [00:01] lecture content")
        self.assertEqual(question, "Why does this work?")


if __name__ == "__main__":
    unittest.main()
