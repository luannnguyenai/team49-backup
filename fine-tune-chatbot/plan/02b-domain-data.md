# P2b — Domain Data from Course Assets (CS224n + CS231n)

**Goal**: convert existing course assets in `data/courses/` and
`data/bootstrap/question_bank.json` into tutor-style SFT examples.

This is the **primary domain data source**, prioritized above external
public datasets because it matches the production tutor's actual content.

## Inventory (audited 2026-04-25)

| Asset | Path | Count | Language |
|---|---|---|---|
| Bootstrap question bank | `data/bootstrap/question_bank.json` | 549 MCQs | 310 VN + 239 EN |
| P4 quality-gated MCQs | `data/courses/*/processed/P4/L*/*.json` | 985 MCQs | EN |
| P3c knowledge-point MCQs | `data/courses/*/processed/P3c/L*/*.json` | ~100 MCQs | EN |
| Lecture transcripts | `data/courses/*/transcripts/*.txt` | 41 files | EN, timestamped |
| ToC summaries | `data/courses/*/ToC_Summary/*.json` | 44 files | EN, sectioned |
| Segmented units (P1) | `data/courses/*/processed/P1/*.json` | 41 files | EN |
| Slide PDFs | `data/courses/*/slides/*.pdf` | 28 PDFs | EN, visual |

**Total MCQs available: ~1634 with full metadata** (rationale, evidence
quotes, timestamps, KP IDs, distractor explanations, difficulty).

## Why this beats external datasets for v1

1. **Domain alignment**: trained model sees the exact CS224n/CS231n content
   it will be asked about in production.
2. **Citation training**: each MCQ carries `evidence.timestamps` + `evidence.transcript_quotes`
   — perfect ground truth to train HH:MM:SS citation behavior.
3. **Refusal/scope grounding**: questions are guaranteed in-scope; we can
   pair with synthetic out-of-scope versions for refusal training.
4. **Distractor rationale**: each wrong answer has `distractor_*_rationale`
   — gold for training "why is this wrong" Bloom-level reasoning.
5. **Bilingual native**: 310 VN MCQs already exist; the rest can be
   translated cheaply (~$5–10 via Gemini Flash).

## Conversion strategy

### Strategy A — MCQ → Tutor Q&A (deterministic, free)

For each MCQ, generate **3 tutor-style training samples**:

#### A.1 Concept question (use stem as student question)

```json
{
  "messages": [
    {"role": "system", "content": "<verbatim tutor system prompt>"},
    {"role": "user", "content": "[INPUT]\n<TOC + transcript window built from evidence.timestamps>\n\nCurrent Time Window (00:13:40):\n<transcript ±300s around timestamp>\n\nCurrent Chapter: <section_title from ToC>\n\nStudent Question: \"<MCQ.stem_text>\""},
    {"role": "assistant", "content": "<MCQ.explanation_text>\n\n<thêm reference timestamp HH:MM:SS từ evidence>"}
  ]
}
```

#### A.2 Distractor confusion (student picks wrong, tutor explains why)

```json
{
  "messages": [
    {"role": "user", "content": "Em nghĩ <distractor_a_text>, đúng không thầy?"},
    {"role": "assistant", "content": "Không hẳn em ạ. <distractor_a_rationale>\n\nĐáp án đúng là: <correct_answer_text>. <explanation>"}
  ]
}
```

This is **uniquely valuable** — most public datasets don't teach the model
how to correct misconceptions politely.

#### A.3 Open-ended explanation (paraphrase MCQ stem as free-form question)

```json
{
  "messages": [
    {"role": "user", "content": "Thầy giải thích cho em về <topic_slug từ MCQ>"},
    {"role": "assistant", "content": "<expanded explanation built from MCQ.explanation_text + key_takeaways từ ToC section>"}
  ]
}
```

**Yield**: 1634 MCQs × 3 variants = **~4900 training samples** without any
LLM API calls.

### Strategy B — Transcript-grounded synthetic Q&A (Gemini Flash, $5–10)

For lectures without sufficient MCQ coverage, sample 10 transcript windows
per lecture and ask Gemini Flash:

```
You are generating training data for a tutor model.
Given this lecture transcript window from CS224n Lecture <N>, section "<section_title>":

<transcript window>

Generate ONE student question a learner might ask, and ONE tutor-style answer
in <vi/en>, citing timestamps in HH:MM:SS format. The answer must reference
ONLY the provided transcript content. Output JSON: {"q": "...", "a": "..."}.
```

**Yield**: 41 lectures × 10 windows × 2 langs = ~800 samples for ~$5–8.

### Strategy C — Synthetic refusal pairs (Gemini Flash, $2–5)

For each lecture, generate 5 off-topic questions a real student might ask
(e.g., asking about week 3 content during week 1, asking about Python
syntax during a theory lecture, asking off-topic personal questions).
Then generate the tutor's polite redirect using the exact tutor system prompt.

