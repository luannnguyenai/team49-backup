# P1 — Environment Setup (Blackwell sm_120)

**Goal**: prove the full Unsloth + vLLM stack runs on RTX 5060 Ti **before**
investing time in data prep.

**Duration**: ~0.5 day. **Critical path** — failure here blocks everything.

## Why this is risky

RTX 5060 Ti uses Blackwell (sm_120). As of late 2025 / early 2026:

- PyTorch stable wheels may lack sm_120 → need nightly with CUDA 12.8
- bitsandbytes < 0.45 has no Blackwell kernels
- vLLM prebuilt images may target sm_90/sm_100 only → may need source build
- Unsloth's `xformers` / Triton backends need recent versions

**Verify first, plan later.** If wheels are missing, fallback options at the
bottom of this doc.

## Hardware / driver baseline

```bash
nvidia-smi   # confirm:
#   Driver Version ≥ 555 (Blackwell support)
#   CUDA Version ≥ 12.8
#   Memory: 16384 MiB
```

If driver < 555: install latest NVIDIA Studio/Game Ready driver before anything.

## Two separate environments

We use **two virtualenvs** — train and serve have conflicting dependencies
(Unsloth pins specific torch versions, vLLM pins different ones).

```
.venv-train/   # Unsloth + transformers + datasets + bitsandbytes + autoawq
.venv-serve/   # vLLM only (or use docker — preferred)
```

Serving will run via **docker container** in production (see `05-serving-vllm.md`),
so `.venv-serve` is only for local smoke tests.

## Train env setup — VERIFY-THEN-INSTALL

⚠️ **The commands below are CANDIDATES, not locked.** Blackwell support
moves week-to-week across Unsloth, vLLM, bitsandbytes, PyTorch, xformers.
Do NOT run any command without first verifying it against the current
official docs at install time.

### Step 1 — Read official docs first (mandatory)

Open in browser before running anything:
- Unsloth Blackwell install guide: <https://docs.unsloth.ai/get-started/installing-+-updating>
- vLLM compatibility matrix: <https://docs.vllm.ai/en/latest/getting_started/installation.html>
- PyTorch nightly index: <https://download.pytorch.org/whl/nightly/>
- bitsandbytes Blackwell status: <https://github.com/bitsandbytes-foundation/bitsandbytes/issues>
  (search "sm_120" / "Blackwell")

If any of these doc pages contradict the candidate commands below at the
time you run them, **trust the docs, not this plan**.

### Step 2 — Candidate commands (verify first)

```bash
cd D:/VSCODE/VINAI/A20-App-049/fine-tune-chatbot
uv venv .venv-train --python 3.11
source .venv-train/Scripts/activate    # Windows Git Bash
# or: .venv-train\Scripts\activate     # PowerShell

# PyTorch nightly with CUDA 12.8 — VERIFY index URL/version per docs
uv pip install --pre torch torchvision \
  --index-url https://download.pytorch.org/whl/nightly/cu128

# Verify GPU
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0), torch.cuda.get_device_capability())"
# Expected: True NVIDIA GeForce RTX 5060 Ti (12, 0)

# Unsloth — CANDIDATE; the [cu128] extra may not exist or may be renamed
# Verify on https://github.com/unslothai/unsloth README before running
uv pip install "unsloth[cu128] @ git+https://github.com/unslothai/unsloth.git"
# Common alternatives if [cu128] extra is missing:
#   uv pip install "unsloth @ git+https://github.com/unslothai/unsloth.git"
#   uv pip install unsloth-zoo  # may also be needed depending on Unsloth release

uv pip install --upgrade transformers datasets accelerate trl peft bitsandbytes pillow

# AWQ for quantization (P5) — also verify version Blackwell support
uv pip install autoawq
```

### Step 3 — Mandatory output artifacts after install

```
fine-tune-chatbot/scripts/env/
├── env-frozen.txt          # uv pip freeze > env-frozen.txt
├── install-notes.md        # ACTUAL commands run + any deviations from candidates
└── smoke_results.json      # machine-readable results from smoke tests below
```

`install-notes.md` template:
```
# Install run YYYY-MM-DD HH:MM
- OS: Windows 11 / WSL2 / Linux ...
- Driver version: ...
- CUDA version: ...
- PyTorch version installed: ...
- Unsloth install command actually used (after verifying docs): ...
- bitsandbytes version: ...
- Any deviation from plan candidates: ...
- Issues encountered: ...
```

