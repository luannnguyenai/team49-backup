# GPT Review — Fine-tune Chatbot Plan

Review date: 2026-04-25

Scope reviewed:
- `README.md`
- `01-environment.md`
- `02-data-pipeline.md`
- `03-finetune.md`
- `04-eval-quantize.md`
- `05-serving-vllm.md`
- `06-codebase-changes.md`
- `07-rollout.md`

## Executive summary

The plan is directionally sound: Qwen2.5-VL-3B + Unsloth QLoRA + vLLM
OpenAI-compatible serving is a reasonable v1 path for a self-hosted tutor on a
single 16GB GPU, provided that the project accepts lower reasoning quality than
Gemini and keeps Gemini as fallback.

The biggest risks are not product-design risks. They are operational:

1. Blackwell compatibility on RTX 5060 Ti (`sm_120`) for PyTorch, bitsandbytes,
   Unsloth, AWQ, and vLLM.
2. Inconsistent phase numbering and contradictory file-change scope.
3. Overconfidence in AWQ/vLLM support for a Qwen2.5-VL architecture.
4. Tool-calling and LangGraph fallback details are underspecified and may not
   work as written.
5. Evaluation gates rely heavily on LLM-as-judge, but there is not enough
   deterministic regression testing for tool calls, citation format, and
   groundedness.

Recommended decision: keep the current model choice and local-first approach,
but rewrite the execution plan around stricter gates:

1. P1 local stack smoke tests.
2. P2 data + deterministic eval fixture creation.
3. P3 small 100-sample overfit run.
4. P4 full fine-tune.
5. P5 eval gate.
6. P6 quantization/serving proof.
7. P7 code integration behind feature flags.
8. P8 shadow/canary rollout.

## Train location decision

Use local RTX 5060 Ti 16GB as the primary training environment. It matches the
intended serving machine, avoids notebook timeouts, keeps artifacts local, and
forces the plan to validate the exact CUDA/vLLM/Docker path that will matter in
production.

Colab should be a fallback, not the default. It is useful if local Blackwell
wheels fail, especially for running P3 training on a more established cloud GPU.
However, Colab GPU types and limits vary over time, and premium GPUs are subject
to availability. If Colab is used, only use it for training and copy adapters or
merged model artifacts back locally for eval, quantization, vLLM, Docker, and
integration work.

Kaggle should not be the primary training path. It is useful for data cleaning,
smoke tests, and maybe a small prototype LoRA run. Its weekly accelerator quota,
session limits, less controllable CUDA stack, and hardware variability make it a
bad fit for the main plan.

Current external constraints checked:
- Colab FAQ says resource limits, maximum VM lifetime, and GPU types vary over
  time and are not guaranteed:
  https://research.google.com/colaboratory/intl/en-GB/faq.html
- Google Workspace Colab docs describe Pro subscriptions using compute units:
  https://support.google.com/a/answer/15094583
- NVIDIA's Kaggle blog describes limited accelerator quota, including an
  example of 30h/week:
  https://developer.nvidia.com/blog/how-kaggle-makes-gpus-accessible-to-5-million-data-scientists/
- RTX 5060 Ti 16GB reference specs list 16GB GDDR7 and Blackwell/GB206:
  https://www.techpowerup.com/gpu-specs/geforce-rtx-5060-ti-16-gb.c4292

## High-priority issues

### 1. Phase numbering is inconsistent

`04-eval-quantize.md` defines P4 Eval and P5 Quantization.
`05-serving-vllm.md` is also titled P5 Serving.
`06-codebase-changes.md` then calls itself P6.
`07-rollout.md` calls itself P7.

This will cause confusion once implementation starts.

Recommendation:
- Keep `04-eval-quantize.md` as P4/P5 only if serving becomes P6.
- Rename:
  - `05-serving-vllm.md`: P6 Serving
  - `06-codebase-changes.md`: P7 Codebase Changes
  - `07-rollout.md`: P8 Rollout
