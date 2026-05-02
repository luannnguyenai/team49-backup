import json
from pathlib import Path


FIXTURE_PATH = Path("tests/fixtures/agent/golden_eval_cases.json")


def _load_dataset() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_golden_agentic_rag_eval_dataset_is_reviewable_and_multilingual():
    dataset = _load_dataset()

    assert dataset["version"] >= 1
    assert "product contracts" in dataset["description"]
    assert dataset["defaults"]["no_domain_keyword_maps"] is True
    assert any(
        "Do not copy fixture terms into production routing logic" in rule
        for rule in dataset["review_rules"]
    )

    cases = dataset["cases"]
    assert len(cases) >= 24

    ids = [case["id"] for case in cases]
    assert len(ids) == len(set(ids))
    assert {"vi", "en"}.issubset({case["language"] for case in cases})

    for case in cases:
        assert case["id"]
        assert case["category"]
        assert case["turns"]
        assert case["turns"][-1]["role"] == "user"
        assert case["turns"][-1]["text"].strip()
        assert isinstance(case["expected"], dict)
        assert isinstance(case["forbidden"], dict)
        assert "exact_answer" not in case["expected"]


def test_golden_agentic_rag_eval_dataset_covers_required_behavior_groups():
    categories = {case["category"] for case in _load_dataset()["cases"]}

    assert {
        "rag_initial_retrieval",
        "rag_followup_same_topic",
        "source_limited_answer",
        "contextual_evidence_gap",
        "new_topic_after_context",
        "thread_memory",
        "scope_current_path_first",
        "scope_expansion_approval",
        "too_many_results",
        "pending_retrieval_followup",
        "failed_request_retry",
        "routing_lexical_trap",
        "assessment_intent_boundary",
        "planner_mode_boundary",
    }.issubset(categories)


def test_golden_agentic_rag_eval_dataset_encodes_core_safety_invariants():
    cases = {case["id"]: case for case in _load_dataset()["cases"]}

    assert (
        cases["vi_new_topic_cnn_after_yolo"]["forbidden"]["must_not_reuse_active_yolo_citation"]
        is True
    )
    assert (
        cases["en_new_topic_cnn_after_yolo"]["forbidden"]["must_not_reuse_active_yolo_citation"]
        is True
    )

    assert (
        cases["vi_yolo_loss_function_no_direct_source"]["forbidden"][
            "must_not_cite_generic_loss_as_yolo_loss_evidence"
        ]
        is True
    )
    assert (
        cases["en_yolo_loss_function_no_direct_source"]["forbidden"][
            "must_not_invent_yolo_loss_formula"
        ]
        is True
    )

    assert (
        cases["vi_current_path_first_no_silent_expansion"]["expected"]["must_search_current_path_first"]
        is True
    )
    assert (
        cases["vi_scope_expansion_approval_continues_search"]["expected"][
            "must_resume_pending_clarification"
        ]
        is True
    )
    assert (
        cases["vi_show_top_results_after_refinement_offer"]["forbidden"][
            "must_not_append_top_result_to_query_text"
        ]
        is True
    )

    assert (
        cases["vi_memory_recall_visible_thread"]["expected"]["must_use_visible_thread_memory"]
        is True
    )
    assert (
        cases["vi_memory_recall_visible_thread"]["forbidden"]["must_not_include_hidden_reasoning"]
        is True
    )


def test_golden_agentic_rag_eval_dataset_keeps_planner_actions_out_of_chat_side_effects():
    cases = {case["id"]: case for case in _load_dataset()["cases"]}

    assert cases["vi_repath_is_planner_mode_future"]["expected"]["must_require_confirmation_or_planner_mode"] is True
    assert (
        cases["vi_repath_is_planner_mode_future"]["forbidden"][
            "must_not_mutate_active_path_from_chat_text_only"
        ]
        is True
    )
    assert (
        cases["en_repath_is_planner_mode_future"]["forbidden"][
            "must_not_mutate_active_path_from_chat_text_only"
        ]
        is True
    )
