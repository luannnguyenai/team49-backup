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
| **Knowledge Graph (canonical KPs)** | `data/final_artifacts/cs224n_cs231n_cs230_v1/p2_output_manual_append.json` | ~1.4MB structured KPs | EN metadata |
| **KP edge labels (prereq, related)** | `data/final_artifacts/cs224n_cs231n_cs230_v1/gpt54_edge_labels.json` | ~532K edges | — |
| **Pruned transitive edge graph** | `data/final_artifacts/cs224n_cs231n_cs230_v1/p5_output_transitive_pruned.json` | ~224K | — |

**Total MCQs available: ~1634 with full metadata** (rationale, evidence
quotes, timestamps, KP IDs, distractor explanations, difficulty).

**Knowledge Graph asset (NEW source for v1)**: each KP carries `name`,
`description`, `difficulty_level` (0–1 float), `importance_level`
(critical/high/medium/low), `domain_tags`, `career_path_tags`,
`structural_role` (gateway/foundation/application/etc.), `source_course_ids`,
and `merged_from_local_ids`. Edges encode prereq / related-to / part-of
relationships across CS224n/CS230/CS231n. This dwarfs the MCQ count for
*generative* synthesis purposes — see Strategy E below.

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

### Strategy E — Knowledge-Graph-driven synthetic Q&A (Gemini Flash, $8–15)

The KG in `data/final_artifacts/cs224n_cs231n_cs230_v1/` contains
canonicalized knowledge points (KPs) with rich metadata and prereq/related
edges. This is the highest-structure data source we have — Q&A generated
from it is **graph-grounded** rather than free-form, which means each
sample carries explicit metadata (difficulty, importance, source course,
prereq chain) that can be used for stratified mixing and ablation.

Generate 5 KP-grounded Q&A flavors:

#### E.1 Definition Q&A (deterministic, free)

For each KP with `difficulty_level` and `description`:

```json
{"messages": [
  {"role": "user", "content": "Trong {source_course_ids[0]}, {kp.name} là gì?"},
  {"role": "assistant", "content": "{kp.description}\n\nĐây là khái niệm {importance_level} ở mức độ khó {difficulty_level:.0%}, thuộc {domain_tags joined}. {if structural_role == 'gateway': 'Nhiều khái niệm sau dựa trên ý này.'}"}
]}
```

No LLM call needed. **Yield**: ~1 sample per KP × ~1500 KPs = ~1500 samples
(filter KPs with description < 50 chars).

#### E.2 Prerequisite-aware Q&A (deterministic + Gemini polish)

For each edge `(src) --prereq--> (dst)`:

```
Q (vi): "Trước khi học {dst.name} em cần nắm những gì?"
A: enumerate all incoming prereq edges of dst, deepest-first via topological order,
   include short {kp.name} + 1-line description for each prereq.
```

Use Gemini Flash only to **polish phrasing** (not to invent content):
template-fill the answer, ask Gemini to rewrite in tutor voice. Keeps
factual content graph-grounded; prevents hallucination. **Yield**: ~600
prereq-chain samples × 2 langs = ~1200 samples.

#### E.3 Difficulty-stratified deep-dive (Gemini Flash)

Group KPs by `difficulty_level` band:
- **Easy band (≤ 0.4)**: generate "Em đang bắt đầu — giải thích {kp.name} cho người mới"
- **Mid band (0.4–0.7)**: generate "Giải thích {kp.name} kèm ví dụ thực tế"
- **Hard band (> 0.7)**: generate "Trình bày {kp.name} ở mức nâng cao, kèm derivation/proof nếu có"

For each KP, produce one sample at the matching depth. The hard band
explicitly trains the model to derive — a capability current API output
in `qa_history` may not have signal for. **Yield**: ~1500 samples × 60% VN
selection = ~900 VN + 600 EN.

#### E.4 Cross-course linking (Gemini Flash, free for KPs with `len(source_course_ids) ≥ 2`)

When the same canonical KP appears in ≥ 2 courses (e.g., backprop in CS230
and CS224n), generate a comparison sample: how does each course frame this
concept? Different angles, different formalism, common ground. This is
unique training signal — the API baseline does not see cross-course KP
canonicalization. **Yield**: estimated ~150–300 samples depending on
overlap rate.

#### E.5 Misconception → correction (deterministic from edges + Gemini)

