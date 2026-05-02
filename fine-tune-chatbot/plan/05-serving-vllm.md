# P5 — Serving

## Goal

Serve the selected English-only tutor model behind an OpenAI-compatible endpoint after the training winner has been chosen.

## Scope

This document is intentionally narrower than the older serving plan.

- text-only serving is the active path
- no vision-specific runtime requirements
- no tool-calling-specific serving requirements

## Serving recommendation

Start with the simplest viable deployment:

- load the selected base model plus LoRA adapter, or a merged text model
- expose an OpenAI-compatible chat endpoint
- verify English tutor responses on representative prompts

## Integration requirements

- keep backend wiring separate from training decisions
- configure the serving endpoint by environment variable
- verify latency and correctness after integration

## Smoke checks

- health endpoint responds
- simple English concept explanation works
- comparison question works
- long-form explanation remains coherent

## Non-goals

- no multimodal payload handling in v1
- no Hermes tool-call parser work
- no vision benchmarking
