# Fine-tune Chatbot Plan — English AI/ML Tutor

This plan aligns the `fine-tune-chatbot` folder to the current target:

- English-only tutor
- vision-capable base model with text-first fine-tuning in v1
- project dataset as domain anchor
- filtered ELI5 as auxiliary explanation-style data
- `Qwen/Qwen2.5-VL-3B-Instruct` as the base model

## Decisions

| Item | Value |
|---|---|
| Target tutor | English AI/ML/NLP/CV tutor |
| Base model | `Qwen/Qwen2.5-VL-3B-Instruct` |
| Fine-tune method | QLoRA 4-bit |
| Primary data | Project domain dataset |
| Auxiliary data | Filtered ELI5 only |
| Training supervision in v1 | Text-first SFT, no new multimodal research corpus |
| Main eval gate | Held-out internal domain set |
| Secondary eval | MMLU selected subjects, MMLU-Pro, TheoremQA |
| Style eval | Filtered ELI5 dev/test |

## What changed from the older plan

The earlier plan optimized for a different problem:

- Vietnamese support
- tool-calling preservation
- self-hosted runtime as the central design constraint

That is no longer the active target. The active target is now an English-only tutor pipeline that keeps the existing dataset research intact while switching the serving/model layer to a vision-capable Qwen VL model.

## Roadmap

### P1. Data audit

- Document the current domain dataset in detail.

### P2. ELI5 filtering and mixing

- Build a filtered ELI5 subset for explanation-style transfer only.
- Keep ELI5 capped at 30% in v1.
- Prepare ablation datasets A/B/C/D.

### P3. Fine-tuning

- Run QLoRA on `Qwen/Qwen2.5-VL-3B-Instruct`.
- Keep v1 supervision text-first so dataset research remains unchanged.
- Save adapters per ablation run.
- Track validation loss, but do not use it as the sole selection criterion.

### P4. Evaluation

- Evaluate internal domain correctness first.
- Then run MMLU selected subjects, MMLU-Pro, and TheoremQA.
- Run style evaluation on filtered ELI5 dev/test.

### P5. Selection and rollout

- Pick the best run using domain-first decision rules.
- Prepare the selected adapter for integration.
- Keep serving and deployment work separate from the training decision.
- Preserve multimodal serving compatibility at the API layer even though v1 training data remains text-first.

## Success criteria

- Internal domain benchmark improves over base model.
- English explanation quality improves over the domain-only baseline.
- Regression on secondary academic benchmarks remains acceptable.
- No selected run is more fluent but less correct.

## Failure criteria

- Domain correctness drops after adding ELI5.
- Hallucination rate increases.
- Answers become verbose without adding substance.
- Style improves only marginally while training complexity rises materially.

## Reading order

1. `../PROPOSAL.md`
2. `../PIPELINE.md`
3. `datasets.md`
4. `01-environment.md`
5. `02-data-pipeline.md`
6. `03-finetune.md`
7. `04-eval-quantize.md`
8. `05-serving-vllm.md`
9. `06-codebase-changes.md`
10. `07-rollout.md`

## Scope note

The serving and codebase integration docs remain in this folder because they are part of the active target again. Dataset research and mixing strategy stay domain-first and text-first; the change in this revision is the selected base model and runtime assumptions, not the dataset thesis.
