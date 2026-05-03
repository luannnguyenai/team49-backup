# P4 — Evaluation and Model Packaging

## Goal

Select the best ablation run using domain-first evaluation rules, then package the chosen adapter for downstream serving.

## Core principle

Do not choose the winner by training loss alone.

The winning run must show:

- stronger internal domain performance
- better English explanation quality
- acceptable regression on secondary academic benchmarks

## Evaluation stack

### 1. Internal domain eval

This is the main gate.

Suggested slices:

| Slice | What it tests |
|---|---|
| Concept explanation | explain a course concept correctly |
| Comparison | contrast related methods accurately |
| Applied reasoning | explain observed training or modeling behavior |

Suggested human rubric:

| Metric | Scale |
|---|---|
| Correctness | 1-5 |
| Completeness | 1-5 |
| Clarity | 1-5 |
| Hallucination | yes/no |
| Stepwise structure | yes/no |

### 2. Academic regression eval

Use:

- MMLU selected subjects
- MMLU-Pro
- TheoremQA

Purpose:

- detect over-specialization
- report academically defensible benchmark deltas

### 3. Style eval

Use filtered ELI5 dev/test as a style-only benchmark.

Suggested rubric:

| Metric | What it checks |
|---|---|
| Coherence | logical flow |
| Pedagogical quality | tutor-like explanation |
| Conciseness | long enough, not rambling |
| English fluency | natural written English |
| Factual safety | no invented claims |

## Decision rules

### Accept

- internal domain score improves
- style score improves clearly
- secondary benchmark regression stays small

### Reject

- ELI5 fluency rises while domain correctness drops
- answers become more verbose but less precise
- hallucination rate increases

## Ablation comparison

Compare:

- Run A: domain only
- Run B: domain + 10% ELI5
- Run C: domain + 20% ELI5
- Run D: domain + 30% ELI5

Recommended interpretation:

- If B improves style without hurting domain, keep exploring upward.
- If C is best overall, treat it as the likely v1 candidate.
- If D drifts, keep it as evidence for the upper bound rather than the deployment choice.

## Packaging

Once the winner is selected:

- save adapter weights
- record exact config and dataset mix
- produce a short evaluation report with per-run deltas

## Quantization note

Quantization is now a downstream serving concern, not a design driver for the fine-tuning strategy. Do not let quantization constraints distort the training-data plan.
