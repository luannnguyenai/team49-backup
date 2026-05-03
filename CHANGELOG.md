# Changelog

## 2026-05-02

### Tutor prompt guardrails
- Refactored tutor system-prompt assembly in `src/services/llm_service.py` into `_build_tutor_system_instruction(has_image: bool)`.
- Preserved all original tutor prompt rules and output-format instructions unchanged.
- Appended an `[ADDITIONAL GUARDRAILS]` block covering hidden-instruction secrecy, prompt-injection resistance, untrusted transcript/OCR/history boundaries, no outside-knowledge fallback, long/noisy prompt handling, and timestamp integrity.
- Added backend regression tests in `tests/services/test_llm_service_prompt.py` to verify both original-rule preservation and new guardrail presence for text-only and image-enabled tutor prompts.
- Added planning note in `remaining tasks/guardrails/tutor-system-prompt-guardrails-plan.md`.