- Or split eval and quantization into separate files:
  - P4 Eval
  - P5 Quantization
  - P6 Serving
  - P7 Codebase
  - P8 Rollout

### 2. README success criteria contradicts codebase-change plan

`README.md` says:

> Zero net code changes to `llm_service.py`, `router.py`, LangGraph

But `06-codebase-changes.md` requires changes to `llm_service.py`, including:
- provider-aware tutor model resolution,
- wrapping `compiled_graph.stream(...)`,
- fallback graph construction.

This is a material contradiction.

Recommendation:
- Replace the README criterion with:
  - "No user-facing API route changes."
  - "No router model migration in v1."
  - "LangGraph topology remains behaviorally equivalent except fallback wrapper."
- Or if zero `llm_service.py` changes is truly desired, move all provider
  switching and fallback behavior into `chat_model_factory.py` or a new tutor
  model adapter layer and update `06-codebase-changes.md` accordingly.

### 3. `06-codebase-changes.md` says 3 files touched, but lists more

The plan says:

> Files touched: 3

But the same file later requires changes to:
- `src/config.py`
- `.env.example`
- `docker-compose.yml`
- `src/services/chat_model_factory.py`
- `src/services/llm_service.py`
- `src/services/llm_rate_limiter.py`

That is at least 6 files.

Recommendation:
- Fix the scope line.
- Add tests to the file list:
  - `tests/services/test_chat_model_factory.py`
  - `tests/services/test_llm_rate_limiter.py`
  - optional targeted test for self-hosted provider selection.

### 4. `depends_on: tutor-llm` is unsafe as written

`06-codebase-changes.md` says to add `depends_on: tutor-llm` so backend waits
for vLLM healthcheck.

In Docker Compose, plain `depends_on` controls startup order, but does not
necessarily mean the dependency is healthy unless condition syntax is used and
supported by the Compose version.

Recommendation:
- Use a healthcheck-aware form if Compose supports it:

```yaml
depends_on:
  tutor-llm:
    condition: service_healthy
```

- If that is not supported in the deployed Compose version, keep backend startup
  independent and rely on runtime fallback/retry logic.

### 5. Fallback wrapper likely does not switch the existing compiled graph

The proposed `_run_with_fallback(inputs)` catches errors around
`compiled_graph.stream(inputs, ...)`, then builds a new mini graph using
`fallback_llm`.

This may work for some failures, but it is not equivalent to the main graph.
Potential issues:
- The original graph's `agent_node`, context assumptions, callbacks, and state
  behavior are bypassed.
- If failure occurs after partial streaming to the user, fallback may produce a
  second answer stream after a partial failed answer.
- Error boundaries around streaming chunks are tricky. Some provider errors may
  surface after the response has already started.
- The new fallback graph is compiled per failure, increasing complexity during
  an incident.

Recommendation:
- Prefer provider selection before graph execution.
- Build the graph around an injectable LLM or create separate cached graphs per
  provider:
  - `get_compiled_graph(provider="self_hosted")`
  - `get_compiled_graph(provider="google_genai")`
- On primary failure before first emitted token, retry with fallback.
- After first token is emitted, fail gracefully and log; do not silently switch
  model mid-stream unless UX explicitly supports it.

### 6. Canary conflicts with `lru_cache(maxsize=1)`

`07-rollout.md` correctly notes that `_get_llm_with_tools` is cached and canary
requires keying on provider/lecture or removing the cache.

But this is not reflected in `06-codebase-changes.md`, where the replacement
function still uses `@lru_cache(maxsize=1)`.

Recommendation:
- In the codebase-change plan, either:
  - remove canary from v1 and rollout only by environment/config, or
  - implement provider-specific caching:

```python
@lru_cache(maxsize=4)
def _get_llm_with_tools_for_provider(provider: str, model_name: str):
    ...
```

Then route per request using `_provider_for_lecture(lecture_id)`.

