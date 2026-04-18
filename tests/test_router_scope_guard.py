import unittest
from unittest.mock import patch

from src.services.router import route_question


class _FakeLLM:
    def __init__(self, content):
        self.content = content
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return type("Resp", (), {"content": self.content})()


class RouterScopeGuardTests(unittest.TestCase):
    def test_route_question_preserves_adjacent_scope_for_simple_answers(self):
        fake_llm = _FakeLLM(
            '{"route":"SIMPLE","scope":"ADJACENT","direct_answer":"Nó vẫn nằm trong lecture hiện tại.","reason":"lecture-related but outside the active chapter"}'
        )

        with patch("src.services.router._get_router_llm", return_value=fake_llm):
            result = route_question(
                question="BatchNorm dùng để làm gì?",
                lecture_title="Lecture 6: CNN Architectures",
                context_summary="- Batch Normalization: ổn định phân phối kích hoạt",
                current_timestamp=1200,
                current_chapter="AlexNet, VGGNet, GoogLeNet, ResNet",
                lecture_scope={
                    "lecture_title": "Lecture 6: CNN Architectures",
                    "course_phase": "Perceiving and Understanding the Visual World",
                    "core_topics": [
                        "Batch Normalization",
                        "Transfer learning",
                        "AlexNet, VGG, ResNet",
                    ],
                    "scope_keywords": [
                        "cnn architectures",
                        "batch normalization",
                        "resnet",
                    ],
                },
            )

        self.assertEqual(result["route"], "SIMPLE")
        self.assertEqual(result["scope"], "ADJACENT")
        self.assertIn("lecture hiện tại", result["direct_answer"])
        self.assertIn("Batch Normalization", fake_llm.messages[1].content)

    def test_route_question_builds_contextual_block_message_for_out_of_scope_questions(self):
        fake_llm = _FakeLLM(
            '{"route":"BLOCKED","scope":"BLOCKED","reason":"outside lecture scope"}'
        )

        with patch("src.services.router._get_router_llm", return_value=fake_llm):
            result = route_question(
                question="Viết giúp mình bài thơ tình nhé",
                lecture_title="Lecture 5: Image Classification with CNNs",
                context_summary="- Convolution and pooling: các phép tích chập và pooling",
                current_timestamp=900,
                current_chapter="Convolution and pooling",
                lecture_scope={
                    "lecture_title": "Lecture 5: Image Classification with CNNs",
                    "course_phase": "Perceiving and Understanding the Visual World",
                    "core_topics": [
                        "History",
                        "Higher-level representations",
                        "Convolution and pooling",
                    ],
                    "scope_keywords": ["cnn", "convolution", "pooling"],
                },
            )

        self.assertEqual(result["route"], "BLOCKED")
        self.assertEqual(result["scope"], "BLOCKED")
        self.assertIn("Convolution and pooling", result["message"])
        self.assertIn("Lecture 5", result["message"])


if __name__ == "__main__":
    unittest.main()
