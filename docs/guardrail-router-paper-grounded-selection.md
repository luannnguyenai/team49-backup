# Paper-Grounded Dataset Selection for Guardrail Router

This note converts the selection/curation logic from the relevant dataset papers/cards into extraction rules for the Qwen3.5-0.8B lesson-scope router.

EduVidQA is excluded here because it already has a separate preprocessing review.

## Main conclusion

Do not sample the public datasets blindly. The papers/cards expose the intended strata:

- topic-control distractors
- OOS intent/domain splits
- prompt harmfulness labels
- adversarial/jailbreak attack type
- safety policy category
- language and harm category
- safe/unsafe category labels where available

Random sampling should happen only inside those strata after filtering.

## CantTalkAboutThis

Paper/card intent: train and evaluate topic control in task-oriented dialogue by adding distractor turns to on-topic conversations.

Paper-grounded rule:

- Use the `distractors` field directly, because the dataset was built around distractor turns.
- Stratify by `domain` and scenario.
- Treat as easy/medium `SAFE + OFF_TOPIC`, not hard lesson-near negative.
- Prefer the commercially friendly CC-BY-4.0 version.
- Keep the human-annotated test subset for evaluation if possible.

Use for our router:

```text
OFF_TOPIC_EASY / SOFT_REFUSE_REDIRECT
```

Avoid:

- treating full conversations as router samples without extracting the off-topic user turn
- expecting multilingual robustness from this source, because it is English-only

## CLINC150/OOS

Paper intent: evaluate intent classifiers under out-of-scope prediction. The key contribution is not just 150 intents, but explicit OOS handling.

Paper-grounded rule:

- Use explicit OOS rows as the cleanest off-topic examples.
- Also use in-scope intents as safe off-topic examples for a lesson router, but stratify by intent.
- Exclude/downweight lesson-overlap intents such as definition, translate, spelling, calculator, and measurement conversion if those could be valid tutor queries.
- Preserve OOS rows for eval slices because the paper shows OOS recall is the hard metric.

Use for our router:

```text
SAFE + OFF_TOPIC generic
```

Avoid:

- sampling by raw row count, because each intent has fixed repeated counts
- using educational-looking intents as off-topic without checking current lesson scope

## WildGuardMix

Paper intent: one-stop moderation for three tasks: prompt harmfulness, response harmfulness, and response refusal. WildGuardMix intentionally balances vanilla prompts and adversarial jailbreaks across broad risk categories.

Paper-grounded rule:

- Use `prompt_harm_label` as the primary selector.
- Use `subcategory` to balance unsafe categories.
- Use `adversarial` as metadata/eval slice, not direct `JAILBREAK`.
- Select jailbreak candidates by combining harmful prompt label with bypass/prompt-injection patterns.
- Router should use prompt-only data; response labels are useful as metadata but should not enter router input.

Use for our router:

```text
UNSAFE / SAFETY_REFUSE
JAILBREAK / SAFETY_REFUSE when bypass intent is present
SAFE / OFF_TOPIC for unharmful non-lesson prompts
```

Avoid:

- mapping every `adversarial=true` row to `JAILBREAK`
- overusing response text, because the router labels user query and routing action

## JailBreakV-28K

Paper/card intent: benchmark MLLM robustness against jailbreak attacks. It contains 20k text-based LLM transfer attacks and 8k image-based MLLM attacks across multiple methods and safety policies.

Paper-grounded rule:

- For a text router, use only text-transfer attack methods:
  - Template
  - Logic
  - Persuade
- Exclude or separately hold out image-dependent methods:
  - FigStep
  - Query-relevant / image-dependent rows
- Stratify by `policy` and `format`.
- Use `jailbreak_query` as the router input.
- Keep `redteam_query` as metadata or as a separate unsafe baseline.

Use for our router:

```text
JAILBREAK / SAFETY_REFUSE
```

Avoid:

- mixing MLLM/image attack rows into text-router training
- collapsing all policies into one dominant source distribution

## MultiJail

Paper intent: expose multilingual jailbreak/safety gaps. It starts from 315 English unsafe prompts and annotates them into 9 non-English languages, including Vietnamese, and studies unintentional and intentional multilingual bypass scenarios.

Paper-grounded rule:

- Treat base prompts as multilingual `UNSAFE`, not automatically `JAILBREAK`.
- Stratify by language resource group:
  - high-resource: zh, it, vi
  - medium-resource: ar, ko, th
  - low-resource: bn, sw, jv
- Ensure Vietnamese coverage.
- Create intentional code-switch/jailbreak samples through controlled wrappers if needed.

Use for our router:

```text
UNSAFE multilingual
JAILBREAK multilingual only when wrapped with bypass/prompt-injection intent
```

Avoid:

- labeling all MultiJail rows as jailbreak
- ignoring low-resource languages if the goal is robustness evaluation

## Paper-grounded v1 extraction recipe: 5 public sources only

| Router group | Source | Paper-grounded selector | Suggested v1 quota |
| --- | --- | --- | ---: |
| OFF_TOPIC easy | CantTalkAboutThis | `distractors[*].distractor`, stratify by domain | 700-900 |
| OFF_TOPIC generic | CLINC150/OOS | explicit OOS + stratified intents minus lesson-overlap intents | 700-1,000 |
| UNSAFE | WildGuardMix | `prompt_harm_label=harmful`, length-filtered, no bypass, stratify by subcategory | 1,100-1,300 |
| JAILBREAK | WildGuardMix | harmful + bypass/prompt-injection pattern, use adversarial as metadata | 250-350 |
| JAILBREAK | JailBreakV-28K | `format in {Template, Logic, Persuade}` and `transfer_from_llm=true`, stratify by policy/format | 800-1,000 |
| UNSAFE multilingual | MultiJail | language + harm category stratification, include vi | 450-650 |
| JAILBREAK multilingual | MultiJail-derived | controlled code-switch/bypass wrappers over selected unsafe prompts | 100-250 |

## Sources

- CantTalkAboutThis dataset card / EMNLP 2024 paper: https://huggingface.co/datasets/nvidia/CantTalkAboutThis-Topic-Control-Dataset
- CLINC150 / OOS eval repo and EMNLP 2019 paper: https://github.com/clinc/oos-eval
- WildGuard paper page: https://huggingface.co/papers/2406.18495
- JailBreakV-28K dataset card: https://huggingface.co/datasets/JailbreakV-28K/JailBreakV-28k
- MultiJail dataset card: https://huggingface.co/datasets/walledai/MultiJail
