# External Datasets for Fine-tuning

> **⚠️ Read `02b-domain-data.md` FIRST.** Course assets in `data/courses/`
> provide ~1634 quality-gated MCQs and 41 lecture transcripts — they are
> the primary training source. External datasets in this catalog are
> **secondary**, used only to inject capabilities not present in domain
> data (specifically: function-calling format).

This catalog supplements organic data from `qa_history.jsonl` and
domain-converted MCQs. Use these to inject specific capabilities
(function-calling format adherence is the main one).

⚠️ **All datasets must be downloaded once and cached locally.** Per data
governance in README, no organic `qa_history` data leaves the machine; but
public HF datasets can be cached in `~/.cache/huggingface/`.

⚠️ **License compliance**: each table column shows the license. Do NOT use
non-commercial datasets if the resulting model is intended for commercial
deployment. Cross-check with project legal scope.

## Priority tiers

| Tier | Purpose | When to use |
|---|---|---|
| **Tier 0 (eval-only — DO NOT TRAIN ON)** | AI/ML domain benchmarks for held-out evaluation | Always; gates progress |
| **Tier 1 (must)** | Function-calling format, Vietnamese instruction | Use in every training run |
| **Tier 1.5 (must for AI/ML domain)** | Paper-verified AI/ML knowledge benchmarks (small training subsets only) | Use to inject domain reasoning when KG synth alone is insufficient |
| **Tier 2 (recommended)** | Math reasoning, refusal/safety | Use if organic counts low |
| **Tier 3 (optional)** | General multi-turn chat, vision-language | Use only if specific gap |

---

## Tier 0 — Eval-only benchmarks (never train on these)

Held out from training; used in P4 to measure generalization and detect
catastrophic forgetting after fine-tuning. Each is paper-cited and widely
used in published model cards (Llama 3.1, Qwen 2.5, Mistral, Tulu 3,
Zephyr).

| Dataset | Subset | Use | Paper / source |
|---|---|---|---|
| `cais/mmlu` | `STEM` (esp. `college_computer_science`, `machine_learning`, `college_mathematics`, `high_school_mathematics`, `high_school_statistics`) | Knowledge regression check (≤ 5% drop allowed) | Hendrycks et al., "Measuring Massive Multitask Language Understanding", ICLR 2021 |
| `TIGER-Lab/MMLU-Pro` | full | Harder MMLU successor, 10-option | Wang et al., NeurIPS 2024 |
| `TIGER-Lab/TheoremQA` | full | Theorem-application STEM benchmark | Chen et al., "TheoremQA: A Theorem-driven Question Answering Dataset", EMNLP 2023 |
| `openai/gsm8k` | `main` test split | Grade-school math reasoning | Cobbe et al., "Training Verifiers to Solve Math Word Problems", 2021 |
| `hendrycks/competition_math` (MATH) | test split | Olympiad-level math | Hendrycks et al., NeurIPS 2021 |
| `openbookqa` | test split | Elementary science reasoning | Mihaylov et al., EMNLP 2018 |
| `ai2_arc` | `ARC-Challenge` test | Hard science MCQ | Clark et al., 2018 |

**Critical**: run a hash-based collision check between Tier 0 data and the
final training mix. Any leakage invalidates the eval.

---

## Tier 1.5 — Paper-verified AI/ML domain training data (subsets only)

Use small subsets (1–3% of total mix each) to inject capability our KG and
MCQ data don't fully cover. Each entry below is paper-cited; do not pull
unverified clones from random HF orgs.

### 1.5.1 Theorem & STEM reasoning (training subsets)

| Dataset | Sample size | Format | License | Why for tutor |
|---|---|---|---|---|
| `TIGER-Lab/MAmmoTH-V2-Math-Coding-Subset` | 100K total (we sample 800–1500) | Q/A with CoT + program-of-thought | MIT | MathInstruct-style mix used to train MAmmoTH (Yue et al., ICLR 2024) — proven to lift math reasoning without forgetting |
| `nvidia/OpenMathInstruct-2` | 14M (sample 1000–2000) | Q/A with code | NVIDIA Open Model License (commercial OK with attribution) | Nemotron Math paper recipe; code-grounded answers match our `execute_python` flow |
| `microsoft/orca-math-word-problems-200k` | 200K (sample 500) | Q/A | MIT | Orca 2 paper: synthetic but quality-filtered |

**Sampling rule**: stratify by difficulty if available; oversample
multi-step (CoT depth ≥ 3) since 3B base struggles there.

