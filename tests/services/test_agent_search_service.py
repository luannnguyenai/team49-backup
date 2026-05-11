from types import SimpleNamespace

import pytest

from src.schemas.agent import RuntimeNavigationTrace, UnitSearchRequest
from src.services.agent_search_service import AgentUnitSearchService


class FakeNavigation:
    async def resolve_many(self, canonical_unit_ids):
        return {
            unit_id: SimpleNamespace(
                canonical_unit_id=unit_id,
                learning_unit_id=f"learning-{unit_id}",
                course_slug="cs231n",
                unit_slug=f"{unit_id}-slug",
                learn_href=f"/courses/cs231n/learn/{unit_id}-slug",
            )
            for unit_id in canonical_unit_ids
        }

    def to_trace(self, nav):
        return RuntimeNavigationTrace(
            canonical_unit_id=nav.canonical_unit_id,
            source="product_learning_unit",
            learning_unit_id=nav.learning_unit_id,
            course_slug=nav.course_slug,
            unit_slug=nav.unit_slug,
            learn_href=nav.learn_href,
        )


@pytest.mark.asyncio
async def test_search_intersects_course_scope_and_sorts_by_score():
    captured = {}

    class Repo:
        async def search_canonical_units(self, terms, course_ids, limit, title_only=False):
            captured["terms"] = terms
            captured["course_ids"] = course_ids
            captured["title_only"] = title_only
            return [
                SimpleNamespace(
                    unit_id="weak",
                    course_id="CS231n",
                    lecture_id="lecture-02",
                    lecture_title="CNN intro",
                    unit_name="Pooling",
                    summary="only cnn",
                    description="",
                    has_quiz_items=True,
                ),
                SimpleNamespace(
                    unit_id="strong",
                    course_id="CS231n",
                    lecture_id="lecture-03",
                    lecture_title="CNN receptive fields",
                    unit_name="CNN receptive field",
                    summary="cnn receptive field convolution",
                    description="",
                    has_quiz_items=False,
                ),
            ]

    service = AgentUnitSearchService(Repo(), FakeNavigation())
    response = await service.search(
        UnitSearchRequest(query="CNN receptive field", courseIds=["CS231n", "CS224n"]),
        allowed_course_ids=["CS231n"],
    )

    assert captured["course_ids"] == ["CS231n"]
    assert captured["title_only"] is True
    assert response.results[0].canonical_unit_id == "strong"
    assert response.results[0].learn_href == "/courses/cs231n/learn/strong-slug"
    assert response.trace.candidate_courses == ["CS231n"]
    assert response.trace.runtime_navigation_resolution[0].canonical_unit_id == "strong"


@pytest.mark.asyncio
async def test_search_scores_punctuation_insensitive_matches_without_domain_synonyms():
    class Repo:
        async def search_canonical_units(self, terms, course_ids, limit, title_only=False):
            return [
                SimpleNamespace(
                    unit_id="u-net-segmentation",
                    course_id="CS231n",
                    lecture_id="lecture-09",
                    lecture_title="Object Detection and Segmentation",
                    unit_name="Semantic segmentation from per-pixel labeling to U-Net",
                    summary="U-Net is discussed in the segmentation lecture.",
                    description="",
                    has_quiz_items=True,
                )
            ]

    service = AgentUnitSearchService(Repo(), FakeNavigation())
    response = await service.search(
        UnitSearchRequest(query="UNet", courseIds=["CS231n"]),
        allowed_course_ids=["CS231n"],
    )

    assert response.results[0].canonical_unit_id == "u-net-segmentation"
    assert response.results[0].score > 0


@pytest.mark.asyncio
async def test_search_does_not_compact_match_across_word_boundaries():
    class Repo:
        async def search_canonical_units(self, terms, course_ids, limit, title_only=False):
            return [
                SimpleNamespace(
                    unit_id="gan-tuning",
                    course_id="CS231n",
                    lecture_id="lecture-14",
                    lecture_title="Generative Models",
                    unit_name="GAN setup",
                    summary="The generator can tune the discriminator feedback.",
                    description="",
                    has_quiz_items=True,
                )
            ]

    service = AgentUnitSearchService(Repo(), FakeNavigation())
    response = await service.search(
        UnitSearchRequest(query="UNet", courseIds=["CS231n"]),
        allowed_course_ids=["CS231n"],
    )

    assert response.results[0].score == 0


