# P5 — Serving

## Goal

Serve the selected English-only tutor model behind an OpenAI-compatible endpoint after the training winner has been chosen.

## Scope

This document is intentionally narrower than the older serving plan.

- vision-capable serving is required
- OpenAI-compatible multimodal chat payloads must remain supported
- no tool-calling-specific serving requirements

## Serving recommendation

Start with the simplest viable deployment:

- load the selected `Qwen/Qwen2.5-VL-3B-Instruct` base model plus LoRA adapter, or a merged model if later needed
- expose an OpenAI-compatible chat endpoint
- verify English tutor responses on representative prompts
- verify at least one image-plus-text request path works end to end

## Integration requirements

- keep backend wiring separate from training decisions
- configure the serving endpoint by environment variable
- verify latency and correctness after integration
- keep request formatting compatible with OpenAI-style multimodal `messages[].content[]`

## Smoke checks

- health endpoint responds
- simple English concept explanation works
- comparison question works
- long-form explanation remains coherent
- single-image question answering works through the OpenAI-compatible endpoint

## Non-goals

- no Hermes tool-call parser work
- no full multimodal benchmark suite in v1