### 1.5.2 ML/AI domain knowledge (training subsets — careful with leakage)

| Dataset | Sample size | Use | License | Why |
|---|---|---|---|---|
| `cais/mmlu` `auxiliary_train` (NOT test/val) | All ~100K, sample 1000 | General STEM grounding | MIT | Hendrycks confirms `auxiliary_train` is held out from MMLU eval splits — safe to train on |
| `allenai/sciq` | 12K train, sample 500 | Science MCQ → tutor explanation format | CC-BY-NC-3.0 (research only — confirm scope) | Welbl et al., "Crowdsourcing Multiple Choice Science Questions", 2017 |
| `tasksource/bigbench` `formal_fallacies`, `logical_deduction` (sample 200 each) | 400 total | Logic patterns useful for ML proofs | Apache-2.0 | BIG-bench paper, Srivastava et al. 2022 |

⚠️ **`sciq` is CC-BY-NC** — only include if the deployment scope is
research/internal. For commercial deployment, replace with synthetic
science questions generated from KG.

### 1.5.3 Conversational alignment (training subsets)

The Zephyr-7B (Tunstall et al., 2023) and Tulu 3 (Lambert et al., 2024)
recipes are reproducible and paper-published — both rely on these:

| Dataset | Sample size | Format | License | Why |
|---|---|---|---|---|
| `HuggingFaceH4/ultrachat_200k` | 200K (sample 1000–1500) | Multi-turn dialogue | MIT | Zephyr SFT base; teaches multi-turn coherence |
| `HuggingFaceH4/ultrafeedback_binarized` | 60K | DPO pairs (chosen/rejected) | MIT | Use only if doing DPO post-SFT (out of v1 scope) |
| `allenai/tulu-3-sft-mixture` | ~939K (sample 1000) | Mixed instruction | ODC-BY-1.0 | Tulu 3 paper recipe; safe general SFT mix |

**Recommended sampling for v1 FAST**: 1000 from `ultrachat_200k` only.
Skip Tulu mixture (overlap with our MCQ-derived samples). Skip
`ultrafeedback` (DPO is v2).

### 1.5.4 Coding (training subsets, Python/PyTorch flavor)

| Dataset | Sample size | Format | License | Why |
|---|---|---|---|---|
| `ise-uiuc/Magicoder-OSS-Instruct-75K` | 75K (sample 500) | Code instruct | MIT | Wei et al., ICML 2024; OSS-Instruct method, high quality |
| `nickrosh/Evol-Instruct-Code-80k-v1` | 80K (sample 500) | Evolving code instruct | Apache-2.0 | WizardCoder lineage; commonly used |
| `HuggingFaceH4/CodeAlpaca_20K` | 20K (sample 300) | Alpaca-format code | CC-BY-NC-4.0 | Research only; light usage |

Filter to Python + PyTorch + NumPy + scikit-learn keyword presence; drop
low-level systems code (C++, Rust) — not relevant for tutor scope.

---

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

## Mixing recipe (suggested for v1 FULL — KG-augmented)

Total target: ~16k–18k training samples (was 10–12k pre-KG).

| Source | Count | Pct |
|---|---|---|
| Organic `qa_history` (after P2 cleaning) | 3000–5000 | 22% |
| **KG-derived synth (Strategy E.1–E.5)** | **4600** | **27%** |
| **Domain MCQ → tutor Q&A (Strategy A)** | **4900** | **28%** |
| `hermes-function-calling-v1` (singleturn + agentic subsets) | 2000 | 12% |
| `xlam-function-calling-60k` (filtered single-tool) | 500 | 3% |
| `Vietnamese-nvidia-OpenMathInstruct-1-50k-gg-translated` | 800 | 5% |
| `MAmmoTH-V2-Math-Coding-Subset` (Tier 1.5) | 500 | 3% |
| `ultrachat_200k` (Tier 1.5, conversational alignment) | 800 | 5% |
| Synthetic refusals (Gemini-generated, tutor voice) | 410 | 2% |
| `Viet-Visual-Instructions` (vision retention) | 300 | 2% |

## Mixing recipe (suggested for v1 FAST — 3-day variant)

Total target: ~10k samples (drop organic + reduce KG to top-importance).

