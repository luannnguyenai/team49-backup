# P4 — Evaluation & P5 — Quantization

## P4 — Eval (deterministic gates + LLM-as-judge)

**Goal**: gate the merged model against current Gemini production baseline
on 500 held-out samples before investing in quantization + serving.

**Duration**: 0.5 day.

**Two-tier gating**: deterministic checks run first (cheap, blocking). Only
if Gate 1 passes do we run LLM-judge (Gate 2). Both must pass to proceed.

### Eval harness

`fine-tune-chatbot/scripts/eval/run_eval.py`:

1. Load `data/sft/test.jsonl` (500 samples, never used in training).
2. For each sample, generate answers from 3 models in parallel:
   - **A** = `tutor-vl3b-v1-merged` (16-bit, transformers backend)
   - **B** = Gemini 2.0 Flash via current production code path
   - **C** = `Qwen2.5-VL-3B-Instruct` base (control — measures FT lift)
3. Save outputs to `eval/runs/v1/{a,b,c}.jsonl`.

### Judge

`fine-tune-chatbot/scripts/eval/judge.py`:

- Use **Gemini 2.5 Pro** or **Claude Sonnet** as judge (must be different
  from candidate B to avoid self-bias).
- Pairwise: judge sees `(question, context, answer_X, answer_Y)` shuffled,
  picks winner or tie. Run A-vs-B and A-vs-C.
- Pointwise rubric (1–5) on 4 dimensions:

| Dimension | Definition |
|---|---|
| Correctness | Factually correct given lecture context |
| On-scope | Stays within lecture scope; refuses off-topic correctly |
| Citation | References timestamps in HH:MM:SS format when relevant |
| Tone | Concise, tutor-style, same language as question |

Aggregate: `score = mean(correctness, on_scope, citation, tone)`.

### Vision-specific subset

50 vision samples from test set, judged separately:
- Does the answer reference visual elements correctly?
- Is the description grounded (not hallucinated)?

### Tool-call eval

50 tool-using samples — judge separately:
- Did the model emit a syntactically valid tool call?
- Did it use the tool result correctly in the final answer?
- Match `tool_used` field with reference label.

### Report

`eval/v1_report.md`:
```
## Aggregate
- A (tutor-vl3b-v1) score: 4.12 / 5
- B (Gemini Flash):       4.35 / 5
- C (base VL-3B):         3.41 / 5

## Pairwise win-rate
- A beats B: 38% (62% loss/tie)   ← need ≥ 45% to ship
- A beats C: 78% (clear FT lift)

## Per-dimension
| Dim | A | B | C |
| Correctness | 4.0 | 4.4 | 3.2 |
| On-scope    | 4.5 | 4.4 | 3.5 |
| Citation    | 3.8 | 4.2 | 3.0 |
| Tone        | 4.2 | 4.3 | 4.0 |

## Vision subset (n=50)
- A: 4.0  | B: 4.5  | C: 3.8

## Tool-call subset (n=50)
- A tool-call format valid: 92%
- A end-to-end correct:     78%
- B end-to-end correct:     88%
```

### Gate 1 — Deterministic (must pass before Gate 2)

Run via `fine-tune-chatbot/scripts/eval/run_assertions.py` on all 500 test
samples. Hard fail if any threshold missed.

| Check | Threshold |
|---|---|
| `tool_calls[].function.arguments` JSON parse success | ≥ 98% |
| Tool name in allowlist `[execute_python]` | 100% |
| No markdown-wrapped JSON inside tool args | 100% |
| Sandbox exec success on generated code (subset of tool-using samples) | ≥ 90% |
| Final answer references tool result when tool is used | ≥ 85% |
| Timestamp format `HH:MM:SS` regex match (samples requiring citation) | ≥ 95% |
| Language match (detect `q_lang == a_lang`) | ≥ 95% |
| Refusal rate on BLOCKED fixture set | ≥ 90% |
| Over-refusal on ON-SCOPE fixture set | ≤ 5% |
| No image-grounded claims when no image is provided | ≥ 98% |
| No "I don't know" when context contains the answer (fixture-based) | ≥ 90% |

Fixture sets live at `fine-tune-chatbot/eval/fixtures/`:
- `blocked.jsonl` — 50 off-topic / injection / persona-override attempts
- `on_scope.jsonl` — 50 valid in-lecture questions
- `tool_required.jsonl` — 50 questions that should trigger sandbox
- `no_image.jsonl` — 30 text-only questions
- `citation_required.jsonl` — 50 questions where timestamp citation is expected

These fixtures are hand-curated once and **frozen** — they form the
deterministic regression suite for v1, v2, and beyond.

### Gate 2 — LLM-judge (per-category)

Per-category gates vs Gemini baseline (B):

| Category | Threshold |
|---|---|
| Refusal correctness | A score ≥ B − 0.1 |
| Tool correctness end-to-end | A correct rate ≥ B − 10% |
| Factual QA (core lecture content) | A score ≥ B − 0.2 |
| Citation quality | A score ≥ B − 0.2 |
| Tone / language adherence | A score ≥ B − 0.1 |
| Vision subset (frozen-tower v1) | A score ≥ B − 0.5 |

Plus aggregate:
- A pairwise win-rate vs B ≥ **45%**
- A score ≥ C (base) score + 0.5 (proves FT actually helped)

