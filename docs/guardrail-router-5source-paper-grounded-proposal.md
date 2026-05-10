# Guardrail Router 5-Source Paper-Grounded Proposal

Scope:

- Keep: CantTalkAboutThis, CLINC150/OOS, WildGuardMix, JailBreakV-28K, MultiJail
- Exclude: EduVidQA from this note, PolyGuardPrompts, BeaverTails

This proposal uses the paper/card intent of each dataset to choose quality strata before sampling.

## Available quality capacity

| Source | Quality-filtered capacity | What it is good for |
| --- | ---: | --- |
| CantTalkAboutThis | 5,462 clean distractors; 900 after cap 100/domain | SAFE/OFF_TOPIC topic-control |
| CLINC150/OOS | 22,800 after excluding lesson-overlap intents; 1,160 after cap 8/intent | SAFE/OFF_TOPIC generic OOD |
| WildGuardMix UNSAFE | 40,867 harmful, length-filtered, non-bypass prompts; 1,680 after cap 120/subcategory | UNSAFE |
| WildGuardMix JAILBREAK-like | 2,538 harmful + bypass-pattern prompts; 963 after cap 80/subcategory | JAILBREAK supplement |
| JailBreakV-28K | 19,996 clean text-transfer attacks; 1,136 after cap 35/format-policy | JAILBREAK main |
| MultiJail | 3,141 clean multilingual unsafe prompts; 900 after cap 90/language; 315 Vietnamese | Multilingual UNSAFE + eval slice |

None of these sources require blind random sampling. Randomness should only be used inside a filtered stratum.

## Recommended v1 quotas from these 5 sources

| Router group | Source | Quota | Selector |
| --- | --- | ---: | --- |
| OFF_TOPIC easy | CantTalkAboutThis | 800 | `distractors[*].distractor`, nonempty, 3-40 words, no bypass pattern, stratify by domain |
| OFF_TOPIC generic | CLINC150/OOS | 700 | explicit OOS plus capped intent samples, excluding lesson-overlap intents |
| UNSAFE | WildGuardMix | 1,200 | `prompt_harm_label=harmful`, 5-220 words, no bypass pattern, stratify by subcategory |
| JAILBREAK | WildGuardMix | 300 | harmful + bypass/prompt-injection pattern, stratify by subcategory, keep adversarial as metadata |
| JAILBREAK | JailBreakV-28K | 900 | `jailbreak_query`, `format in {Template, Logic, Persuade}`, `transfer_from_llm=true`, stratify by policy/format |
| UNSAFE multilingual | MultiJail | 500 | prompt, char length 8-1200, stratify by language and harm category |
| JAILBREAK multilingual | MultiJail-derived | 150-250 | controlled bilingual/bypass wrappers over selected MultiJail unsafe prompts |

Total from these five sources: about 4,550-4,650 samples.

This should be combined with:

- EduVidQA processed ON_TOPIC: about 4,000
- `open_qa_eval` tier A/B ON_TOPIC: about 900-1,000
- cross-pair negatives from EduVidQA + open_qa_eval: about 2,500-3,200
- ambiguous/contextual templates: about 400-600

Full v1 total: about 12k-14k.

## Source-specific selection details

### CantTalkAboutThis

Paper/card intent: topic-control via distractor turns.

Use:

```text
source field: distractors[*].distractor
label: SAFE + OFF_TOPIC + SOFT_REFUSE_REDIRECT
quota: 800
```

Selection:

- cap around 90 per domain
- keep scenario/domain as metadata
- hold out some domains or the human test set for eval if possible

Why this is quality data:

- Off-topic turns are explicitly annotated as distractors, not inferred.

### CLINC150/OOS

Paper intent: intent classification plus out-of-scope prediction.

Use:

```text
source fields: utterance + intent + split
label: SAFE + OFF_TOPIC + SOFT_REFUSE_REDIRECT
quota: 700
```

Selection:

- include explicit OOS rows
- sample capped rows from remaining intents
- exclude/downweight lesson-overlap intents:
  - `definition`
  - `translate`
  - `spelling`
  - `calculator`
  - `measurement_conversion`
  - `what_is_your_name`

Why this is quality data:

- It gives intent-diverse safe off-topic examples, and explicit OOS rows are aligned with router behavior.

### WildGuardMix

Paper intent: one-stop moderation across prompt harmfulness, response harmfulness, and refusal. For router training, use prompt harmfulness only.

Use:

```text
UNSAFE quota: 1,200
JAILBREAK quota: 300
```

Selection:

- UNSAFE:
  - `prompt_harm_label=harmful`
  - prompt length 5-220 words
  - no bypass pattern
  - stratify by `subcategory`
- JAILBREAK:
  - `prompt_harm_label=harmful`
  - bypass/prompt-injection pattern
  - stratify by `subcategory`
  - keep `adversarial` as metadata, not direct label

Notes:

- `prompt_harm_agreement` exists for only 1,699 of 88,458 labeled rows, so use it as optional eval-grade metadata, not as a required training filter.
- Use prompt only; do not feed response text into router samples.

Why this is quality data:

- Harm labels and risk subcategories are explicit, and bypass-pattern filtering separates unsafe from jailbreak-like rows.

### JailBreakV-28K

Paper/card intent: jailbreak robustness, including text-transfer and image-based MLLM attacks.

Use:

```text
source field: jailbreak_query
label: JAILBREAK + N_A + SAFETY_REFUSE
quota: 900
```

Selection:

- include only text-transfer methods:
  - Template
  - Logic
  - Persuade
- require `transfer_from_llm=true`
- exclude image-dependent methods for text-router training
- stratify by `policy` and `format`

Why this is quality data:

- Attack method and violated safety policy are explicit, so we can build a balanced jailbreak set instead of sampling raw rows.

### MultiJail

Paper intent: multilingual safety/jailbreak stress test from unsafe prompts translated into 9 non-English languages, including Vietnamese.

Use:

```text
base rows: UNSAFE multilingual
derived wrappers: JAILBREAK multilingual/code-switch
quota: 500 unsafe + 150-250 derived jailbreak
```

Selection:

- base UNSAFE:
  - char length 8-1200
  - stratify by language and harm category
  - include at least 150 Vietnamese rows if possible
- derived JAILBREAK:
  - apply controlled wrappers to selected unsafe prompts
  - examples: Vietnamese role override, English+Vietnamese scope bypass, "ignore lesson scope"

Why this is quality data:

- Language and harm coverage are explicit. It fills the gap that WildGuardMix/JailBreakV do not solve well: Vietnamese and multilingual safety.

## Final recommendation

Use the 5-source public mix as a targeted supplement, not the center of the router dataset. The center should remain lesson data:

```text
Lesson-scope core:
- EduVidQA ON_TOPIC
- open_qa_eval ON_TOPIC
- derived cross-pair OFF_TOPIC

Public guardrail supplement:
- CantTalkAboutThis
- CLINC150/OOS
- WildGuardMix
- JailBreakV-28K
- MultiJail
```

For the public guardrail part, a strong v1 target is:

```text
CantTalkAboutThis: 800
CLINC150/OOS: 700
WildGuardMix UNSAFE: 1,200
WildGuardMix JAILBREAK: 300
JailBreakV-28K: 900
MultiJail UNSAFE: 500
MultiJail-derived JAILBREAK: 150-250
```

This gives about 4.5k public guardrail samples, enough for robustness without turning the router into a general safety classifier.

