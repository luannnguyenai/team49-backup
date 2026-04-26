# P3 — Fine-tune (Unsloth QLoRA on Qwen2.5-VL-3B)

**Goal**: produce LoRA adapter `checkpoints/tutor-vl3b-v1/` and merged
weights `models/tutor-vl3b-v1-merged/`.

**Duration**: 0.5 day (training itself ~2–4h on 5060 Ti).

## Configuration

| Hyperparameter | Value | Rationale |
|---|---|---|
| Base | `unsloth/Qwen2.5-VL-3B-Instruct-bnb-4bit` | 4-bit pre-quantized for QLoRA |
| `finetune_vision_layers` | `False` | Keep vision tower frozen (Option C) |
| `finetune_language_layers` | `True` | Train text adapters |
| `finetune_attention_modules` | `True` | LoRA on attention |
| `finetune_mlp_modules` | `True` | LoRA on MLP |
| LoRA `r` | 16 | 3B doesn't need 32; reduce overfit |
| LoRA `alpha` | 16 | Match `r` (alpha/r = 1) |
| LoRA dropout | 0.05 | Regularization |
| `max_seq_length` | 4096 | Fits with bs=2 on 16GB |
| `per_device_train_batch_size` | 2 | Memory-bound |
| `gradient_accumulation_steps` | 8 | Effective batch = 16 |
| `num_train_epochs` | 3 | Avoid overfit on 10k samples |
| `learning_rate` | 2e-4 | Standard for QLoRA |
| `lr_scheduler_type` | cosine | — |
| `warmup_ratio` | 0.03 | — |
| `bf16` | True | Blackwell native |
| `optim` | adamw_8bit | bitsandbytes 8-bit Adam |
| `packing` | False | VL samples have variable image tokens — packing breaks |
| `gradient_checkpointing` | "unsloth" | Memory saver |
| Eval frequency | every 100 steps | Catch overfit early |
| Save frequency | every 200 steps, keep best 2 | — |

## Training script

`fine-tune-chatbot/scripts/train/train_tutor.py`:

```python
import json, os, torch
from datasets import load_dataset
from unsloth import FastVisionModel
from unsloth.trainer import UnslothVisionDataCollator
from trl import SFTTrainer, SFTConfig

OUT = "checkpoints/tutor-vl3b-v1"
MERGED = "models/tutor-vl3b-v1-merged"

model, processor = FastVisionModel.from_pretrained(
    "unsloth/Qwen2.5-VL-3B-Instruct-bnb-4bit",
    load_in_4bit=True,
    use_gradient_checkpointing="unsloth",
    max_seq_length=4096,
)

model = FastVisionModel.get_peft_model(
    model,
    r=16, lora_alpha=16, lora_dropout=0.05,
    bias="none",
    finetune_vision_layers=False,
    finetune_language_layers=True,
    finetune_attention_modules=True,
    finetune_mlp_modules=True,
    target_modules="all-linear",
    random_state=42,
)

train = load_dataset("json", data_files="data/sft/train.jsonl", split="train")
val   = load_dataset("json", data_files="data/sft/val.jsonl",   split="train")

trainer = SFTTrainer(
    model=model,
    tokenizer=processor.tokenizer,
    data_collator=UnslothVisionDataCollator(model, processor),
    train_dataset=train,
    eval_dataset=val,
    args=SFTConfig(
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,
        num_train_epochs=3,
        learning_rate=2e-4,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        bf16=True,
        optim="adamw_8bit",
        weight_decay=0.0,

        eval_strategy="steps",
        eval_steps=100,
        save_strategy="steps",
        save_steps=200,
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",

        logging_steps=10,
        report_to=["tensorboard"],

        remove_unused_columns=False,
        dataset_kwargs={"skip_prepare_dataset": True},
        dataset_text_field="",
        max_seq_length=4096,

        output_dir=OUT,
        seed=42,
    ),
)

stats = trainer.train()
print("Train metrics:", stats.metrics)

# Save adapter only
trainer.model.save_pretrained(OUT)
processor.save_pretrained(OUT)

# Save merged 16-bit (for AWQ next step)
trainer.model.save_pretrained_merged(MERGED, processor.tokenizer, save_method="merged_16bit")
```

## VRAM budget (5060 Ti 16GB)

Expected at peak step:

| Component | VRAM |
|---|---|
| Model weights (4bit) | ~2.5 GB |
| LoRA params (fp16) | ~0.05 GB |
| Activations + grads (bs=2, ctx=4096, with checkpointing) | ~8–9 GB |
| Optimizer state (adamw_8bit) | ~0.5 GB |
| KV cache for forward | ~1 GB |
| Image tower forward (vision samples) | ~1 GB |
| **Peak** | **~13–14 GB** ✅ fits |

If OOM during first 100 steps:
1. Drop `max_seq_length` to 3072
2. Drop `per_device_train_batch_size` to 1, `grad_accum` to 16
3. Set `finetune_attention_modules=True, finetune_mlp_modules=False`

## Monitoring

```bash
tensorboard --logdir checkpoints/tutor-vl3b-v1 --port 6006
```

Watch:
- `train/loss` — should drop monotonically. If stuck >2.0 after epoch 1: bug.
- `eval/loss` — should track train loss within 0.1–0.2. If diverges upward
  after step 500: overfitting → early stop.
- `train/grad_norm` — spikes >10 indicate instability → lower `lr` to 1e-4.

`nvidia-smi -l 5` in another terminal to confirm VRAM usage and no thermal
throttling (5060 Ti can hit 80°C+ under sustained load — clean fans, ensure
case airflow).

## Estimated training time

- 10k samples × 3 epochs / (effective batch 16) = ~1875 steps
- 5060 Ti at ~0.7 it/s with bs=2 ctx=4096 VL = ~2700s ≈ **45 min per epoch**
- Plus vision samples are heavier: realistic **2–4 hours total**

## Post-train sanity check

```python
# fine-tune-chatbot/scripts/train/verify.py
from unsloth import FastVisionModel
from PIL import Image

model, processor = FastVisionModel.from_pretrained(
    "checkpoints/tutor-vl3b-v1", load_in_4bit=True,
)
FastVisionModel.for_inference(model)

# 5 fixed test questions from data/sft/test.jsonl
for sample in load_first_n_test(5):
    out = generate(model, processor, sample)
    print("Q:", sample["question"][:80])
    print("A:", out[:200])
    print("---")
```

If outputs are gibberish or repeat tokens → adapter loaded wrong, debug
before merging.

## Exit criteria

- [ ] Best `eval_loss` ≤ 1.5 (rough heuristic — depends on data)
- [ ] No OOM, no NaN losses
- [ ] `models/tutor-vl3b-v1-merged/` exists with valid `config.json` +
      tokenizer + safetensors
- [ ] 5 manual sample outputs look reasonable (subjective gate)
- [ ] Tool-call format preserved in at least one of 5 samples (look for
      `<tool_call>` tags or function-call JSON)
