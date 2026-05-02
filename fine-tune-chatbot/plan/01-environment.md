# P1 — Environment

## Goal

Prepare a reproducible training environment for the English-only fine-tune pipeline on a vision-capable Qwen VL base model.

## Requirements

| Item | Recommendation |
|---|---|
| Python | 3.12 |
| GPU | 24GB preferred, 16GB minimum with tighter batch/sequence settings |
| Framework | `transformers`, `peft`, `trl`, `bitsandbytes`, optionally `unsloth` |
| Precision | 4-bit QLoRA load, bf16 if supported else fp16 |

## Environment checks

- Confirm the base model `Qwen/Qwen2.5-VL-3B-Instruct` loads successfully.
- Confirm tokenizer and chat template work.
- Confirm a small SFT dataset can be tokenized without schema errors.
- Confirm evaluation datasets can be loaded separately from training data.
- Confirm the processor can accept a simple image-plus-text chat message for later serving compatibility checks.

## Non-goals

- No tool-calling parser validation.
- No Vietnamese-specific environment setup.
- No new multimodal training dataset preparation in this phase.
