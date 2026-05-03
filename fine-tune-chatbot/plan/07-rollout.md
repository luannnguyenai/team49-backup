# P7 — Rollout

## Goal

Roll out the selected English-only tutor safely after it passes the training and evaluation gates.

## Stage model

### Stage 0 — Internal validation

- manual checks on representative AI/ML/NLP/CV questions
- verify English-only output
- confirm answers remain domain-grounded
- run a small multimodal smoke pass on representative diagrams or screenshots

### Stage 1 — Limited canary

- route a small share of tutor traffic to the new model
- compare outputs against the previous baseline
- monitor error rate and response quality

### Stage 2 — Expanded canary

- increase traffic only if correctness and latency remain acceptable

### Stage 3 — Full rollout

- switch fully once the canary stays stable
- keep rollback available

## Metrics to watch

| Metric | Why it matters |
|---|---|
| tutor error rate | operational stability |
| response latency | usability |
| fallback rate | deployment health |
| human review score | answer quality |
| hallucination reports | factual safety |
| multimodal request success rate | vision-serving reliability |

## Risk register

| Risk | Mitigation |
|---|---|
| Domain drift from ELI5 | cap ELI5, prefer smallest effective ratio |
| Verbose but wrong answers | domain-first eval gate |
| Benchmark regression | check MMLU selected, MMLU-Pro, TheoremQA |
| English inconsistency | normalization and language checks |

## Rollback

- revert provider selection to the previous baseline
- disable the new model endpoint if quality degrades
- retain run reports so rollback reasons are explicit