| Source | Count | Pct | `has_tool_call` |
|---|---|---|---|
| **KG-derived synth (E.1 + E.3 only, importance ≥ high)** | **2500** | **25%** | false |
| **Domain MCQ → tutor Q&A (Strategy A, top 3 variants)** | **3000** | **30%** | false |
| **VN MCQ translations (Strategy D)** | **1500** | **15%** | false |
| `hermes-function-calling-v1` (singleturn) | 1500 | 15% | **true** |
| **Strategy F — synthetic tool-call traces (NEW, see 02b-domain-data.md)** | **800** | **8%** | **true** |
| `xlam-function-calling-60k` (filtered single-tool) | 200 | 2% | **true** |
| `Vietnamese-nvidia-OpenMathInstruct-1-50k-gg-translated` | 200 | 2% | false (code_reasoning only) |
| `ultrachat_200k` | 200 | 2% | false |
| Synthetic refusals | 100 | 1% | false |

**`has_tool_call=true` total**: 1500 + 800 + 200 = 2500 / 10000 = **25%** ✅
(meets target; previously 10% claimed but mathematically failed)

**Stratified mix** ensures:
- Tool-call samples ≥ 25% (combined organic + hermes + xlam + math-with-code)
- Vietnamese ≥ 65%
- Vision ≥ 3% (just enough to prevent VL projector drift)
- Refusal ≥ 4%

## License allowlist gate (script-enforced, NOT manual checklist)

Manual license audit fails at scale. Replace with `license_allowlist.json`
+ build-time gate:

`fine-tune-chatbot/data/license_allowlist.json`:
```json
{
  "deployment_scope": "research",
  "scopes": {
    "research": ["MIT", "Apache-2.0", "BSD-3-Clause", "ODC-BY-1.0",
                 "CC-BY-4.0", "CC-BY-3.0", "CC-BY-NC-4.0", "CC-BY-NC-3.0",
                 "NVIDIA Open Model License"],
    "internal": ["MIT", "Apache-2.0", "BSD-3-Clause", "ODC-BY-1.0",
                 "CC-BY-4.0", "CC-BY-3.0", "NVIDIA Open Model License"],
    "commercial": ["MIT", "Apache-2.0", "BSD-3-Clause",
                   "NVIDIA Open Model License (commercial OK)"]
  }
}
```

Each dataset entry in `datasets/registry.json` carries:
```json
{
  "name": "TIGER-Lab/MAmmoTH-V2-Math-Coding-Subset",
  "license": "MIT",
  "license_verified_at": "2026-04-27",
  "license_verified_via": "https://huggingface.co/datasets/TIGER-Lab/MAmmoTH-V2-Math-Coding-Subset",
  "verified_exists": true
}
```

Build script `scripts/sft/0_validate_licenses.py`:
1. Read `DEPLOYMENT_SCOPE` env var (`research|internal|commercial`)
2. For every dataset planned in the mix, look up license
3. **Fail build** if any license not in allowlist for current scope
4. Print summary table (dataset, license, allowed?)

This runs BEFORE any data download/processing. CI in pipeline rejects PR
that adds a non-allowlisted dataset.

## Dataset existence + license runtime verification

Notes in `## Verification snapshot` are not enough. Add a script that
re-verifies at install time:

`scripts/sft/0_verify_datasets_exist.py`:
1. For each dataset in the registry, attempt `datasets.load_dataset(repo,
   subset, split=..., streaming=True)` and pull 1 example
2. Confirm dataset still exists, license metadata still matches registry
3. If repo moved/renamed/license changed: fail with actionable message,
   require registry update before proceeding

## Dataset selection checklist (before training)

- [ ] **License gate script `0_validate_licenses.py` passes** for current
      `DEPLOYMENT_SCOPE`
- [ ] **Existence verify script `0_verify_datasets_exist.py` passes**
- [ ] PII check: spot-check 20 random samples per dataset for names/IDs/addresses
- [ ] Language audit: confirm VN ratio ≥ 60% in final mix
- [ ] Format consistency: all samples converted to Qwen2.5 ChatML
- [ ] Tool-call format match: matches the format committed in P0.5
      `smoke_results.json` (Hermes XML, Qwen native, OR structured field —
      one of three, not all)
- [ ] **`has_tool_call=true` ratio ≥ 25%** (NOT `code_reasoning=true`; see
      `02b-domain-data.md` § "Tool-call vs code-reasoning metric")
- [ ] Tokenizer length stats: p95 < 4096 (matches `max_seq_length`)
- [ ] No data leakage: held-out test set has zero overlap with training mix
      (group-key split + cross-split MinHash 0.85 reports zero matches)
- [ ] Manifest: each sample tagged with `_meta.source`, `_meta.has_tool_call`,
      `_meta.code_reasoning`, `_meta.grounding_level`,
      `_meta.external_api_used` for ablation analysis

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
