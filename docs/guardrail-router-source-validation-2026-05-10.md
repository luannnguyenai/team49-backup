# Guardrail Router Source Validation - 2026-05-10

## What was validated

Validation script:

```text
scripts/validate_guardrail_router_sources.py
```

Output directory:

```text
data/guardrail_router/source_validation
```

Note: `data/**` is gitignored in this repo, so downloaded metadata/sample rows are local artifacts, not tracked source changes.

## Result summary

| Source | Status | Notes |
| --- | --- | --- |
| EduVidQA | Usable | Local processed data exists; `valid_context_samples_window_120 = 4178`, enough for ~4k ON_TOPIC samples. |
| Internal question bank | Usable | Local canonical bank has 1276 rows and is usable for ON_TOPIC plus cross-pair negatives. |
| CantTalkAboutThis | Usable | Hugging Face schema matched expected topic-control fields; license reported as `cc-by-4.0`. |
| CLINC150/OOS | Usable | GitHub `data_full.json` downloaded; splits match expected in-scope/OOS structure. |
| JailBreakV-28K | Usable | Hugging Face schema matched expected jailbreak fields; text-oriented subset can be filtered by `format` and `transfer_from_llm`. |
| MultiJail | Usable with mapping | Schema has `prompt`, `harms`, `source`; language is represented by split name such as `vi`, not a `language` column. |
| WildGuardMix | Usable with HF_TOKEN | Repo is gated. After loading `HF_TOKEN` from `.env`, direct parquet download worked and schema matched. Hugging Face datasets-server still returned 401, so use direct Hub file download for this source. |
| BeaverTails optional fallback | Usable but license-limited | Schema matched; license reported as `cc-by-nc-4.0`, so avoid for commercial production training unless license is acceptable. |
| PolyGuardPrompts optional fallback | Usable | Schema matched multilingual safety fields; license reported as `cc-by-4.0`. Good fallback if WildGuardMix access is blocked. |

## Local source details

EduVidQA:

```json
{
  "usable_rows_with_timestamp": 4196,
  "valid_context_samples_window_120": 4178,
  "unique_videos_valid": 258
}
```

Internal question bank:

```json
{
  "total": 1276,
  "qa_gate_passed": 1276,
  "with_primary_kp_id": 1276,
  "with_unit_id": 1276,
  "with_course_id": 1276
}
```

CLINC150/OOS downloaded split counts:

```json
{
  "train": 15000,
  "val": 3000,
  "test": 4500,
  "oos_train": 100,
  "oos_val": 100,
  "oos_test": 1000
}
```

## Feasibility conclusion

The dataset plan is feasible.

1. Keep WildGuardMix as the main safety source, but load it through authenticated Hugging Face Hub file download rather than datasets-server.
2. Keep `ToxicityPrompts/PolyGuardPrompts` as a useful multilingual safety supplement.
3. Use BeaverTails only as an optional prompt-only source if the non-commercial license is acceptable for the target use.
4. Keep JailBreakV-28K for English jailbreak style and MultiJail for Vietnamese/multilingual unsafe and jailbreak eval slices.
5. Keep EduVidQA and the internal question bank as the center of the dataset; these are already locally available and sufficient for the ON_TOPIC and cross-pair parts.

## Mapping notes

Use common runtime labels:

```text
SAFE | UNSAFE | JAILBREAK
ON_TOPIC | OFF_TOPIC | AMBIGUOUS | N_A
ALLOW_LESSON_ANSWER | SOFT_REFUSE_REDIRECT | ASK_CLARIFY | SAFETY_REFUSE
```

Do not create runtime labels such as `JAILBREAK_MULTILINGUAL` or `OBFUSCATED_JAILBREAK`. Keep those as `attack_type`, `language`, or `eval_slice`.

MultiJail mapping:

```text
split name -> language
prompt -> user_query
harms -> safety category metadata
source -> provenance metadata
```

WildGuardMix mapping if access is granted:

```text
prompt -> user_query
prompt_harm_label=harmful + bypass intent -> JAILBREAK
prompt_harm_label=harmful without bypass intent -> UNSAFE
prompt_harm_label=unharmful -> SAFE, usually OFF_TOPIC for lesson router
adversarial -> metadata only, not direct label
```

JailBreakV-28K mapping:

```text
jailbreak_query -> user_query
redteam_query -> original harmful prompt metadata
format=Template -> attack_type=jailbreak_template
format=Logic/Persuade -> attack_type=prompt_injection or unknown
transfer_from_llm=true -> prioritize for text router
```
