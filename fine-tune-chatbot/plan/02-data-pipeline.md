# P2 — Data Pipeline

**Goal**: produce `data/sft/{train,val,test}.jsonl` in Qwen2.5-VL ChatML
format with text + vision + tool-call samples.

**Duration**: 1–3 days depending on whether image recovery is needed.

## ⚠️ BLOCKER: Image data is truncated

`src/services/llm_service.py:110`:
```python
image_base64=image_base64[:500] if image_base64 else None,
```

**Only the first 500 chars of base64 are stored** in `qa_history.image_base64`.
That's not a valid image. We cannot reconstruct vision training data from
existing `qa_history` rows.

### Three options to unblock

**Option A — Fix logging now, collect for 2 weeks**
- Patch `_save_qa_history` to write full image to object storage (S3/MinIO)
  and keep only an URL/key in DB.
- Wait 2 weeks of organic traffic.
- Pro: real user data, distribution matches production.
- Con: 2-week delay.

**Option B — Synthetic image data (recommended for v1)**
- Sample random frames from existing lecture videos (`data/` or course assets).
- For each frame, ask Gemini Pro VLM (or Claude) to:
  - Describe the slide
  - Generate 3 plausible student questions
  - Generate the answer in tutor style (using surrounding transcript)
- Yields ~2k–5k vision samples in 1 day at API cost ~$30–80.
- Pro: fast, distribution-controlled.
- Con: synthetic bias, distill from teacher model.

**Option C — Skip vision in training, use base VL capabilities**
- Train LoRA on **text adapters only** (`finetune_vision_layers=False`).
- Vision encoder + projector stay frozen at Qwen2.5-VL pretrain quality.
- Pro: simplest, smallest VRAM, fastest train.
- Con: vision answers won't match tutor style; image-grounded reasoning unchanged.

→ **Decision for v1**: **Option C + small Option B supplement** (200–500
synthetic vision samples just to keep model from forgetting vision during
LoRA on text). Text adapters frozen on vision tower.

If results are weak in vision eval, escalate to full Option B in v2.

## Data sources

| Source | Path | Volume estimate | Use for |
|---|---|---|---|
| QA history JSONL | `logs/qa_history.jsonl` | grow daily | Primary text SFT |
| QA history DB | `qa_history` table | same | Cross-check, get `route`, `tool_used` |
| Tutor system prompt | `src/services/llm_service.py` lines 324–348 | 1 | Verbatim system message |
| Lecture transcripts | `transcript_lines` table | many | Context blocks for samples |
| Sandbox traces | `qa_history.thoughts` containing `[SANDBOX]` | subset | Tool-call training |
| Lecture frames | extract from videos in `data/` | synthetic | Vision (Option B) |

## Pipeline structure

```
fine-tune-chatbot/scripts/sft/
├── 01_extract_from_jsonl.py    # logs/qa_history.jsonl → raw.jsonl
├── 02_extract_from_db.py       # join qa_history + lectures + chapters → raw_db.jsonl
├── 03_dedupe_clean.py          # MinHash dedupe, length filters, PII scrub
├── 04_format_chatml.py         # → Qwen2.5-VL ChatML
├── 05_build_tool_samples.py    # synthesize tool-call traces from sandbox logs
├── 06_synth_vision.py          # (optional, Option B) Gemini-distilled vision pairs
├── 07_split.py                 # 90/5/5 train/val/test stratified by route
└── stats.py                    # report distribution: routes, langs, lengths
```

## Step 01 — Extract from JSONL

`logs/qa_history.jsonl` schema (from `src/services/llm_service.py:208`):
```json
{"time":"...", "lecture":"...", "at_seconds":..., "at_formatted":"...",
 "question":"...", "route":"SIMPLE|COMPLEX|BLOCKED",
 "tool_used":true|false, "answer":"..."}
```

Filter rules:
- Drop rows where `answer` length < 20 chars (likely error)
- Drop rows where `question` < 5 chars
- Drop rows where `answer` contains `"e":"...error..."` markers
- Keep all routes (SIMPLE / COMPLEX / BLOCKED) — we want the model to learn refusals too

Output: `data/sft/raw_text.jsonl`.

## Step 02 — Enrich from DB

For each kept QA, join with `lectures`, `chapters`, `transcript_lines` to
rebuild the **exact same context block** the original LLM saw. This is
critical: training on truncated context teaches the model to hallucinate.

For each sample, fetch:
- Lecture title + scope keywords
- All chapters (TOC)
- Transcript window: `start_window = max(0, current_timestamp - 300)` to
  `current_timestamp + 300` (matches `_fetch_transcript_window`)
- Last 5 QA history items before this one (matches `_fetch_lecture_context`)

Output: `data/sft/raw_enriched.jsonl` with full reproducible inputs.