`smoke_results.json` schema:
```json
{
  "torch_version": "...",
  "torch_cuda_capability": [12, 0],
  "bnb_available": true,
  "smoke_01_load_vl3b": {"passed": true, "vram_gb": 2.7, "notes": "..."},
  "smoke_02_inference": {"passed": true, "first_token_ms": 450, "notes": "..."},
  "smoke_03_train_step": {"passed": true, "final_loss": 1.8, "notes": "..."},
  "smoke_04_vllm": {"passed": true, "image_tag_used": "...", "notes": "..."},
  "p0_5_toolcall_format": {"passed": true, "vllm_returned_tool_calls_field": true}
}
```

## Smoke test 1 — load Qwen2.5-VL-3B in 4-bit

```python
# fine-tune-chatbot/scripts/smoke/01_load_vl3b.py
from unsloth import FastVisionModel
import torch

model, processor = FastVisionModel.from_pretrained(
    "unsloth/Qwen2.5-VL-3B-Instruct-bnb-4bit",
    load_in_4bit=True,
    use_gradient_checkpointing="unsloth",
)
print("OK — VRAM:", torch.cuda.memory_allocated() / 1e9, "GB")
```

Expected output: `OK — VRAM: ~2.5–3.0 GB`. If OOM here, GPU is broken.

## Smoke test 2 — vision + text generation

```python
# fine-tune-chatbot/scripts/smoke/02_vl3b_inference.py
from unsloth import FastVisionModel
from PIL import Image

model, processor = FastVisionModel.from_pretrained(
    "unsloth/Qwen2.5-VL-3B-Instruct-bnb-4bit", load_in_4bit=True,
)
FastVisionModel.for_inference(model)

img = Image.open("fine-tune-chatbot/scripts/smoke/sample_lecture.jpg")
messages = [{"role": "user", "content": [
    {"type": "image"},
    {"type": "text", "text": "Mô tả slide này bằng tiếng Việt."},
]}]

input_text = processor.apply_chat_template(messages, add_generation_prompt=True)
inputs = processor(image=img, text=input_text, return_tensors="pt").to("cuda")
out = model.generate(**inputs, max_new_tokens=200, do_sample=False)
print(processor.decode(out[0], skip_special_tokens=True))
```

Provide one lecture screenshot at `sample_lecture.jpg`. Pass = coherent
Vietnamese description referencing the image.

## Smoke test 3 — short LoRA train step (10 steps)

Just to verify backprop + LoRA + grad checkpoint work on Blackwell.

```python
# fine-tune-chatbot/scripts/smoke/03_train_step.py
from unsloth import FastVisionModel
from datasets import Dataset
from trl import SFTConfig, SFTTrainer

model, processor = FastVisionModel.from_pretrained(
    "unsloth/Qwen2.5-VL-3B-Instruct-bnb-4bit", load_in_4bit=True,
    use_gradient_checkpointing="unsloth",
)
model = FastVisionModel.get_peft_model(
    model, r=16, lora_alpha=16,
    target_modules=["q_proj","k_proj","v_proj","o_proj"],
    finetune_vision_layers=False,   # text-only adapter for smoke
)

# 10 dummy text-only samples
ds = Dataset.from_list([{"text": f"Q{i}: 2+2? A: 4."} for i in range(10)])

trainer = SFTTrainer(
    model=model, tokenizer=processor.tokenizer, train_dataset=ds,
    args=SFTConfig(per_device_train_batch_size=1, max_steps=10,
                   learning_rate=2e-4, output_dir="/tmp/smoke", bf16=True,
                   max_seq_length=1024),
)
trainer.train()
print("Train loop OK")
```

Pass = no CUDA error, loss decreases.

## Smoke test 4 — vLLM Blackwell

Try prebuilt image first:

```bash
docker pull vllm/vllm-openai:latest
docker run --rm --gpus all -p 8001:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai:latest \
  --model Qwen/Qwen2.5-VL-3B-Instruct \
  --max-model-len 4096 --gpu-memory-utilization 0.85
```

Then in another shell:
```bash
curl http://localhost:8001/v1/models
curl http://localhost:8001/v1/chat/completions -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen2.5-VL-3B-Instruct","messages":[{"role":"user","content":"Hi"}]}'
```

Pass = response returned. If `CUDA error: no kernel image is available for execution on the device`
→ Blackwell unsupported in this image, see fallbacks below.

## Smoke test 5 (P0.5) — Tool-call format compatibility proof — BLOCKING

**This gate is the single highest-value check in P1. Skipping it risks
invalidating the entire training corpus.**

The plan trains on Qwen ChatML messages with assistant `tool_calls` JSON
field. At inference, vLLM with `--tool-call-parser hermes` parses the
**model's text output** to construct `choices[].message.tool_calls`.
**Training format ≠ inference format** is a real failure mode — model
learns the structured field but does not emit Hermes-parseable text at
inference.

