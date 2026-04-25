# External Datasets for Fine-tuning

This catalog supplements organic data from `qa_history.jsonl`. Use these
**only if** P2a audit shows organic data is insufficient (< 8k usable rows
or < 1500 tool-call samples), OR to inject specific capabilities (math
reasoning, refusal patterns, function-calling format adherence).

⚠️ **All datasets must be downloaded once and cached locally.** Per data
governance in README, no organic `qa_history` data leaves the machine; but
public HF datasets can be cached in `~/.cache/huggingface/`.

⚠️ **License compliance**: each table column shows the license. Do NOT use
non-commercial datasets if the resulting model is intended for commercial
deployment. Cross-check with project legal scope.

## Priority tiers

| Tier | Purpose | When to use |
|---|---|---|
| **Tier 1 (must)** | Function-calling format, Vietnamese instruction | Use in every training run |
| **Tier 2 (recommended)** | Math reasoning, refusal/safety | Use if organic counts low |
| **Tier 3 (optional)** | General multi-turn chat, vision-language | Use only if specific gap |

---

## Tier 1 — Must-have

### 1.1 Function-calling (preserve tool-use capability)

| Dataset | Size | Format | License | Why |
|---|---|---|---|---|
| `NousResearch/hermes-function-calling-v1` | ~10K rows across 5 subsets (`func_calling_singleturn`, `func_calling`, `glaive_func_calling`, `json_mode_agentic`, `json_mode_singleturn`) | **Hermes XML** (`<tools>...</tools>`, `<tool_call>...</tool_call>`) | Apache-2.0 | **Direct format match** with vLLM `--tool-call-parser hermes`. This is the gold standard for our serving setup. |
| `Salesforce/xlam-function-calling-60k` | 60K | JSON (query/tools/answers) | CC-BY-4.0 | High quality, human-verified ≥95%; needs format conversion to ChatML+Hermes. Use APIGen pipeline output style. |
| `glaiveai/glaive-function-calling-v2` | ~113K | ChatML with `<functioncall>` tags | Apache-2.0 | Large volume; useful for diversity. Older format — convert to Hermes before mixing. |

**Recommended sampling**: 2k–3k from `hermes-function-calling-v1` (esp. the
`func_calling_singleturn` subset for our single-tool case) + 1k from
`xlam-function-calling-60k` filtered to single-tool / math-related queries.

**Format conversion**: write `scripts/sft/convert_hermes_to_chatml.py` to
map Hermes XML to Qwen2.5 chat template with `tool_calls` field.

### 1.2 Vietnamese instruction (preserve VN quality)

| Dataset | Size | Format | License | Why |
|---|---|---|---|---|
| `5CD-AI/Vietnamese-meta-math-MetaMathQA-40K-gg-translated` | 40K | Q/A | Apache-2.0 | High-quality VN math via Google Translate from MetaMathQA. Critical for VN math tutor. |
| `5CD-AI/Vietnamese-microsoft-orca-math-word-problems-200k-gg-translated` | 200K | Q/A | MIT | Vietnamese math word problems. Subsample 5k–10k. |
| `5CD-AI/Vietnamese-nvidia-OpenMathInstruct-1-50k-gg-translated` | 50K | Q/A with code | Apache-2.0 | **VN math + code** — perfect for our `execute_python` flow. Highly recommended. |
| `5CD-AI/Viet-r1_90k_instruct` | 80K | Instruct | Check on HF | Reasoning-style VN instruction (R1-distilled). Useful for COMPLEX route training. |
| `bkai-foundation-models/vi-self-chat-sharegpt-format` | ~80K | ShareGPT | Apache-2.0 | Multi-turn VN conversations. Useful for tutor follow-up Q&A patterns. |
| `vilm/OpenOrca-Viet` | ~150K | Alpaca-like | MIT | Translated OpenOrca. Strong general instruction following in VN. Subsample. |

**Recommended sampling**: 5k from `Vietnamese-nvidia-OpenMathInstruct` +
3k from `vi-self-chat-sharegpt-format` + 2k from `Viet-r1_90k_instruct`
(reasoning).

---

## Tier 2 — Recommended

### 2.1 Math reasoning (English, for reasoning skill transfer)