### 7. AWQ for VLM is called out as tricky, but the plan still assumes it

`04-eval-quantize.md` correctly warns that AWQ for Qwen2.5-VL is tricky.
However, the overall plan still treats AWQ as the serving target.

Risks:
- AWQ library may not support the exact VL architecture.
- vLLM may load the text model but fail vision path.
- `awq_marlin` kernel availability on Blackwell may depend on exact vLLM/CUDA
  build.
- Quantized text path may pass while image input silently fails or has degraded
  quality.

Recommendation:
- Add a hard "quantization feasibility gate" before code integration.
- Define fallback serving modes in order:
  1. AWQ Int4 in vLLM if all text/vision/tool smoke tests pass.
  2. vLLM bitsandbytes quantization if AWQ fails.
  3. BF16 or FP16 merged model with lower concurrency/context if quantization
     fails but quality is required.
  4. Keep Gemini fallback and do not roll out self-hosting if none pass.
- Update serving plan to mount `tutor-current` symlink from day one instead of
  a version-specific model path.

### 8. Tool-call format is under-validated

The plan targets tool-call samples at 25-35% and uses Hermes parser in vLLM.
That is good, but the eval criteria are too weak for a tool-using tutor.

Current criteria:
- valid format >= 85%
- end-to-end judged on 50 samples

Missing deterministic checks:
- JSON parseability of `tool_calls[].function.arguments`
- required schema fields present
- no markdown-wrapped JSON in tool arguments
- no hallucinated tool names
- no unsafe Python if sandbox has safety policy
- final answer must reference tool result when tool is used

Recommendation:
- Add deterministic tool-call validator before LLM judge.
- Gate:
  - tool-call JSON parse success >= 98%
  - allowed tool names only = 100%
  - sandbox execution success on generated code >= 90%
  - final answer uses tool result >= 85%

### 9. Evaluation has too much LLM-as-judge and too little fixed regression

LLM-as-judge is useful for quality, but the plan needs deterministic regression
fixtures for:
- timestamp citation format,
- refusal behavior on blocked/off-topic questions,
- language matching Vietnamese/English,
- tool-call syntax,
- no image hallucination when image is absent,
- no answer when context is insufficient.

Recommendation:
- Add `eval/fixtures/*.jsonl` with maybe 100 curated cases.
- Add a deterministic `run_assertions.py` before `judge.py`.
- Only run LLM judge after deterministic checks pass.

### 10. Data pipeline depends on fields that may not exist consistently

`02-data-pipeline.md` references:
- `qa_history.thoughts` containing `[SANDBOX]`
- joining DB `qa_history`, `lectures`, `chapters`, `transcript_lines`
- exact line matches from `llm_service.py`

The plan should verify the real schema and logs before promising extraction.

Recommendation:
- Add a P2.0 "schema and data audit" step:
  - count rows in `logs/qa_history.jsonl`
  - count DB rows
  - count usable rows after filters
  - count rows with `thoughts`
  - count rows with tool traces
  - count distinct lectures
  - count Vietnamese vs English
- Make synthetic data mandatory if usable rows are below threshold, not just a
  fallback note.

## Medium-priority issues

### 11. The training-time estimate may be optimistic

`03-finetune.md` estimates 2-4 hours total. This might hold for text-heavy 3B
QLoRA, but it is optimistic with:
- 10k samples,
- 3 epochs,
- 4096 context,
- vision samples,
- 5060 Ti memory constraints,
- Windows/WSL/Docker overhead depending on execution environment.

Recommendation:
- Present as "target: 2-4h, budget: 4-8h".
- Add a 100-step benchmark after P1 and update estimates from actual seconds per
  step.

### 12. `max_seq_length` and serving `--max-model-len` mismatch needs a reason

Training uses `max_seq_length=4096`.
Serving uses `--max-model-len 8192`.