**Yield**: 41 × 5 × 2 langs = ~410 refusal samples.

### Strategy D — VN translation of EN MCQs (Gemini Flash, $5–10)

Translate the 985 P4 EN MCQs (and ~100 P3c) to Vietnamese to balance the
VN ratio. Use the existing tutor's voice (formal "em/thầy" tutor style).

Skip translation for MCQs with heavy code blocks or formulas.

**Yield**: ~700 additional VN MCQs → 700 × 3 variants = +2100 VN samples.

## Conversion scripts

```
fine-tune-chatbot/scripts/sft/domain/
├── 10_load_qbank.py              # bootstrap/question_bank.json → unified MCQ
├── 11_load_p4_mcqs.py            # P4 → unified MCQ
├── 12_load_p3c_mcqs.py           # P3c → unified MCQ
├── 13_load_transcripts.py        # transcripts + ToC + P1 → context blocks
├── 20_mcq_to_tutor_qa.py         # MCQ → 3 tutor-style ChatML samples (Strategy A)
├── 21_synth_transcript_qa.py     # Strategy B (calls Gemini)
├── 22_synth_refusals.py          # Strategy C (calls Gemini)
├── 23_translate_mcqs.py          # Strategy D (calls Gemini)
└── 30_merge_domain.py            # combine all → domain.jsonl
```

## Updated mixing recipe (v1 final)

| Source | Count | Pct | Origin |
|---|---|---|---|
| Organic `qa_history` (post-clean) | 3000–5000 | 25–35% | DB + JSONL |
| **Domain MCQ → tutor Q&A (Strategy A)** | **4900** | **35%** | course_assets (free) |
| **Transcript-grounded synth (Strategy B)** | **800** | **6%** | Gemini Flash |
| **VN MCQ translations (Strategy D)** | **2100** | **15%** | Gemini Flash |
| **Synthetic refusals (Strategy C)** | **410** | **3%** | Gemini Flash |
| Hermes function-calling | 2000 | 14% | NousResearch |
| xLAM filtered single-tool | 500 | 4% | Salesforce |
| Viet-Visual-Instructions retain | 300 | 2% | 5CD-AI |
| **TOTAL** | **~14000** | **100%** | — |

**VN ratio**: 310 + 2100 + (organic est. 60%) + 200 + 200 ≈ 65–70% ✅
**Tool-call samples**: 2000 + 500 + (organic est. 30%) ≈ 30% ✅
**Domain alignment**: 60% from course assets directly ✅

## Cost estimate

| Item | Cost |
|---|---|
| Strategy B (800 samples × ~2K input + 500 output) | ~$3–5 |
| Strategy C (410 samples) | ~$2 |
| Strategy D (700 translations) | ~$3–5 |
| **Total Gemini Flash budget** | **~$8–12** |

Trivial vs. external dataset download bandwidth and licensing complexity.

## Data governance compliance

- ✅ All course data is local; no upload to external services for training data prep
- ⚠️ Strategy B/C/D send transcripts/MCQs to **Gemini Flash API** — this is
  Google's API, transcripts are public Stanford courseware, so OK. But
  document this in the manifest as `source: synthetic_gemini-flash`
- ✅ No `qa_history` data goes to external API in this pipeline
- ✅ All output samples carry `_meta.source` for ablation/audit

## Schema mapping reference

### Bootstrap question_bank.json
```python
{
  "item_id", "topic_slug", "module_slug", "bloom_level", "difficulty_bucket",
  "stem_text", "option_a/b/c/d", "correct_answer",
  "distractor_a/c/d_rationale",  # NB: no "b" rationale (b is correct in many)
  "explanation_text", "kc_slugs", "time_expected_seconds"
}
```

### P4 repaired_question_bank
```python
{
  "item_id", "item_type", "knowledge_scope", "type",
  "question", "choices", "answer_index", "explanation",
  "primary_kp_id", "difficulty",
  "code_block": {"language", "snippet", "highlight_lines"},
  "evidence": {"source", "transcript_quotes", "timestamps"}
}
```

### P1 lecture structure
```python
{
  "lecture_title",
  "table_of_contents": [{"section_index", "title", "start_s", "end_s"}],
  "units": [{"unit_id", ...}]
}
```

### Transcript .txt format
```
Title: <youtube title>
URL: <youtube url>
Video ID: <id>
============================================================

HH:MM:SS
<text line>

HH:MM:SS
<text line>
...
```

## Exit criteria for P2b

- [ ] All 4 conversion strategies executed
- [ ] `data/sft/domain.jsonl` ≥ 8000 samples
- [ ] Manifest tracks per-source counts and language distribution
- [ ] Spot-check 100 random samples: ≤ 5% rejection rate
- [ ] Citation timestamps are valid HH:MM:SS in 100% of samples that should have them
- [ ] No MCQ leakage between training and `data/sft/test.jsonl` (held-out)