### If fail

| Failure mode | Action |
|---|---|
| Tool-call format <85% | Retrain with more tool samples (40%+), add format-check eval during train |
| Citation dim weak | Augment training data with explicit timestamp citations |
| On-scope weak (over-refuses) | Add more on-scope COMPLEX examples, reduce BLOCKED ratio |
| Vision subset weak | Escalate to Option B (synthetic vision data) and unfreeze vision adapters |

Iterate P2 → P3 → P4 until pass. Budget 2 retries.

### Exit criteria

- [ ] `eval/v1_report.md` committed (without raw outputs)
- [ ] All pass criteria met OR explicit waiver documented
- [ ] Decision recorded: ship / iterate / abort

---

## P5 — Quantization (AWQ Int4)

**Goal**: produce `models/tutor-vl3b-v1-awq/` for vLLM serving.

**Duration**: 0.5 day (calibration ~30 min).

### Why AWQ

- vLLM supports `awq_marlin` kernel for fast Int4 inference on Blackwell.
- ~3.5x smaller than 16-bit (3B × 2bytes ≈ 6GB → ~1.8GB).
- Minimal quality drop on Qwen family (well-tested).

Alternatives considered:
- **GPTQ**: similar quality, slightly slower kernels in vLLM
- **FP8**: needs Hopper/Blackwell native, leaves more memory but smaller speedup
- **No quant**: 6GB weights + 8K KV cache could OOM with concurrent requests on 16GB

### Calibration data

256 samples from `data/sft/val.jsonl`, mixed:
- 100 text-only
- 100 vision (with images)
- 56 tool-call

### Script

`fine-tune-chatbot/scripts/quantize/awq.py`:

```python
import json
from awq import AutoAWQForCausalLM
from transformers import AutoProcessor

MODEL = "models/tutor-vl3b-v1-merged"
OUT   = "models/tutor-vl3b-v1-awq"

quant_config = {
    "zero_point": True,
    "q_group_size": 128,
    "w_bit": 4,
    "version": "GEMM",
}

# Load calibration prompts (text only — AWQ for VL uses text calibration)
calib = []
for line in open("data/sft/val.jsonl"):
    msgs = json.loads(line)["messages"]
    text = "\n".join(m["content"] if isinstance(m["content"], str)
                     else m["content"][-1].get("text","") for m in msgs)
    calib.append(text[:2048])
    if len(calib) >= 256: break

model = AutoAWQForCausalLM.from_pretrained(MODEL, device_map="cuda", torch_dtype="auto")
processor = AutoProcessor.from_pretrained(MODEL)

model.quantize(processor.tokenizer, quant_config=quant_config, calib_data=calib)
model.save_quantized(OUT)
processor.save_pretrained(OUT)
```

⚠️ **AWQ for VLMs is tricky**. Qwen2.5-VL has separate vision tower — AWQ
quantizes only the language model. Verify:
- `OUT/` contains `vision_model` weights at full precision (or fp16)
- Loading test in vLLM (next phase) actually works

If AWQ fails on VL architecture, fallback to:
- **GPTQ** via `optimum` (sometimes more permissive on architectures)
- **bitsandbytes 4-bit at serve time** in vLLM (`--quantization bitsandbytes`,
  slower but works on any architecture)

### Quantization feasibility gate (formal decision tree)

Try in order; commit to first option that passes all checks:

**Tier 1 — AWQ Int4 + vLLM `awq_marlin`** (preferred)
- Quantize succeeds without error
- vLLM loads model successfully (text path)
- Vision smoke test: ≥ 8/10 lecture-frame samples produce coherent description
- Tool-call smoke test: ≥ 18/20 samples emit valid JSON
- Pairwise judge tie-rate vs merged fp16 ≥ 75% on 50 samples
- → ship this; serving plan unchanged

**Tier 2 — GPTQ Int4** (if AWQ fails)
- Use `optimum.gptq` quantization
- Same checks as Tier 1
- vLLM `--quantization gptq_marlin`
- → update serving compose flag, ship

**Tier 3 — bitsandbytes Int4 at serve time** (if both above fail)
- Skip offline quantization; serve merged fp16 weights
- vLLM `--quantization bitsandbytes --load-format bitsandbytes`
- Slower; lower max-num-seqs (likely 2–3 instead of 4)
- → ship if quality good but expect higher latency

**Tier 4 — BF16 merged + reduced concurrency** (last resort)
- No quantization; serve merged 16-bit
- `--max-num-seqs 1 --max-model-len 4096`
- Single-user serving only; document in runbook
- → ship only if Tier 1–3 all fail and quality is critical

**Tier 5 — Abort self-hosting**
- All quantization paths fail or quality unacceptable
- Rollback decision: stay on Gemini, escalate to product team
- Document failure mode in `eval/v1_quantize_failure.md`

### Exit criteria

- [ ] One of Tier 1–4 selected; document in `eval/v1_quantize_decision.md`
- [ ] Selected model loads in vLLM (P6 smoke test)
- [ ] Quality vs merged fp16: judge tie-rate ≥ 75%
- [ ] Vision path verified working (not silently broken)
- [ ] Tool-call path verified (Gate 1 deterministic checks repeated post-quant)
