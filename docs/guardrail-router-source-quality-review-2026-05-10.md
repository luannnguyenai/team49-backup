# Guardrail Router Source Quality Review - 2026-05-10

EduVidQA is excluded from this review because it already has dedicated preprocessing documentation under `data/eduvidqa/reports`.

Stats script:

```text
scripts/review_guardrail_router_sources.py
```

Local outputs:

```text
data/guardrail_router/source_review/source_quality_review.json
data/guardrail_router/source_review/source_quality_summary.csv
```

## Bottom line

These sources do not require blind random sampling. Each useful dataset has enough structure for deterministic filtering and stratified extraction:

- Internal question bank: quality gates, KP/unit/course metadata, grounding confidence, difficulty, question intent.
- CLINC150/OOS: intent labels and explicit OOS splits.
- CantTalkAboutThis: explicit `distractors` field.
- WildGuardMix: prompt harm labels, adversarial metadata, subcategory, refusal/harm metadata.
- JailBreakV-28K: attack `format`, safety `policy`, `transfer_from_llm`, source.
- MultiJail: language split, harm categories, source.
- PolyGuardPrompts: language, harm labels, adversarial metadata, subcategory.
- BeaverTails: `is_safe` and multi-label category metadata, but license is non-commercial.

## Source-by-source statistics

### Internal question bank

| Metric | Count |
| --- | ---: |
| total rows | 1,276 |
| qa_gate_passed | 1,276 |
| high grounded with KP/unit/course/lecture | 1,125 |
| can make hard cross-pair same lecture diff unit | 1,276 |
| can make medium cross-pair same course diff lecture | 1,276 |
| unique primary KP | 521 |
| unique units | 362 |

Distribution:

```text
course_id: CS224n 604, CS231n 381, CS230 291
difficulty: medium 767, easy 385, hard 124
intent: conceptual 577, diagnostic 259, procedural 252, application 188
grounding_confidence: high 1125, medium 151
```

Decision: quality extraction is strong.

Recommended extraction:

- ON_TOPIC: use `qa_gate_passed = true`, stratified by course, difficulty, and question intent.
- KP output: use `primary_kp_id`, but only when it appears in runtime `candidate_kp_ids`.
- Cross-pair negatives: generate deterministically by metadata, not random text pairing.
- Hard negatives: same lecture, different unit/KP.
- Medium negatives: same course, different lecture.

### CLINC150/OOS

| Metric | Count |
| --- | ---: |
| total rows | 23,700 |
| train | 15,000 |
| val | 3,000 |
| test | 4,500 |
| oos_train | 100 |
| oos_val | 100 |
| oos_test | 1,000 |
| unique train intents | 150 |

Decision: quality extraction is good for generic SAFE/OFF_TOPIC.

Recommended extraction:

- Use stratified sampling by intent plus explicit OOS rows.
- Keep 700-1,000 examples by selecting diverse intents instead of random rows.
- Cap or remove intents that may overlap with tutoring, such as `definition`, `translate`, and simple math-like questions, if the current lesson scope might allow them.

Limitation: CLINC gives easy/generic off-topic, not lesson-near hard negatives.

### CantTalkAboutThis

| Metric | Count |
| --- | ---: |
| dialogues | 1,093 |
| distractors | 5,465 |
| usable distractors 3-40 words | 5,465 |
| domains | 9 |

Top domains:

```text
banking 140, real estate 120, insurance 120, travel 120, health 120,
education 120, legal 120, taxes 119, computer troubleshooting 114
```

Decision: quality extraction is very strong for topic-control OFF_TOPIC because the dataset already marks distractors.

Recommended extraction:

- Extract `distractors[*].distractor` directly as SAFE/OFF_TOPIC.
- Stratify by domain to avoid overrepresenting banking.
- Treat as easy/medium off-topic; do not use as hard lesson-scope negative.

Limitation: English only.

### WildGuardMix

| Metric | Count |
| --- | ---: |
| total rows | 88,484 |
| harmful prompts | 46,970 |
| unharmful prompts | 41,488 |
| adversarial true | 41,766 |
| bypass pattern any | 4,153 |
| harmful with bypass pattern | 3,107 |
| safe prompt-only length 8-1200 | 38,189 |

Top prompt labels:

```text
harmful 46970, unharmful 41488, missing 26
```

Top subcategories include:

```text
benign 41514
others 10825
social stereotypes / unfair discrimination 6419
false or misleading information 4128
sensitive organization/government information 3135
toxic language / hate speech 3061
violence and physical harm 2941
private information individual 2616
fraud / illegal activities 2340
cyberattack 1647
```

Decision: quality extraction is strong. Do not sample blindly.

Recommended extraction:

- UNSAFE: sample from `prompt_harm_label = harmful`, stratified by `subcategory`.
- SAFE/OFF_TOPIC support: sample from `prompt_harm_label = unharmful`, length-filtered, stratified by benign/adversarial metadata.
- JAILBREAK: use bypass/prompt-injection patterns plus `adversarial` metadata; do not label every `adversarial=true` row as JAILBREAK.
- Router input should use prompt only, not response.

Limitation: bypass regex is conservative; final extraction should include a reviewed pattern list.

### JailBreakV-28K

