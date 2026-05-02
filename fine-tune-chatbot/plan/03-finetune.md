# P3 — Fine-tuning

## Goal

Run QLoRA fine-tuning for the A/B/C/D ablation mixes and compare outcomes.

## Base configuration

| Item | Value |
|---|---|
| Base model | `Qwen/Qwen2.5-7B-Instruct` |
| Method | QLoRA |
| Quantized load | 4-bit |
| Suggested rank | `r=16` or `r=32` |
| Suggested max length | 2048 or 4096 |

## Recommended target modules

- `q_proj`
- `k_proj`
- `v_proj`
- `o_proj`
- `gate_proj`
- `up_proj`
- `down_proj`

## Run policy

- Train one run per mix: A, B, C, D.
- Save each adapter separately.
- Compare based on evaluation, not only `eval_loss`.

## Selection rule

Reject any run where:

- internal domain score falls materially
- hallucination rises
- style gains come with technical regressions

Prefer the smallest ELI5 ratio that delivers a clear style improvement without harming correctness.
