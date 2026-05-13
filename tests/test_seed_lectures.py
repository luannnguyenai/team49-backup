from types import SimpleNamespace
from unittest import TestCase

import scripts.seed_lectures as module


class SeedLecturesTests(TestCase):
    def test_build_runtime_lecture_specs_uses_canonical_units_instead_of_toc_summary(self) -> None:
        units = [
            SimpleNamespace(
                unit_id="u1",
                course_id="CS224n",
                lecture_id="lecture-10",
                lecture_order=10,
                lecture_title="Transformer Lecture",
                unit_name="Motivation",
                description="Why attention matters",
                summary="RNN limitations",
                ordering_index=1,
                content_ref={"start_s": 120, "end_s": 300, "video_url": "https://example.com/v"},
                transcript_path="data/courses/CS224n/transcripts/lecture-10.txt",
            ),
            SimpleNamespace(
                unit_id="u2",
                course_id="CS224n",
                lecture_id="lecture-10",
                lecture_order=10,
                lecture_title="Transformer Lecture",
                unit_name="Self-attention",
                description="QKV",
                summary="Attention math",
                ordering_index=2,
                content_ref={"start_s": 300, "end_s": 480, "video_url": "https://example.com/v"},
                transcript_path="data/courses/CS224n/transcripts/lecture-10.txt",
            ),
        ]

        specs = module._build_runtime_lecture_specs(units)

        self.assertEqual(len(specs), 1)
        spec = specs[0]
        self.assertEqual(spec.course_slug, "cs224n")
        self.assertEqual(spec.lecture_order, 10)
        expected_video = module._find_course_video(module.CS224N_DIR, 10)
        expected_lecture_id = module.build_course_runtime_lecture_id(
            course_slug="cs224n",
            lecture_order=10,
            explicit_lecture_id="lecture-10",
            video_filename=expected_video.name if expected_video is not None else None,
        )
        self.assertEqual(spec.lecture_id, expected_lecture_id)
        self.assertEqual(spec.lecture_title, "Transformer Lecture")
        self.assertEqual(
            spec.video_url,
            str(expected_video) if expected_video is not None else "https://example.com/v",
        )
        self.assertEqual(len(spec.chapters), 2)
        self.assertEqual(spec.chapters[0].title, "Motivation")
        self.assertEqual(spec.chapters[0].start_time, 120)
        self.assertEqual(spec.chapters[0].end_time, 300)
        self.assertEqual(spec.chapters[1].title, "Self-attention")
        self.assertEqual(spec.chapters[1].end_time, 480)