| Metric | Count |
| --- | ---: |
| total rows | 30,000 |
| text-router candidates: Template/Logic/Persuade + transfer_from_llm | 20,000 |
| no-image-dependency candidates | 20,000 |
| unique policies | 17 |
| transfer_from_llm true | 20,000 |

Format distribution:

```text
Template 18336
figstep 2000
SD_typo 2000
SD 2000
typo 2000
missing 2000
Persuade 1368
Logic 296
```

Top policies:

```text
Malware 3953
Illegal Activity 3555
Fraud 3044
Economic Harm 2575
Bias 2508
Government Decision 1899
Unethical Behavior 1818
Violence 1548
Hate Speech 1542
Physical Harm 1463
```

Decision: quality extraction is strong.

Recommended extraction:

- Use `jailbreak_query` as JAILBREAK input.
- Filter to text-oriented methods: Template, Logic, Persuade.
- Stratify by `policy` and `format`.
- Use `redteam_query` only as metadata or separate UNSAFE baseline, not as jailbreak input.

Limitation: many rows are MLLM/image-oriented; exclude FigStep/query/image-dependent items for the text router.

### MultiJail

| Metric | Count |
| --- | ---: |
| total rows | 3,150 |
| languages | 10 |
| Vietnamese rows | 315 |
| English rows | 315 |
| non-English rows | 2,835 |
| unique harm categories | 18 |

Language distribution:

```text
ar 315, bn 315, en 315, it 315, jv 315,
ko 315, sw 315, th 315, vi 315, zh 315
```

Top harms:

```text
Violence & incitement 850
Discrimination & injustice 510
Hate speech & offensive language 380
Bullying & harassment 340
Non-violent unethical behavior 300
Conspiracy theories & misinformation 290
Theft 280
Weapons 220
Adult content 200
Substance abuse & banned substances 190
Terrorism & organized crime 180
Fraud & deception 170
```

Decision: quality extraction is strong for multilingual UNSAFE and eval slices.

Recommended extraction:

- Stratify by language and harm category.
- Use Vietnamese rows directly for multilingual production coverage.
- Treat base rows as UNSAFE, not automatically JAILBREAK.
- Create JAILBREAK/code-switch variants only through controlled wrapper augmentation, and keep original prompt as unsafe baseline.

### PolyGuardPrompts

| Metric | Count |
| --- | ---: |
| total rows | 29,325 |
| harmful prompts | 12,818 |
| unharmful prompts | 16,065 |
| adversarial harmful | 5,797 |
| languages | 17 |
| safe prompt-only length 8-1200 | 15,335 |

Languages:

```text
English, Hindi, French, Italian, German, Portuguese, Thai, Spanish,
Czech, Swedish, Chinese, Arabic, Dutch, Korean, Polish, Russian, Japanese
```

Each language has 1,725 rows.

Decision: quality extraction is strong as multilingual safety supplement.

Recommended extraction:

- Stratify by language and `prompt_harm_label`.
- Use `adversarial` as metadata/eval slice, not direct JAILBREAK label.
- Useful fallback/supplement to WildGuardMix.

Limitations:

- No Vietnamese.
- It is benchmark-like and only has a `test` split in this repo, so avoid overusing it if you want to preserve it as eval.

### BeaverTails optional

| Metric | Count |
| --- | ---: |
| total rows in 30k train | 27,186 |
| unsafe prompts | 15,582 |
| safe prompts | 11,604 |
| unsafe prompt-only length 8-1200 | 15,582 |
| safe prompt-only length 8-1200 | 11,597 |

Top categories:

```text
violence/aiding/incitement 6927
non-violent unethical behavior 4816
financial/property/theft 2566
hate speech/offensive language 2537
discrimination/stereotype/injustice 2346
drug/weapons/banned substance 1527
privacy violation 1397
```

Decision: quality extraction is possible, but use is license-constrained.

Recommended extraction:

- Only use `prompt`, `is_safe`, and `category`.
- Do not train router on response text.
- Use as optional unsafe fallback if CC-BY-NC-4.0 is acceptable.

## Final decision

The fine-tune dataset should not be built by pure random sampling.

Recommended extraction strategy:

| Target group | Best extraction method |
| --- | --- |
| ON_TOPIC | Internal question bank quality filters + EduVidQA existing processed pipeline |
| OFF_TOPIC easy | CLINC150 stratified by intent + CantTalkAboutThis distractor field |
| OFF_TOPIC medium/hard | Deterministic cross-pair from question bank/EduVidQA metadata |
| UNSAFE | WildGuardMix by `prompt_harm_label` and `subcategory`; MultiJail by language/harm; optional BeaverTails by `is_safe/category` |
| JAILBREAK | JailBreakV by `format/policy/transfer_from_llm`; WildGuardMix harmful+bypass pattern; controlled obfuscation/code-switch wrappers |
| Multilingual | MultiJail language splits; PolyGuardPrompts language field; Vietnamese augmentation from internal course queries |
| AMBIGUOUS | Rule/template generation with context/no-context variants |

Random sampling should only be used inside a filtered stratum after quality filters are applied, for example:

```text
sample 100 WildGuard harmful cyberattack prompts
sample 80 JailBreakV Template prompts from Malware policy
sample 50 CLINC utterances from each selected safe off-topic intent
sample 100 MultiJail Vietnamese prompts across harm categories
```

This gives a controlled, explainable dataset rather than a random mixture of public sources.

