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

## Train env setup

```bash
cd D:/VSCODE/VINAI/A20-App-049/fine-tune-chatbot
uv venv .venv-train --python 3.11
source .venv-train/Scripts/activate    # Windows Git Bash
# or: .venv-train\Scripts\activate     # PowerShell

# PyTorch nightly with CUDA 12.8
uv pip install --pre torch torchvision \
  --index-url https://download.pytorch.org/whl/nightly/cu128

# Verify GPU
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0), torch.cuda.get_device_capability())"
# Expected: True NVIDIA GeForce RTX 5060 Ti (12, 0)

# Unsloth (latest dev — has Blackwell wheels)
uv pip install "unsloth[cu128] @ git+https://github.com/unslothai/unsloth.git"
uv pip install --upgrade transformers datasets accelerate trl peft bitsandbytes pillow

# AWQ for quantization (P5)
uv pip install autoawq
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

## Fallbacks if Blackwell fails

| Symptom | Workaround |
|---|---|
| PyTorch nightly missing sm_120 | Pin to specific known-good nightly; or use `cu126` + recompile a few kernels |
| bitsandbytes no kernels | Use `torchao` int4 instead (Unsloth supports both) |
| vLLM prebuilt fails | Build from source: `git clone vllm-project/vllm && pip install -e . --no-build-isolation` (45–90 min) |
| All else fails | Use **Hugging Face TGI** (`ghcr.io/huggingface/text-generation-inference`) or **SGLang** as alt servers — both support Blackwell earlier than vLLM historically |

## Exit criteria for P1

- [ ] All 4 smoke tests pass
- [ ] VRAM headroom verified: 3B-VL 4bit + LoRA + ctx 4K + bs 2 ≤ 12GB
- [ ] vLLM (or alt server) returns valid responses for VL-3B base model
- [ ] Document exact pinned versions in `fine-tune-chatbot/scripts/env-frozen.txt`
      (`uv pip freeze > scripts/env-frozen.txt`)

Only then proceed to P2.