## Step 03 — Clean and dedupe

- **PII scrub**: regex student names, emails, phone numbers, IDs in `question`
- **Profanity / off-topic filter**: drop questions with high toxicity score
  (use `detoxify` lib or simple keyword list)
- **Dedupe**: MinHash with threshold 0.85 on `(question, answer)` pairs
- **Length cap**: trim `answer` > 4000 chars (rare, usually hallucinations)
- **Language detection**: tag `lang` field (`vi`/`en`/other) for stratified split

Manual spot-check: dump 100 random samples to `data/sft/spot_check_100.jsonl`
and review by hand. Reject batch if >10% have wrong/lazy answers from base
model. Iterate filters until quality bar met.

## Step 04 — Format ChatML

Qwen2.5-VL chat template (text-only sample):

```json
{"messages": [
  {"role": "system", "content": "<verbatim from llm_service.py system_instruction>"},
  {"role": "user", "content": "[INPUT]\nLecture Content:\n<scope>\n<TOC>\n\nCurrent Time Window (HH:MM:SS):\n<transcript>\n\nCurrent Chapter: <name>\n\nStudent Question: \"<q>\""},
  {"role": "assistant", "content": "<answer markdown with HH:MM:SS refs>"}
]}
```

Vision sample (when image present):
```json
{"messages": [
  {"role": "system", "content": "..."},
  {"role": "user", "content": [
    {"type": "image", "image": "file:///path/to/frame.jpg"},
    {"type": "text", "text": "[INPUT]\n..."}
  ]},
  {"role": "assistant", "content": "..."}
]}
```

Tool-call sample (route=COMPLEX with sandbox):
```json
{"messages": [
  {"role": "system", "content": "..."},
  {"role": "user", "content": "..."},
  {"role": "assistant", "content": null,
   "tool_calls": [{"id": "call_1", "type": "function",
                   "function": {"name": "execute_python",
                                "arguments": "{\"code\": \"...\"}"}}]},
  {"role": "tool", "tool_call_id": "call_1", "content": "===== EXECUTED CODE =====\n..."},
  {"role": "assistant", "content": "<final answer using tool result>"}
]}
```

## Step 05 — Tool-call samples

3B-VL has weaker tool-calling than 7B. Need oversampling:

- Extract all rows where `thoughts` starts with `[COMPLEX] [SANDBOX]\n` and
  parse the embedded code + result
- Reconstruct full multi-turn ChatML
- Synthesize additional tool-call examples for common cases:
  - Numerical computation ("tính diện tích...", "giải phương trình...")
  - Symbolic math via sympy
  - Data analysis on small csvs
- **Target distribution**: 30–35% of training samples include `tool_calls`

Source candidates:
- Math/physics/CS lectures with formulas in transcript → auto-generate Q+A+code

## Step 06 — Vision samples (Option B, optional)

Only if Option C results fail vision eval. Skip for v1.

Pipeline:
1. Sample 500 lecture frames (`ffmpeg -ss <t> -i video.mp4 -frames:v 1 frame.jpg`)
2. For each frame, ask Gemini 2.0 Flash:
   ```
   Given this lecture slide screenshot, generate one student question
   and a tutor-style answer in Vietnamese, referencing visual elements.
   ```
3. Filter by length and language consistency
4. Format as vision ChatML

Estimated cost: 500 × ~2K input tokens + ~500 output = ~$10–20 with Flash.

## Step 07 — Split

Stratified by `(route, has_image, has_tool_call, lang)`:

| Split | Ratio | Size target |
|---|---|---|
| train | 90% | 8k–14k |
| val | 5% | 500 |
| test | 5% | 500 |

Test set is **held out forever** — only used for final eval and never for
hyperparameter selection.

## Volume target for v1

| Category | Target count |
|---|---|
| SIMPLE (short factual) | 2k |
| COMPLEX text-only | 5k |
| COMPLEX + tool call | 3k |
| BLOCKED (off-topic refusal) | 500 |
| Vision (Option C minimal) | 200–500 |
| **Total** | **~10k–11k** |

If `qa_history` has <5k usable rows after filters, generate synthetic
supplement using Gemini Pro on real lecture transcripts.

## Output schema

`data/sft/train.jsonl` — one ChatML object per line, ready for Unsloth.
`data/sft/manifest.json` — counts, splits, hashes, generation timestamp.
`data/sft/stats.html` — distribution plots for review.

## Exit criteria

- [ ] ≥ 8k training samples
- [ ] Tool-call samples ≥ 25% of training set
- [ ] Spot-check 200 samples by hand: <5% rejection rate
- [ ] Train/val/test splits have matching distributions on `route` and `lang`
- [ ] Manifest committed (without raw data — gitignore `data/sft/*.jsonl`)
