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
P2  Data pipeline      (1–3d)  Extract from qa_history.jsonl + recover images
P3  Fine-tune          (0.5d)  Unsloth QLoRA on VL-3B
P4  Eval               (0.5d)  LLM-judge vs Gemini baseline
P5  Quantize           (0.5d)  AWQ Int4 for vLLM
P6  Serve              (0.5d)  vLLM docker service
P7  Codebase changes   (0.5d)  Patch chat_model_factory + config
P8  Shadow + rollout   (1w)    A/B with 10% → 50% → 100%
```

Total: ~5–7 working days excluding shadow period.

## Repository layout (this folder)

```
fine-tune-chatbot/
├── plan/                        # ← you are here
│   ├── README.md                # overview, decisions, roadmap
│   ├── 01-environment.md        # Blackwell GPU stack setup
│   ├── 02-data-pipeline.md      # SFT data extraction + image recovery
│   ├── 03-finetune.md           # Unsloth QLoRA training
│   ├── 04-eval-quantize.md      # eval harness + AWQ Int4
│   ├── 05-serving-vllm.md       # vLLM docker service
│   ├── 06-codebase-changes.md   # exact patches to src/
│   └── 07-rollout.md            # shadow, rollout, risks, runbook
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
- [ ] LLM-judge score ≥ Gemini baseline − 5% on 500-sample eval set
- [ ] p50 streaming latency ≤ 4s, p95 ≤ 10s on production traffic
- [ ] Vision questions answered correctly on ≥ 80% of vision eval subset
- [ ] Shadow A/B 1 week passes; 100% rollout with Gemini fallback armed
- [ ] Zero net code changes to `llm_service.py`, `router.py`, LangGraph
