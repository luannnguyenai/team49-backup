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
- **Blinding**: candidate identity (A/B/C) MUST be hidden from judge.
  Replace with random labels per sample (e.g., "X" / "Y") and rotate
  positions 50/50 to defeat positional bias.
- **Reproducibility logging**: every judge run writes `eval/runs/v1/judge_log.jsonl`
  with one line per judged comparison:
  ```json
  {"sample_id": "...", "judge_model": "claude-sonnet-4.6",
   "judge_prompt_version": "v1.0", "judge_prompt_sha256": "...",
   "x_label": "X", "x_actual_candidate": "B",
   "y_label": "Y", "y_actual_candidate": "A",
   "winner_label": "Y", "winner_actual": "A",
   "winning_dim_breakdown": {...}, "judge_seed": 42}
  ```
- Judge prompt template stored as a versioned file
  `eval/judge_prompts/pairwise_v1.0.md`; bumping the prompt requires a
  new version number and re-baseline of the historical comparison set.
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
| No "I don't know" when context contains the answer (deterministic matcher, see below) | ≥ 90% |

**Deterministic matcher for "I don't know" gate** (avoids judge subjectivity):

Build a regex set + multilingual phrase list at `eval/fixtures/idk_phrases.json`:
```json
{
  "vi": ["không biết", "tôi chưa rõ", "em chưa rõ", "không có thông tin",
         "tôi không thể trả lời", "không tìm thấy", "câu hỏi này không có"],
  "en": ["i don't know", "i'm not sure", "i cannot answer",
         "no information", "i'm unable to", "the context does not"]
}
```

Matcher: lowercased answer matches any phrase via word-boundary regex.
Gate counts as "violation" only when:
1. Matcher hits AND
2. Fixture-tagged `answer_present_in_context: true` (curated label) AND
3. Answer length < 200 chars (filters cases where model adds disclaimers
   alongside a real answer)

Violations / total fixture-rows ≤ 10% to pass. Test fixture
`citation_required.jsonl` extended with `answer_present_in_context` label
during fixture authoring. Matcher is committed to repo; gate result is
deterministic and re-runnable across runs.

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

### Quantization feasibility ladder — RE-ORDERED (BF16 first, AWQ last)

⚠️ **Reordered from prior plan** based on AWQ-on-VLM risk. Qwen2.5-VL has
a vision tower that AWQ does not quantize cleanly; offline AWQ can break
load path, vision path, or remote-code config. Start from the safest
serving mode and step up to higher compression only when each tier passes
all smoke gates.

Decision tree (try in order, commit to **first** that passes all checks):

**Tier 1 — Merged BF16/FP16 unquantized in vLLM** (start here, NOT AWQ)
- Goal: prove the merged model can be served at all
- vLLM `--dtype bfloat16` (or `auto`); no `--quantization` flag
- Memory: ~7 GB weights + KV cache → fits 16GB with `--max-num-seqs 2`
- Smoke gates: text + vision + tool-call (criteria below)
- → **If pass: this is the v1 serving path.** Quantization is optional optimization, not required for ship.

**Tier 2 — bitsandbytes Int4 load-time quantization** (if Tier 1 needs more concurrency)
- vLLM `--quantization bitsandbytes --load-format bitsandbytes`
- No offline calibration needed — quantize at serve startup
- Permissive: works on most VL architectures including Qwen2.5-VL
- Slower than AWQ Marlin but correct
- → ship if Tier 1 OOM at desired concurrency and bnb quality acceptable

**Tier 3 — GPTQ Int4** (if more headroom needed)
- `optimum.gptq` calibration ~30 min
- vLLM `--quantization gptq_marlin`
- Often more permissive than AWQ on VLM architectures
- Same smoke gates as Tier 1

**Tier 4 — AWQ Int4 + `awq_marlin`** (last, only if T1–T3 insufficient)
- Highest compression and throughput
- Highest risk on VL architecture — vision tower may load broken
- Calibration text-only (vision excluded); verify vision still works post-quantize
- Same smoke gates as Tier 1
- → ship only if T1–T3 cannot meet concurrency target

**Tier 5 — Abort self-hosting**
- All four serving modes fail or quality unacceptable
- Stay on Gemini, escalate to product team
- Document in `eval/v1_quantize_failure.md`

### Smoke gates (apply to whichever tier is being tested)

For each tier, run all four smoke tests:

| Smoke | Sample size | Pass threshold |
|---|---|---|
| Load + `/v1/models` returns model name | 1 | 200 OK with served model name |
| Text generation streaming | 10 prompts | 10/10 produce coherent answer, no NaN tokens |
| Vision (lecture frame) | 10 frames | ≥ 8/10 coherent description (preserve base ability, see README vision scope) |
| Tool-call (re-runs P0.5 gate) | 20 prompts | ≥ 18/20 produce parseable `tool_calls`, 20/20 args valid JSON |
| Pairwise judge vs prior tier | 50 samples | tie-rate ≥ 75% (no quality regression vs uncompressed) |

If any tier fails any smoke: drop to next safer tier. Do NOT skip tiers.

**Backend integration is BLOCKED until at least one tier passes all smokes.**
The plan's original assumption that AWQ would just work is invalidated;
P7 codebase changes must wait for serving proof.

### Exit criteria

- [ ] One of Tier 1–4 selected; document in `eval/v1_quantize_decision.md`
- [ ] Selected model loads in vLLM (P6 smoke test)
- [ ] Quality vs merged fp16: judge tie-rate ≥ 75%
- [ ] Vision path verified working (not silently broken)
- [ ] Tool-call path verified (Gate 1 deterministic checks repeated post-quant)
