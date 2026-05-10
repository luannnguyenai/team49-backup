# Guardrail Router V2 Build Report

Generated: 2026-05-10

## Output

- Dataset directory: `data/guardrail_router/v2`
- Builder: `scripts/build_guardrail_router_v2_dataset.py`
- OpenQA review queue: `data/guardrail_router/v2/openqa_review_candidates.csv`

## Schema

```json
{
  "safety_label": "SAFE | HARMFUL",
  "topic_label": "ON_TOPIC | OFF_TOPIC | AMBIGUOUS | N_A",
  "action": "ALLOW_LESSON_ANSWER | SOFT_REFUSE_REDIRECT | ASK_CLARIFY | SAFETY_REFUSE",
  "attack_type": "none | harmful_request | schema_override | policy_override | role_override | scope_override | kp_injection | obfuscation | jailbreak_template | multilingual_jailbreak | unknown",
  "selected_kp_ids": []
}
```

Production routing should use `safety_label` and `action`; `attack_type` is auxiliary.

## Current Counts

| Group | Count |
|---|---:|
| Total | 13,513 |
| Train | 10,756 |
| Validation | 1,041 |
| Test | 1,716 |
| SAFE::ON_TOPIC | 5,107 |
| SAFE::OFF_TOPIC | 4,326 |
| SAFE::AMBIGUOUS | 440 |
| HARMFUL::N_A | 3,640 |

## HARMFUL Mix

| Source/group | Count |
|---|---:|
| WildGuardMix | 1,500 |
| JailBreakV-28K | 900 |
| MultiJail | 500 |
| MultiJail-derived | 200 |
| Router-injection synthetic | 300 |
| Harmful off-topic-like synthetic | 240 |
| Total HARMFUL | 3,640 |

Attack type distribution:

| attack_type | Count |
|---|---:|
| harmful_request | 1,684 |
| policy_override | 851 |
| jailbreak_template | 416 |
| multilingual_jailbreak | 181 |
| schema_override | 66 |
| scope_override | 65 |
| role_override | 64 |
| kp_injection | 60 |
| obfuscation | 13 |

## OpenQA Handling

After reviewing and filling `openqa_review_labels.csv`:

| OpenQA bucket | Count |
|---|---:|
| Included as ON_TOPIC | 900 |
| Included as AMBIGUOUS | 53 |
| Dropped for review | 0 |
| Needs manual review: generic | 0 |
| Needs manual review: option-dependent | 0 |

The review file labels 180 previously flagged rows as `ON_TOPIC` and 53 option/choice-dependent rows as `AMBIGUOUS`. Regex only created the review queue; the labels are stored in `openqa_review_labels.csv`.

## Validation Checks

- Bad target schema/enums/invariants: 0
- Input reference/answer leakage: 0
- Cross-pair same unit: 0
- Cross-pair shared primary KP: 0
- ON_TOPIC with empty `selected_kp_ids`: 4,000 / 5,130, expected from EduVidQA because EduVidQA has no internal KP ids.

## V2 Hardening Checks

Reviewer issues addressed in the latest build:

| Check | Result |
|---|---:|
| SAFE::AMBIGUOUS in test | 111 |
| Router injection per attack type | 42 train / 9 validation / 9 test |
| Benign router terms | 66 train / 12 validation / 12 test |
| Public/safety sources using real lesson scopes | Yes |
| HARMFUL rows with empty candidate KPs | 0 / 3,640 |
| OFF_TOPIC rows with empty candidate KPs | 0 / 4,326 |
| Exact input cross-split overlap groups | 0 |
| Duplicate extra rows | 81 |
| Cross-pair same unit | 0 |
| Cross-pair shared primary KP | 0 |

Router-injection language mix, rough heuristic:

| Language bucket | Count |
|---|---:|
| English | 173 |
| Vietnamese | 64 |
| Code-switch | 119 |
| Other/neutral | 34 |

## Next Manual Step

Optional next review: inspect `data/guardrail_router/v2/openqa_review_labels.csv` and adjust any row if you disagree with the current labels:

- `ON_TOPIC`: query is answerable in the current unit/KP without hidden options.
- `AMBIGUOUS`: query is in-scope but cannot be answered confidently without missing choices/options or a referent.
- `DROP`: assessment artifact or unclear even after context review.

The current build already uses `openqa_review_labels.csv`. Rebuild with `python scripts/build_guardrail_router_v2_dataset.py --output-dir data/guardrail_router/v2` after edits.

## Runtime Policy Note

Evaluation found that some harmful-looking requests can be predicted as `SAFE::OFF_TOPIC` rather than `HARMFUL::N_A`. They are not allowed, but production must avoid sending raw user text to the answer model for any non-ALLOW route.

Recommended rule:

```python
if action != "ALLOW_LESSON_ANSWER":
    return deterministic_template_or_sanitized_payload()
```

Do not use `attack_type` as the masking gate. Use `action` and `safety_label`.

Latest data changes add `HARMFUL_OFFTOPIC_LIKE` rows and relabel benign router terms as ON_TOPIC/OFF_TOPIC/AMBIGUOUS according to scope instead of forcing all to ON_TOPIC.
