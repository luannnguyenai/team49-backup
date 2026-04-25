# Fine-tune Chatbot — Self-hosted AI Tutor

Replace the current API-based AI Tutor (Gemini/OpenAI/Anthropic via LangChain
`init_chat_model`) with a **self-hosted fine-tuned VLM** running on local GPU.

## Decisions (locked)

| Item | Value |
|---|---|
| GPU | RTX 5060 Ti 16GB (Blackwell, sm_120) |
| Base model | **Qwen2.5-VL-3B-Instruct** (vision-language, native tool calling) |
| Fine-tune framework | **Unsloth** (QLoRA, 4-bit) |
| Serving framework | **vLLM** (OpenAI-compatible API + Hermes tool parser) |
| Quantization for serving | AWQ Int4 |
| Provider name in code | `self_hosted` |
| Vision support | Native (Qwen VL handles `image_base64` in current pipeline) |
| Fallback | Gemini API kept as runtime fallback when vLLM is down |

## Where to fine-tune

**Decision**: fine-tune locally first on the RTX 5060 Ti 16GB. Use Colab only as
a fallback if Blackwell wheels or vLLM/Unsloth kernels fail locally. Use Kaggle
only for smoke tests or small data-pipeline experiments, not as the primary
training environment.

As of 2026-04-25, Colab and Kaggle GPU availability/limits are dynamic rather
than guaranteed. Re-check quotas and assigned GPU type before starting a long
run.

| Option | Best use | Pros | Cons / risk | Fit for this plan |
|---|---|---|---|---|
| **Local PC: RTX 5060 Ti 16GB** | Primary QLoRA training, eval, quantization, and vLLM serving rehearsal | Same GPU class as production serving; no notebook timeout; artifacts stay local; easiest to debug Docker/vLLM integration; no dataset upload/privacy issue | Blackwell stack risk (`sm_120`): PyTorch/Unsloth/bitsandbytes/vLLM may require nightly/source builds; 16GB VRAM leaves little room for larger ctx/batch | **Recommended primary path**. Run P1 smoke tests first, then P2-P7 locally. |
| **Google Colab** | Fallback training or isolated benchmark when local Blackwell stack fails | Zero local setup; paid plans may access premium GPUs subject to availability; easy notebook iteration | GPU type and limits vary; sessions/timeouts can interrupt runs; compute units can drain quickly on premium GPUs; environment differs from final local serving box | **Good fallback** for P3 training only. Export adapter/merged model back to local for P4-P7. |
| **Kaggle Notebooks** | Smoke tests, small prototypes, data cleaning notebooks | Free GPU access; convenient dataset/notebook workflow; usually enough for small text-only QLoRA experiments | Weekly accelerator quota and session limits; assigned hardware may be P100/T4 class; less control over CUDA/kernel versions; poor fit for vLLM serving validation | **Not primary**. Use for P2/P3 prototype only if local is blocked. |

Practical rule:
- If P1 passes locally: stay local end-to-end.
- If local training fails but data pipeline is ready: run P3 on Colab, then copy
  `checkpoints/` and `models/` back locally for eval, quantization, serving, and
  rollout.
- If both local and Colab are blocked: reduce scope to text-only LoRA, lower
  `max_seq_length` to 3072, or postpone self-hosting until a more predictable
  GPU environment is available.

References for current constraints:
- Colab FAQ: resource limits and GPU types vary over time; paid premium GPUs
  are subject to availability:
  <https://research.google.com/colaboratory/intl/en-GB/faq.html>
- Google Workspace Colab subscriptions: Colab Pro examples use compute units:
  <https://support.google.com/a/answer/15094583>
- NVIDIA/Kaggle blog: Kaggle accelerator quota example of 30h/week:
  <https://developer.nvidia.com/blog/how-kaggle-makes-gpus-accessible-to-5-million-data-scientists/>
- RTX 5060 Ti 16GB reference specs:
  <https://www.techpowerup.com/gpu-specs/geforce-rtx-5060-ti-16-gb.c4292>

## Why VL-3B over alternatives

- **vs Qwen2.5-7B text**: keeps vision feature self-hosted (current code path
  already passes `image_base64` to LLM in `src/services/llm_service.py`).
- **vs Qwen2.5-VL-7B**: 7B-VL is too tight on 16GB during QLoRA train (OOM
  risk). 3B-VL leaves headroom for ctx 4K + bs 2 + LoRA r=16.
- **Trade-off accepted**: weaker reasoning and tool-calling than 7B. Mitigated
  by oversampling tool-call examples in training data (target 35%) and keeping
  Gemini fallback for COMPLEX-tool failures.

## Roadmap

