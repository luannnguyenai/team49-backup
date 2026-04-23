"""Centralized repository data paths used by scripts and services."""

from __future__ import annotations

from pathlib import Path


DATA_DIR = Path("data")

BOOTSTRAP_DIR = DATA_DIR / "bootstrap"
COURSES_DIR = DATA_DIR / "courses"
WORKING_DIR = DATA_DIR / "working"
FINAL_ARTIFACTS_DIR = DATA_DIR / "final_artifacts" / "cs224n_cs231n_v1"
CANONICAL_ARTIFACTS_DIR = FINAL_ARTIFACTS_DIR / "canonical"

CS224N_DIR = COURSES_DIR / "CS224n"
CS231N_DIR = COURSES_DIR / "CS231n"

COURSES_FILE = BOOTSTRAP_DIR / "courses.json"
OVERVIEWS_FILE = BOOTSTRAP_DIR / "overviews.json"
UNITS_FILE = BOOTSTRAP_DIR / "units.json"
KG_BRIDGES_FILE = BOOTSTRAP_DIR / "kg_bridges.yaml"
MODULES_FILE = BOOTSTRAP_DIR / "modules.json"
TOPICS_FILE = BOOTSTRAP_DIR / "topics.json"
QUESTION_BANK_FILE = BOOTSTRAP_DIR / "question_bank.json"

P2_BUNDLE_FILE = WORKING_DIR / "p2" / "p2_input_bundle.json"
P3_INPUTS_DIR = WORKING_DIR / "p3_inputs"
P5_INPUT_FILE = WORKING_DIR / "p5" / "p5_input_cs224n_cs231n.json"

P2_OUTPUT_FILE = FINAL_ARTIFACTS_DIR / "p2_output_rationale_repaired.json"
P5_OUTPUT_FILE = FINAL_ARTIFACTS_DIR / "p5_output.json"
P5_TRANSITIVE_PRUNED_FILE = FINAL_ARTIFACTS_DIR / "p5_output_transitive_pruned.json"
GPT54_EDGE_LABELS_FILE = FINAL_ARTIFACTS_DIR / "gpt54_edge_labels.json"

MODEL_EXPERIMENTS_DIR = FINAL_ARTIFACTS_DIR / "model_experiments"
MODERNBERT_EDGE_SCORES_FILE = MODEL_EXPERIMENTS_DIR / "modernbert_edge_scores.json"
MODERNBERT_MASKED_V2_FILE = MODEL_EXPERIMENTS_DIR / "modernbert_edge_scores_masked_v2.json"
MODERNBERT_LARGE_MASKED_V2_FILE = MODEL_EXPERIMENTS_DIR / "modernbert_large_edge_scores_masked_v2.json"
SCIBERT_MASKED_V2_FILE = MODEL_EXPERIMENTS_DIR / "scibert_edge_scores_masked_v2.json"
EDGE_SCORING_INPUT_BUNDLE_FILE = MODEL_EXPERIMENTS_DIR / "edge_scoring_input_bundle.json"
EDGE_SCORING_INPUT_COMBO_FILE = MODEL_EXPERIMENTS_DIR / "edge_scoring_input_bundle_for_combo.json"
EDGE_SCORING_INPUT_NO_GPT_FILE = MODEL_EXPERIMENTS_DIR / "edge_scoring_input_no_gpt_bundle.json"

KG_VISUALIZATIONS_DIR = FINAL_ARTIFACTS_DIR / "kg_visualizations"
CANONICAL_MANIFEST_FILE = CANONICAL_ARTIFACTS_DIR / "manifest.json"
CANONICAL_VALIDATION_REPORT_FILE = CANONICAL_ARTIFACTS_DIR / "validation_report.json"