| Dataset | Size | Format | License | Why |
|---|---|---|---|---|
| `meta-math/MetaMathQA` | 395K | Q/A | MIT | Source of the VN translation above. Use English version if VN corpus too small. |
| `TIGER-Lab/MathInstruct` | 262K | Q/A with CoT + PoT (program-of-thought) | MIT | **Includes Python code solutions** — direct match for our sandbox use. |
| `nvidia/OpenMathInstruct-2` | 14M | Q/A with code | NVIDIA Open Model License (commercial OK with attribution) | Massive, recent. Heavily subsample (1k–2k). |
| `5CD-AI/Vietnamese-395k-meta-math-MetaMathQA-gg-translated` | 395K | Q/A | Apache-2.0 | Full VN translation; subsample to 5k–10k stratified by difficulty. |

**Caveat**: math problems are not lecture-grounded. They train *reasoning*
not *tutor behavior*. Mix at ≤ 15% of training set.

### 2.2 Refusal / safety / scope adherence

| Dataset | Size | Format | License | Why |
|---|---|---|---|---|
| `Anthropic/hh-rlhf` | 161K | Chosen/rejected pairs | MIT | Helpful + harmless behavior. Use only chosen responses for SFT. |
| `allenai/wildguardmix` | ~92K | Categorized (benign / unsafe / refusal) | ODC-BY-1.0 | Modern refusal patterns; covers prompt injection and jailbreaks. |
| `PKU-Alignment/PKU-SafeRLHF` | ~30K | Pairwise safety prefs | CC-BY-NC-4.0 | **NC license — research only**. Skip if commercial. |

**Recommended sampling**: 500–1000 refusal examples from `wildguardmix` +
custom synthetic refusals matching tutor's BLOCKED route persona ("Câu
hỏi này nằm ngoài phạm vi bài giảng. Hãy quay lại với...").

⚠️ **Format adapt**: tutor's refusal style is specific (politely redirect
to current chapter). Generic "I cannot help" responses from public datasets
will degrade tutor voice. **Recommend**: synthesize 300–500 refusals using
Gemini Pro with the exact tutor system prompt, rather than using public
datasets directly.

---

## Tier 3 — Optional

### 3.1 Multi-turn dialogue (Vietnamese)

| Dataset | Size | Format | License | Why |
|---|---|---|---|---|
| `5CD-AI/Vietnamese-Multi-turn-Chat-Alpaca-gemini` (verify exact ID on HF) | varies | Multi-turn | Apache-2.0 | Multi-turn VN; useful for chat history handling. |
| `OpenAssistant/oasst2` | 161K | Conversation tree | Apache-2.0 | Multilingual including VN; high-quality human-written. |

### 3.2 Vietnamese vision-language (rare!)

For v1 we **freeze the vision tower** so heavy vision FT data isn't needed.
But to keep VL coherent during text-only LoRA:

| Dataset | Size | Format | License | Why |
|---|---|---|---|---|
| `5CD-AI/Viet-Visual-Instructions` | 52.4K | LLaVA-style VQA | Apache-2.0 | Vietnamese visual instruction following. Best-in-class for VN VLM. |
| `5CD-AI/LLaVA-CoT-o1-Instruct` | 58.5K | LLaVA + CoT | Apache-2.0 | Reasoning-heavy VLM data; covers educational diagrams. |
| `5CD-AI/Viet-Doc-VQA-verIII` | 205K | Document VQA | Apache-2.0 | OCR-heavy; useful since lecture slides have lots of text. |
| `5CD-AI/Viet-multimodal-open-r1-8k-verified` | 7K | Multimodal reasoning | Apache-2.0 | High-quality verified VN multimodal reasoning. |

**Recommended sampling for v1 (frozen vision)**: 200–500 random samples
from `Viet-Visual-Instructions` purely to keep the projector aligned
during training. No more — overweighting vision data with frozen tower
wastes capacity.

**For v2 (unfrozen vision)**: 5k–10k from these 4 datasets, stratified.

### 3.3 Educational benchmarks (for eval, NOT training)

Hold out for evaluation only — do **not** train on these:

| Dataset | Size | Use |
|---|---|---|
| `cais/mmlu` | 14K | Subject knowledge; sample subjects matching course catalog |
| `5CD-AI/Vietnamese-mmlu-benchmark` (Zalo) | 14K | VN MMLU equivalent |
| `ura-hcmut/ViMMRC` | varies | VN reading comprehension — proxy for lecture transcript understanding |

These can supplement the held-out test set in P4 Eval.

---

## Mixing recipe (suggested for v1)

Total target: ~10k–12k training samples.