```
P1  Environment        (0.5d)  Verify Blackwell stack (CUDA 12.8, PT 2.7+)
P2a Data audit         (0.5d)  Schema/row counts before extraction
P2  Data pipeline      (1–3d)  Extract + clean + ChatML format
P3  Fine-tune          (0.5d)  Unsloth QLoRA on VL-3B (incl. tiny overfit smoke)
P4  Eval               (0.5d)  Deterministic gates + LLM-judge vs Gemini
P5  Quantize           (0.5d)  AWQ Int4 + feasibility gate (fallback to bnb/fp16)
P6  Serve              (0.5d)  vLLM docker service
P7  Codebase changes   (0.5d)  Patch chat_model_factory + config + tests
P8  Shadow + rollout   (1w)    A/B with 10% → 50% → 100%
```

Total: ~5–7 working days excluding shadow period.

File mapping: `01-environment.md` (P1), `02a-data-audit.md` (P2a),
`02-data-pipeline.md` (P2), `03-finetune.md` (P3), `04-eval-quantize.md`
(P4+P5), `05-serving-vllm.md` (P6), `06-codebase-changes.md` (P7),
`07-rollout.md` (P8).

## Repository layout (this folder)

```
fine-tune-chatbot/
├── plan/                        # ← you are here
│   ├── README.md                # overview, decisions, roadmap, governance
│   ├── 01-environment.md        # P1 Blackwell GPU stack setup
│   ├── 02a-data-audit.md        # P2a schema/row audit (run BEFORE P2)
│   ├── 02-data-pipeline.md      # P2 SFT data extraction + ChatML format
│   ├── 03-finetune.md           # P3 Unsloth QLoRA + tiny overfit smoke
│   ├── 04-eval-quantize.md      # P4 eval gates + P5 AWQ quantize
│   ├── 05-serving-vllm.md       # P6 vLLM docker service
│   ├── 06-codebase-changes.md   # P7 patches to src/ + tests
│   ├── 07-rollout.md            # P8 shadow, rollout, risks, runbook
│   ├── datasets.md              # external dataset catalog for FT
│   └── gpt_response.md          # GPT review (resolved in this README)
├── scripts/                     # (created during P2–P5)
├── data/                        # (gitignored) SFT datasets
├── checkpoints/                 # (gitignored) training output
└── models/                      # (gitignored) merged + AWQ weights
```

## Out of scope (v1)

- Vision fine-tuning data quality (depends on P2 image recovery — see
  `02-data-pipeline.md` BLOCKER section).
- Multi-GPU serving.
- Reward modeling / DPO.
- Fine-tuning the router LLM (`src/services/router.py`) — keep Gemini for now.
- Multi-tenant rate limiting on self-hosted endpoint (vLLM handles concurrency
  via `--max-num-seqs`).

## Reading order

1. Read this README.
2. **`01-environment.md`** — do P1 first to verify Blackwell wheel availability.
   This is the riskiest phase and must succeed before investing in data work.
3. Then P2 → P8 in order.

## Success criteria

- [ ] vLLM serves `tutor-v1` endpoint, OpenAI-compatible, streaming works
- [ ] Tool calling (`execute_python`) works end-to-end via `--tool-call-parser hermes`
- [ ] **Deterministic eval gates pass** (see `04-eval-quantize.md` Gate 1)
- [ ] **Per-category LLM-judge gates pass** vs Gemini baseline:
  - Refusal: A score ≥ B − 0.1
  - Tool correctness: A correct rate ≥ B − 10%
  - Factual QA: A score ≥ B − 0.2
  - Vision subset (frozen-tower v1): A score ≥ B − 0.5
  - Aggregate pairwise A vs B win-rate ≥ 45%
- [ ] p50 streaming latency ≤ 4s, p95 ≤ 10s on production traffic
- [ ] Shadow A/B 1 week passes; 100% rollout with Gemini fallback armed
- [ ] No user-facing API route changes
- [ ] Router stays on Gemini in v1 (no migration)
- [ ] LangGraph topology preserved; only LLM provider injection point and
      fallback wrapper change (see `06-codebase-changes.md`)

## Data governance

- **Local-only training data**: `qa_history.jsonl`, DB exports, lecture
  transcripts, and lecture frames stay on the local machine. No upload to
  Colab, Kaggle, or third-party services.
- **PII scrub mandatory** before any data leaves the database (see P2 step 03).
- **Synthetic data labeling**: any sample produced by a teacher model
  (Gemini Pro / Claude) must carry `source: synthetic_<teacher_model>` in
  the manifest.
- **Eval outputs gitignored**: only aggregated reports (`eval/v1_report.md`)
  are committed; raw per-sample outputs (`eval/runs/`) are local-only.
- **Lecture content**: copyrighted course material — used internally for
  training; do not redistribute weights externally without legal review.
- **Retention**: training datasets and intermediate checkpoints are kept on
  local disk; merged + quantized model weights are the only artifact mounted
  into the production container.
