# P6 — Codebase Changes

## Goal

Integrate the selected English-only tutor model into the application with minimal, reversible changes.

## Principles

- keep model-provider integration isolated
- do not let runtime integration redefine the training strategy
- preserve a simple fallback path during rollout

## Expected change areas

- configuration for the selected self-hosted or remote model endpoint
- provider selection in the tutor path
- test coverage for the provider wiring

## Out of scope from the old plan

The following assumptions are no longer part of the active integration design:

- vision payload preservation
- tool-calling-specific adapter behavior
- Vietnamese-specific routing or evaluation logic

## GitNexus note

If this plan turns into actual code edits in service modules, run the required GitNexus impact analysis before editing functions, classes, or methods, per repository policy.