| Source | Count | Pct |
|---|---|---|
| Organic `qa_history` (after P2 cleaning) | 4000–6000 | 40–55% |
| `hermes-function-calling-v1` (singleturn + agentic subsets) | 2000 | 18% |
| `xlam-function-calling-60k` (filtered single-tool) | 1000 | 9% |
| `Vietnamese-nvidia-OpenMathInstruct-1-50k-gg-translated` | 1500 | 13% |
| `bkai-foundation-models/vi-self-chat-sharegpt-format` | 1000 | 9% |
| Synthetic refusals (Gemini-generated, tutor voice) | 500 | 4% |
| `Viet-Visual-Instructions` (vision retention) | 300 | 3% |

**Stratified mix** ensures:
- Tool-call samples ≥ 25% (combined organic + hermes + xlam + math-with-code)
- Vietnamese ≥ 65%
- Vision ≥ 3% (just enough to prevent VL projector drift)
- Refusal ≥ 4%

## Dataset selection checklist (before training)

- [ ] License audit: all datasets allow commercial use OR project is research-only
- [ ] PII check: spot-check 20 random samples per dataset for names/IDs/addresses
- [ ] Language audit: confirm VN ratio ≥ 60% in final mix
- [ ] Format consistency: all samples converted to Qwen2.5 ChatML
- [ ] Tool-call format match: Hermes XML inside `<tools>` and `<tool_call>` tags
- [ ] Tokenizer length stats: p95 < 4096 (matches `max_seq_length`)
- [ ] No data leakage: held-out test set has zero overlap with training mix
      (run MinHash dedup across train ∪ test)
- [ ] Manifest: each sample tagged with `source` field for ablation analysis

## Download script

`fine-tune-chatbot/scripts/sft/download_external.py`:

```python
"""Download external datasets and cache them locally.
Run once; cached in ~/.cache/huggingface/ — large (~5–20GB depending on selection).
"""
from datasets import load_dataset

DATASETS = [
    ("NousResearch/hermes-function-calling-v1", "func_calling_singleturn"),
    ("NousResearch/hermes-function-calling-v1", "json_mode_agentic"),
    ("Salesforce/xlam-function-calling-60k", None),    # may need HF auth + license accept
    ("5CD-AI/Vietnamese-nvidia-OpenMathInstruct-1-50k-gg-translated", None),
    ("5CD-AI/Vietnamese-meta-math-MetaMathQA-40K-gg-translated", None),
    ("bkai-foundation-models/vi-self-chat-sharegpt-format", None),
    ("5CD-AI/Viet-Visual-Instructions", None),
    # ... add others as needed
]

for repo, subset in DATASETS:
    print(f"Downloading {repo}{f' [{subset}]' if subset else ''}...")
    try:
        ds = load_dataset(repo, subset) if subset else load_dataset(repo)
        print(f"  OK — {sum(len(s) for s in ds.values())} rows total")
    except Exception as e:
        print(f"  FAIL: {e}")
```

## Conversion pipeline

After download, each dataset feeds through a converter that emits
unified ChatML:

```
external_raw → format_converter_<source>.py → unified_chatml.jsonl
                                                      ↓
organic_raw → 04_format_chatml.py     →     unified_chatml.jsonl  (combined)
                                                      ↓
                                           07_split.py (stratified)
                                                      ↓
                                      train.jsonl + val.jsonl + test.jsonl
```

Each emitted row carries:
```json
{
  "messages": [...],
  "_meta": {
    "source": "hermes-fc-v1" | "xlam-60k" | "organic-qa" | "synthetic-refusal" | ...,
    "lang": "vi" | "en" | "mixed",
    "has_image": true | false,
    "has_tool_call": true | false,
    "route": "SIMPLE" | "COMPLEX" | "BLOCKED" | "external"
  }
}
```

`_meta` is dropped before training but kept in the manifest for ablations.

## Verification snapshot (HF Hub, 2025-04)

The following datasets were verified to exist on Hugging Face Hub during
plan authoring. If a dataset has been removed/renamed at training time,
fall back to its source citation or a similar dataset from the same
organization.

- ✅ `5CD-AI/*` — confirmed active org with 73 datasets
- ✅ `NousResearch/hermes-function-calling-v1` — 10K+ rows, Hermes XML format
- ✅ `Salesforce/xlam-function-calling-60k` — 60K rows, requires license accept
- ⚠️ Other datasets cited from prior knowledge — verify on download

## Open questions for the team

1. Is the model intended for commercial or research-only use? Affects
   eligibility of CC-BY-NC datasets.
2. Are there course-specific lecture transcripts (e.g., partner
   universities) available for synthetic Q&A generation? This would
   dominate any external dataset for domain alignment.
3. Should we generate a small `domain_specific.jsonl` from `data/`
   lecture transcripts via Gemini Pro (1k–2k samples, in tutor voice)?
   Highest-value addition if budget allows.