This can be valid, but it should be explicitly justified. Longer serving
contexts increase KV cache and may degrade behavior beyond trained distribution.

Recommendation:
- Serve at 4096 for canary unless eval proves 8192 is needed.
- Or add an eval subset for 6K-8K contexts before setting serving to 8192.

### 13. Vision v1 decision is internally tense

The plan says v1 accepts frozen vision and minimal synthetic vision samples.
But success criteria require:

> Vision questions answered correctly on >= 80% of vision eval subset

That may be too ambitious if real image training data is missing and only
200-500 synthetic examples are used.

Recommendation:
- Either lower the v1 vision criterion or require Option B synthetic vision data
  before evaluating v1.
- Separate "base vision capability preserved" from "domain-specific slide tutor
  vision improved".

### 14. Data privacy / licensing needs a line item

Training on QA history and lecture frames may include:
- student-provided questions,
- names/emails/IDs,
- copyrighted lecture material,
- teacher-model synthetic distillation.

The PII scrub is a good start, but not enough.

Recommendation:
- Add a data governance section:
  - what can be used for training,
  - what cannot leave local machine,
  - whether Colab/Kaggle upload is allowed,
  - retention policy for raw JSONL/model artifacts,
  - redaction expectations for `eval/runs`.

### 15. `.env.example` syntax with inline comment may be ambiguous

The proposed line:

```dotenv
TUTOR_PROVIDER_OVERRIDE=          # leave empty until rollout
```

Depending on parser, that may include spaces or comment text.

Recommendation:

```dotenv
# Leave empty until rollout.
TUTOR_PROVIDER_OVERRIDE=
```

### 16. vLLM Docker image must be pinned earlier

`05-serving-vllm.md` says use `vllm/vllm-openai:latest` but comments to pin a
Blackwell-verified tag from P1. The final compose snippet should not contain
`latest` once P1 has run.

Recommendation:
- Add explicit P1 output:
  - `VLLM_IMAGE_TAG=<verified tag or local build sha>`
- Make P6 consume that value.

### 17. Success criterion "A beats Gemini >=45%" may be too permissive

This might be acceptable for self-hosting cost control, but it should be stated
as a business/product trade-off. A model that loses/ties 55-62% against Gemini
may create noticeable quality regressions.

Recommendation:
- Require per-category gates:
  - blocked/refusal: self-hosted must be no worse than Gemini by more than 0.1
  - tool correctness: no worse than Gemini by more than 10%
  - core factual course QA: no worse than Gemini by more than 0.2
- Keep the 45% pairwise win-rate as a secondary aggregate metric.

## Suggested plan rewrite

### P1 — Local environment proof

Keep current P1 but add:
- source of truth file: `fine-tune-chatbot/scripts/env-frozen.txt`
- benchmark file: `fine-tune-chatbot/scripts/smoke/benchmark_100_steps.json`
- final decision:
  - local train OK,
  - local serve OK,
  - train on Colab fallback,
  - abort/self-hosting postponed.

### P2 — Data audit and dataset build

Split into:
- P2a schema/log audit,
- P2b extraction,
- P2c cleaning,
- P2d deterministic eval fixture creation,
- P2e ChatML formatting.

Exit criteria should include real counts, not only target counts.

### P3 — Tiny overfit run

Before full training, run:
- 100 high-quality samples,
- 50-100 steps,
- verify loss drops,
- verify model can reproduce a few exact answers/tool-call shapes.

This catches formatting/collator mistakes faster than full P3.

### P4 — Full fine-tune

Run current P3 with measured params from P3 tiny run.

### P5 — Eval gate

Run deterministic assertions first, LLM judge second.

### P6 — Quantization and serving proof

Quantize only after P5 passes. Validate text, vision, tool calls, streaming, and
concurrency in the same serving stack that backend will call.

### P7 — Code integration

Implement:
- config fields,
- provider factory,
- rate-limiter bypass,
- provider-specific graph/model cache,
- feature flags,
- tests.