### Procedure

1. **Author 20 sample tool-call training examples** in your candidate
   converter format (the format that `scripts/sft/convert_hermes_to_chatml.py`
   would emit). Save to `fine-tune-chatbot/data/format_proof/sample20.jsonl`.

2. **Tiny adapter run** (~50 steps) on these 20 samples using the same
   Unsloth config as the real train, but `max_steps=50, num_train_epochs=ignored`.
   Save adapter to `checkpoints/p0_5_format_proof/`.

3. **Serve the tiny adapter via vLLM** with full production flags:
   ```bash
   docker run --rm --gpus all -p 8002:8000 \
     -v $(pwd)/checkpoints/p0_5_format_proof:/model \
     -v ~/.cache/huggingface:/root/.cache/huggingface \
     vllm/vllm-openai:<verified-tag> \
     --model /model \
     --enable-auto-tool-choice \
     --tool-call-parser hermes \
     --max-model-len 2048 \
     --gpu-memory-utilization 0.6 \
     --trust-remote-code
   ```
   (If LoRA hot-load preferred, use `--enable-lora --lora-modules` instead;
   either path must produce parsed tool calls.)

4. **Send 10 tool-required test prompts** matching the production tutor
   shape (e.g., "Tính tổng các số nguyên tố nhỏ hơn 100"):
   ```bash
   for q in "${test_qs[@]}"; do
     curl -s http://localhost:8002/v1/chat/completions -H 'Content-Type: application/json' -d '{
       "model": "/model",
       "messages": [{"role":"user","content":"'"$q"'"}],
       "tools": [...execute_python schema...],
       "tool_choice": "auto"
     }' | jq '.choices[0].message'
   done
   ```

### Pass criteria (must all hold)

- [ ] At least **8 of 10** responses contain non-null `tool_calls` array
- [ ] Each populated `tool_calls[].function.name == "execute_python"`
- [ ] Each `tool_calls[].function.arguments` is valid JSON parseable into
      `{"code": "..."}`
- [ ] No raw Hermes XML leaks into `content` field (parser ate the markers
      cleanly)

### If fails

Plan stops. Investigate format converter:
- Try **Qwen native tool format** (Qwen 2.5 supports it; may not need Hermes
  parser); if so, switch to `--tool-call-parser qwen` if available, OR train
  on Qwen native tool format syntax
- Try **explicit Hermes XML in training data** (`<tool_call>...</tool_call>`
  text spans in assistant content) instead of structured `tool_calls` field
- Inspect raw model output (set `tool_choice: "none"` to see what tokens the
  model actually emits when it wants to call a tool)

Do NOT proceed to P2b/P3 until format proof passes. Up to **1 working day**
debug budget; if still failing, escalate before continuing.

### Output

Append to `smoke_results.json`:
```json
"p0_5_toolcall_format": {
  "passed": true,
  "samples_with_toolcalls": 9,
  "argument_parse_success": 9,
  "format_used_in_training": "hermes_xml" | "qwen_native" | "structured_field",
  "vllm_parser_flag": "--tool-call-parser hermes",
  "notes": "..."
}
```

## Fallbacks if Blackwell fails

| Symptom | Workaround |
|---|---|
| PyTorch nightly missing sm_120 | Pin to specific known-good nightly; or use `cu126` + recompile a few kernels |
| bitsandbytes no kernels | Use `torchao` int4 instead (Unsloth supports both) |
| vLLM prebuilt fails | Build from source: `git clone vllm-project/vllm && pip install -e . --no-build-isolation` (45–90 min) |
| All else fails | Use **Hugging Face TGI** (`ghcr.io/huggingface/text-generation-inference`) or **SGLang** as alt servers — both support Blackwell earlier than vLLM historically |

## Exit criteria for P1 + P0.5

- [ ] All 4 smoke tests pass
- [ ] **P0.5 tool-call format proof passes** (≥ 8/10 parsed, format choice
      committed and documented in `smoke_results.json`)
- [ ] VRAM headroom verified: 3B-VL 4bit + LoRA + ctx 4K + bs 2 ≤ 12GB
- [ ] vLLM (or alt server) returns valid responses for VL-3B base model
- [ ] Document exact pinned versions in `fine-tune-chatbot/scripts/env/env-frozen.txt`
      (`uv pip freeze > scripts/env/env-frozen.txt`)
- [ ] `install-notes.md` and `smoke_results.json` committed (no secrets)

If any of the above fails: do NOT proceed to P2. Apply auto-escalation
rule from README (FAST → FULL switch if > 8h spent here).
