# Guardrail Router V1 Build Report

Build output:

```text
data/guardrail_router/v1
```

Files:

```text
train.jsonl
validation.jsonl
test.jsonl
all.jsonl
manifest.json
```

Builder:

```text
scripts/build_guardrail_router_v1_dataset.py
```

Tests:

```text
tests/test_build_guardrail_router_v1_dataset.py
```

## Target schema

Router targets are label-only JSON:

```json
{
  "safety_label": "SAFE | UNSAFE | JAILBREAK",
  "topic_label": "ON_TOPIC | OFF_TOPIC | AMBIGUOUS | N_A",
  "action": "ALLOW_LESSON_ANSWER | SOFT_REFUSE_REDIRECT | ASK_CLARIFY | SAFETY_REFUSE",
  "attack_type": "none | prompt_injection | role_override | obfuscation | jailbreak_template | multilingual_jailbreak | unknown",
  "selected_kp_ids": []
}
```

No answer text, refusal prose, or numeric confidence is included in target outputs.

## Counts

Total samples: 12,850

| Split | Count |
| --- | ---: |
| train | 10,490 |
| validation | 915 |
| test | 1,445 |

By source:

| Source | Count |
| --- | ---: |
| EduVidQA | 4,000 |
| open_qa_eval | 950 |
| cross_pair_openqa | 2,800 |
| CantTalkAboutThis | 800 |
| CLINC150/OOS | 700 |
| WildGuardMix | 1,500 |
| JailBreakV-28K | 900 |
| MultiJail | 500 |
| MultiJail-derived | 200 |
| ambiguous_template | 500 |

By route group:

| Route group | Count |
| --- | ---: |
| ON_TOPIC | 4,950 |
| ON_TOPIC_SHORT_CONTEXTUAL | 150 |
| OFF_TOPIC | 4,300 |
| UNSAFE | 1,700 |
| JAILBREAK | 1,400 |
| AMBIGUOUS | 350 |

By action:

| Action | Count |
| --- | ---: |
| ALLOW_LESSON_ANSWER | 5,100 |
| SOFT_REFUSE_REDIRECT | 4,300 |
| SAFETY_REFUSE | 3,100 |
| ASK_CLARIFY | 350 |

## Verification

Commands run:

```bash
rtk uv run pytest tests/test_build_guardrail_router_v1_dataset.py -q
rtk bash -lc 'set -a; source .env; set +a; python scripts/build_guardrail_router_v1_dataset.py --output-dir data/guardrail_router/v1'
rtk python -m py_compile scripts/build_guardrail_router_v1_dataset.py
```

Integrity checks:

```text
target schema violations: 0
unsafe/jailbreak invariant violations: 0
output answer/confidence/refusal leaks: 0
input answer/reference marker leaks: 0
EduVidQA user-query extraction failures: 0
```

## Notes

- Public guardrail sources are selected with paper-grounded filters, not raw random sampling.
- Random sampling is used only inside filtered strata.
- `HF_TOKEN` is loaded from `.env` for gated WildGuardMix access during build.
- `data/**` is gitignored, so generated JSONL files are local artifacts unless explicitly tracked via another mechanism.