Avoid mid-stream fallback unless explicitly designed.

### P8 — Shadow/canary/rollout

Make canary implementation match the caching strategy from P7.

## File-specific notes

### `README.md`

Good:
- Clear model/provider/fallback decision table.
- Local vs Colab vs Kaggle comparison is now explicit.
- Trade-off vs 7B is stated.

Needs change:
- Remove or rewrite "Zero net code changes to `llm_service.py`".
- Align phase numbering.
- Add "data governance" and "cloud upload allowed?" decision.

### `01-environment.md`

Good:
- Correctly treats Blackwell as critical path.
- Separates train and serve envs.
- Includes smoke tests for load, inference, train, vLLM.

Needs change:
- Add explicit WSL/Linux recommendation if Windows native CUDA/Unsloth becomes
  brittle.
- Add source-build fallback as a separately estimated task, not a small aside.
- Record exact GPU, driver, CUDA, torch, triton, bitsandbytes, vLLM versions.

### `02-data-pipeline.md`

Good:
- Correctly identifies truncated image data blocker.
- Sensible decision to use frozen vision for v1.
- Stratified split and held-out test set are good.

Needs change:
- Add schema/log audit first.
- Make data privacy/cloud-upload policy explicit.
- Add deterministic eval fixture creation.
- Clarify whether synthetic teacher outputs are allowed for training and how
  they are labeled in manifest.

### `03-finetune.md`

Good:
- QLoRA params are reasonable for 16GB.
- OOM fallback ladder is practical.
- Post-train sanity check is included.

Needs change:
- Add tiny overfit run before full run.
- Treat 2-4h as target, not guarantee.
- Add tool-call validation after training, not just "one of 5 samples".
- Add checkpoint resume instructions.

### `04-eval-quantize.md`

Good:
- Uses baseline Gemini and base Qwen control.
- Has dimension-specific rubric.
- Notes AWQ/VLM risk.

Needs change:
- Split eval and quantization into two phases or fix numbering.
- Add deterministic assertions before LLM judge.
- Strengthen tool-call gates.
- Make AWQ fallback path a formal decision tree.

### `05-serving-vllm.md`

Good:
- OpenAI-compatible vLLM service design matches existing provider abstraction.
- Smoke tests cover health, streaming, vision, and tools.
- Load-test metrics are useful.

Needs change:
- Rename phase number.
- Do not leave final image tag as `latest`.
- Verify `depends_on` health semantics.
- Consider serving at 4096 context first unless 8192 eval passes.

### `06-codebase-changes.md`

Good:
- Keeps integration mostly behind provider factory/config.
- Rate limiter bypass for self-hosted is correct.
- Not migrating router in v1 is the right call.

Needs change:
- Fix file count.
- Add tests.
- Rework fallback design.
- Resolve `lru_cache` vs canary conflict.
- Avoid compiling fallback graph on exception path if possible.

### `07-rollout.md`

Good:
- Shadow/canary/rollback structure is sensible.
- Risk register covers main operational risks.
- Runbook is practical.

Needs change:
- Ensure shadow mode has a real implementation in P7.
- Do not log only first 500 chars if full comparison is needed; use a structured
  eval log with redaction.
- Add kill-switch env var for self-hosted globally.
- Add "do not promote if fallback rate > threshold" gate after each stage.

## Final recommendation

Proceed with the self-hosted v1 plan only after P1 passes locally. Do not start
full data generation or code integration until the exact local train + serve
stack is proven with Qwen2.5-VL-3B.

If P1 fails locally:
- Use Colab for training only if project data is allowed to leave the local
  machine.
- Keep eval, quantization, vLLM, and backend integration local.
- Do not use Kaggle as the main path.

Before implementation, fix the plan contradictions:
- phase numbering,
- files touched count,
- `llm_service.py` contradiction,
- fallback/canary architecture,
- AWQ fallback decision tree,
- deterministic eval gates.