For each KP that has a `related-but-distinct` edge (graph signal that two
concepts are commonly confused — e.g., "self-supervised" vs "weakly
supervised"), generate:

```
Q: "Em nghĩ {kp_a.name} và {kp_b.name} là một phải không?"
A: short explanation of the distinction, citing both KP descriptions.
```

This is a powerful trainer for the tutor's "polite correction" voice and
tests boundary knowledge. **Yield**: ~200 samples assuming 100 such pairs
× 2 langs.

#### Cost summary for Strategy E

| Sub-strategy | Samples | Gemini Flash cost |
|---|---|---|
| E.1 Definition | 1500 | $0 (deterministic) |
| E.2 Prereq chain | 1200 | $3–5 (polish only) |
| E.3 Difficulty deep-dive | 1500 | $5–8 |
| E.4 Cross-course | 200 | $1 |
| E.5 Misconception | 200 | $1 |
| **Total** | **~4600** | **~$10–15** |

#### Why this matters more than Strategy A/B for v1

- **Higher generative leverage**: 1 KG → 4600 samples vs MCQ → 4900 (similar
  count, but KG samples carry explicit prereq/difficulty/cross-course
  signal absent in MCQ-derived samples)
- **Built-in stratification**: every sample tagged with `kp_id`,
  `difficulty_level`, `importance_level` → free metadata for ablation and
  curriculum-style training (`logging_steps` can break out loss by
  difficulty band)
- **Graph consistency**: prereq chains in answers come from the actual
  graph, not LLM imagination → reduces hallucination training signal
- **Cross-course samples are unique**: cannot be obtained from per-course
  MCQ data; only KG canonicalization produces these

### Conversion script additions

Add to the script list:
```
fine-tune-chatbot/scripts/sft/domain/
├── ... (existing 10–30 scripts)
├── 14_load_knowledge_graph.py       # parse p2_output + edge_labels + p5_pruned → KP+edge tables
├── 24_kg_definition_qa.py           # Strategy E.1 (deterministic)
├── 25_kg_prereq_qa.py               # Strategy E.2 (template + Gemini polish)
├── 26_kg_difficulty_deepdive.py     # Strategy E.3 (Gemini)
├── 27_kg_cross_course.py            # Strategy E.4 (Gemini)
├── 28_kg_misconception.py           # Strategy E.5 (deterministic + Gemini)
└── 30_merge_domain.py               # combine all → domain.jsonl  (update to include KG sources)
```

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

## Updated mixing recipe (v1 final, KG-augmented)

| Source | Count | Pct | Origin |
|---|---|---|---|
| Organic `qa_history` (post-clean) | 3000–5000 | 18–25% | DB + JSONL |
| **Domain MCQ → tutor Q&A (Strategy A)** | **4900** | **27%** | course_assets (free) |
| **Knowledge-Graph synth (Strategy E.1–E.5)** | **4600** | **25%** | KG + Gemini Flash |
| **Transcript-grounded synth (Strategy B)** | **800** | **4%** | Gemini Flash |
| **VN MCQ translations (Strategy D)** | **2100** | **12%** | Gemini Flash |
| **Synthetic refusals (Strategy C)** | **410** | **2%** | Gemini Flash |
| Hermes function-calling | 2000 | 11% | NousResearch |
| xLAM filtered single-tool | 500 | 3% | Salesforce |
| Viet-Visual-Instructions retain | 300 | 2% | 5CD-AI |
| **TOTAL** | **~18000** | **100%** | — |

For **FAST 3-day variant**: drop organic `qa_history` extraction entirely
(P2a still runs as audit but does not feed FAST training); cap total at
~10–12k by reducing Strategy E to top-importance KPs only (filter
`importance_level in {critical, high}`) and skipping E.4/E.5 cross-course +
misconception sub-strategies. Yields ~10k samples deliverable in Day 1.

**VN ratio**: 310 + 2100 + KG_E_VN_share (~50% of 4600 = 2300) + organic
est. 60% + 200 + 200 ≈ 70%+ ✅
**Tool-call samples**: 2000 + 500 + (organic est. 30%) ≈ 25–30% ✅
**Domain alignment**: 70%+ from course assets + KG directly ✅
**Hallucination resistance**: KG-grounded samples (~25%) carry verifiable
graph paths — model trained on these is less likely to invent prereqs

## Cost estimate

| Item | Cost |
|---|---|
| Strategy B (800 samples × ~2K input + 500 output) | ~$3–5 |
| Strategy C (410 samples) | ~$2 |
| Strategy D (700 translations) | ~$3–5 |
| **Total Gemini Flash budget** | **~$8–12** |

Trivial vs. external dataset download bandwidth and licensing complexity.

## Data governance compliance

Per-source policy table (replaces ad-hoc rules; enforced by manifest gate):

| Data class | External API allowed? | Rationale | Manifest tag |
|---|---|---|---|
| `student_qa` (`qa_history` rows) | ❌ NEVER | Private user content, may contain PII even after scrub | `external_api_used=false` (mandatory) |
| `db_exports` (lectures, chapters, transcript_lines tables) | ❌ NEVER | Internal schema may leak structure | `external_api_used=false` |
| `public_course_transcripts` (Stanford CS224n/CS230/CS231n) | ✅ Allowed (Gemini Flash) | Publicly available courseware; no derivative restriction | `external_api_used=true, source=synthetic_gemini-flash` |
| `public_MCQ_assets` (`question_bank.json`, P3c, P4) | ✅ Allowed if license permits derivative | Verify license per file before use | `external_api_used=true, source=synthetic_gemini-flash` |
| `KG artifacts` (`final_artifacts/...`) | ✅ Allowed for polish-only use | Already derived from public courseware | `external_api_used=true, source=kg_synthetic` |
| `model weights trained on course data` | ❌ Not redistributed externally | Copyright + commercial scope unclear | — |

The data pipeline manifest (`data/sft/manifest.json`) MUST carry
`external_api_used: bool` per source row. Build script fails if any
`student_qa` source has `external_api_used=true`.

- ✅ All output samples carry `_meta.source` and `_meta.external_api_used` for
  ablation/audit
- ✅ Manifest gate enforced in `scripts/sft/30_merge_domain.py` (raises if
  governance violated)

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

## Group-key split (mandatory — prevents eval leakage)

⚠️ **Random sample-level split causes silent train/test leakage** when
multiple variants are derived from the same source entity. Strategy A
emits 3 variants per MCQ; Strategy E emits up to 5 flavors per KP.
Random split puts variants of the same MCQ/KP in both train and test.

**Rule**: split BY group key BEFORE expanding variants:

| Source | Group key |
|---|---|
| MCQ (Strategy A, D) | `item_id` (from `question_bank.json` / P4 / P3c) |
| KG (Strategy E.1–E.5) | `global_kp_id` |
| Transcript (Strategy B) | `(lecture_id, time_window_start_s)` |
| Refusal (Strategy C) | `(lecture_id, refusal_seed_id)` |
| Cross-course (Strategy E.4) | tuple of `global_kp_id` × source pair |
| Organic `qa_history` | normalized `question_hash` (after PII scrub) |

Pipeline:

1. Collect all source entities into a `groups.jsonl` with `(group_id,
   source_type)`.
2. Stratified split groups → train/val/test (e.g., 90/5/5 by group count,
   stratified by `source_type` and `difficulty_level` band).
3. Hold-out eval fixtures (P4 `eval/fixtures/*.jsonl`) MUST come from groups
   in the test split — never from train groups.
4. Only AFTER splitting groups, expand each group's variants into
   training samples.
5. Final dedup: MinHash 0.85 within each split (catches accidental
   near-duplicate phrasings); cross-split MinHash MUST find zero matches.

Output: `data/sft/groups_split.json`:
```json
{
  "train_groups": ["mcq_001", "kp_3d_cnn", ...],
  "val_groups":   [...],
  "test_groups":  [...],
  "checksum": "sha256:..."
}
```

`scripts/sft/07_split.py` consumes this JSON and refuses to assign a
sample to a split if its group is not in the corresponding list. Build
fails on group-leak.

## Tool-call vs code-reasoning metric (clarification)

Two distinct flags MUST be tracked separately in `_meta`:

- `_meta.has_tool_call: bool` — assistant message has structured `tool_calls`
  field (the format Hermes parser is supposed to emit). Counts toward the
  "≥ 25% tool-call samples" target.
- `_meta.code_reasoning: bool` — answer contains code blocks in plain text
  (e.g., MathInstruct PoT samples) but no `tool_calls` field. Does NOT count
  toward tool-call target.

Why this matters: training on `code_reasoning=true` teaches the model to
write code in chat answers, NOT to invoke the sandbox tool. These are
different behaviors. Conflating them inflates apparent tool-call coverage
in the mix and produces a model that explains code instead of calling
`execute_python` when needed.

**Updated tool-call ratio target**: `has_tool_call=true` ≥ 25% of total
training samples. To hit this with FULL mix ~18k:
- Hermes singleturn + agentic: 2000
- xLAM filtered: 1000 (was 500)
- **NEW Strategy F — synthetic tool-call traces from KG/MCQ math+code seeds**:
  ~1500 (see below)
- Organic with sandbox marker: ~900 (kept conservative)
- **Total has_tool_call ≈ 5400 / 18000 = 30%** ✅

For FAST mix ~10k, target is ~2500 `has_tool_call=true`:
- Hermes singleturn: 1500 (was 1000)
- Strategy F synthetic: 800
- xLAM filtered: 200
- **Total ≈ 2500 / 10000 = 25%** ✅

### Strategy F — synthetic tool-call traces (NEW)

For each KP/MCQ where the answer naturally requires computation (math,
algorithm steps, statistics), generate a multi-turn ChatML sample:

```json
{"messages": [
  {"role": "user", "content": "Question requiring computation..."},
  {"role": "assistant", "content": null,
   "tool_calls": [{"id": "call_1", "type": "function",
                   "function": {"name": "execute_python",
                                "arguments": "{\"code\": \"...\"}"}}]},
  {"role": "tool", "tool_call_id": "call_1", "content": "<simulated stdout>"},
  {"role": "assistant", "content": "<final answer using tool result>"}
]}
```

Generate using template + Gemini Flash to author code body and final
answer; sandbox-execute the code locally to fill `<simulated stdout>`
with real output. Yield ~1500 samples for ~$5–8.

**P0.5 format gate applies**: at least 50 of these 1500 must round-trip
through vLLM with `--tool-call-parser hermes` and produce parseable
`tool_calls` in the API response. If <50 round-trip: stop; format
converter is wrong.

## KG sample grounding metadata (mandatory)

Each Strategy E sample MUST carry:

```json
"_meta": {
  "source": "kg_e1_definition" | "kg_e2_prereq" | ...,
  "grounding_level": "kg_only" | "kg_plus_transcript" | "mcq_evidence" | "teacher_synthetic",
  "kp_id": "kp_3d_cnn_and_slow_fusion",
  "difficulty_level": 0.7,
  "importance_level": "critical",
  "source_course_ids": ["CS231n"],
  "external_api_used": false | true,
  "has_tool_call": false,
  "code_reasoning": false
}
```

`grounding_level` semantics:
- `kg_only`: answer derived purely from KP description / edges (Strategy
  E.1 default)
- `kg_plus_transcript`: enriched with transcript window evidence
  (Strategy E.3 with transcript injection)
- `mcq_evidence`: backed by MCQ.evidence.transcript_quotes + timestamps
- `teacher_synthetic`: free-form Gemini answer, no graph/transcript
  grounding (riskiest; minimize)

**Citation training rule**: P4 eval Gate 1 "citation HH:MM:SS format ≥ 95%"
applies only to samples with `grounding_level in {kg_plus_transcript,
mcq_evidence}`. Training the citation behavior on `kg_only` samples
produces a model that fabricates timestamps. Filter accordingly when
sampling for the citation-required training subset.

Strategy E.3 prompt (Gemini Flash) MUST include the constraint:
> "If the provided KP description and prereq context do not contain
> enough information to derive the requested explanation, respond with
> the description verbatim and add 'Cần xem lại lecture <X> để hiểu sâu
> hơn'. Do NOT invent derivations or proofs not present in the input."

## Exit criteria for P2b

- [ ] All 4 conversion strategies executed
- [ ] `data/sft/domain.jsonl` ≥ 8000 samples
- [ ] Manifest tracks per-source counts and language distribution
- [ ] Spot-check 100 random samples: ≤ 5% rejection rate
- [ ] Citation timestamps are valid HH:MM:SS in 100% of samples that should have them
- [ ] No MCQ leakage between training and `data/sft/test.jsonl` (held-out)