@pytest.mark.asyncio
async def test_search_reranks_specific_mask_rcnn_above_broad_rcnn_family():
    class Repo:
        async def search_canonical_units(self, terms, course_ids, limit, title_only=False):
            return [
                SimpleNamespace(
                    unit_id="rcnn-family",
                    course_id="CS231n",
                    lecture_id="lecture-09",
                    lecture_title="Lecture 9: Object Detection, Image Segmentation, Visualizing and Understanding",
                    unit_name="Object detection as classification plus localization and the R-CNN family",
                    summary="R-CNN classifies proposal crops and refines boxes.",
                    description="",
                    has_quiz_items=True,
                ),
                SimpleNamespace(
                    unit_id="mask-rcnn",
                    course_id="CS231n",
                    lecture_id="lecture-09",
                    lecture_title="Lecture 9: Object Detection, Image Segmentation, Visualizing and Understanding",
                    unit_name="Instance segmentation with Mask R-CNN",
                    summary=(
                        "Mask R-CNN extends the R-CNN pipeline with an extra convolutional "
                        "branch that predicts a pixel-level mask for each detected object."
                    ),
                    description="",
                    has_quiz_items=True,
                ),
            ]

    service = AgentUnitSearchService(Repo(), FakeNavigation())
    response = await service.search(
        UnitSearchRequest(query="Mask RCNN", courseIds=["CS231n"]),
        allowed_course_ids=["CS231n"],
    )

    assert response.results[0].canonical_unit_id == "mask-rcnn"
    assert response.results[0].score > response.results[1].score
    assert response.trace.ranking_version == "unit_title_rerank_v1"


@pytest.mark.asyncio
async def test_search_reranks_broad_rcnn_to_family_before_mask_subtype():
    class Repo:
        async def search_canonical_units(self, terms, course_ids, limit, title_only=False):
            return [
                SimpleNamespace(
                    unit_id="mask-rcnn",
                    course_id="CS231n",
                    lecture_id="lecture-09",
                    lecture_title="Lecture 9: Object Detection, Image Segmentation, Visualizing and Understanding",
                    unit_name="Instance segmentation with Mask R-CNN",
                    summary="Mask R-CNN extends the R-CNN pipeline for instance segmentation.",
                    description="",
                    has_quiz_items=True,
                ),
                SimpleNamespace(
                    unit_id="rcnn-family",
                    course_id="CS231n",
                    lecture_id="lecture-09",
                    lecture_title="Lecture 9: Object Detection, Image Segmentation, Visualizing and Understanding",
                    unit_name="Object detection as classification plus localization and the R-CNN family",
                    summary=(
                        "R-CNN classifies proposal crops and refines boxes. Fast R-CNN shares "
                        "convolution over the image and region proposal networks refine boxes."
                    ),
                    description="",
                    has_quiz_items=True,
                ),
                SimpleNamespace(
                    unit_id="cnn-foundations",
                    course_id="CS231n",
                    lecture_id="lecture-05",
                    lecture_title="Lecture 5: Image Classification with CNNs",
                    unit_name="What convolutional networks are and why they matter",
                    summary="Convolutional networks use convolution and pooling layers.",
                    description="",
                    has_quiz_items=True,
                ),
            ]

    service = AgentUnitSearchService(Repo(), FakeNavigation())
    response = await service.search(
        UnitSearchRequest(query="RCNN", courseIds=["CS231n"]),
        allowed_course_ids=["CS231n"],
    )

    assert [result.canonical_unit_id for result in response.results[:2]] == [
        "rcnn-family",
        "mask-rcnn",
    ]
    assert response.results[1].score > response.results[2].score


@pytest.mark.asyncio
async def test_search_reranks_kim_cnn_above_generic_cnn_units():
    class Repo:
        async def search_canonical_units(self, terms, course_ids, limit, title_only=False):
            return [
                SimpleNamespace(
                    unit_id="deep-cnn",
                    course_id="CS224n",
                    lecture_id="lecture-16",
                    lecture_title="Lecture 16 - ConvNets and TreeRNNs",
                    unit_name="Deep CNN variants: batch norm, 1x1 conv, and VD-CNN",
                    summary="Deep CNN variants include residual conv blocks and VD-CNN.",
                    description="",
                    has_quiz_items=True,
                ),
                SimpleNamespace(
                    unit_id="kim-cnn",
                    course_id="CS224n",
                    lecture_id="lecture-16",
                    lecture_title="Lecture 16 - ConvNets and TreeRNNs",
                    unit_name="Kim CNN for sentence classification",
                    summary="Kim CNN applies filters over n-grams and max-pools for sentence classification.",
                    description="",
                    has_quiz_items=True,
                ),
                SimpleNamespace(
                    unit_id="vision-cnn",
                    course_id="CS231n",
                    lecture_id="lecture-05",
                    lecture_title="Lecture 5: Image Classification with CNNs",
                    unit_name="What convolutional networks are and why they matter",
                    summary="CNNs are image models built from convolution layers.",
                    description="",
                    has_quiz_items=True,
                ),
            ]

    service = AgentUnitSearchService(Repo(), FakeNavigation())
    response = await service.search(
        UnitSearchRequest(query="Kim CNN", courseIds=["CS224n", "CS231n"]),
        allowed_course_ids=["CS224n", "CS231n"],
    )

    assert response.results[0].canonical_unit_id == "kim-cnn"
    assert response.results[0].score > response.results[1].score
