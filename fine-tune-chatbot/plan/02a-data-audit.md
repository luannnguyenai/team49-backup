# P2a — Data Audit (run BEFORE P2)

**Goal**: verify the assumptions in `02-data-pipeline.md` against real schema
and row counts before writing extraction code. Decide whether organic data is
sufficient or whether synthetic generation becomes mandatory.

**Duration**: 0.5 day.

## Why this phase exists

`02-data-pipeline.md` assumes:
- `logs/qa_history.jsonl` has thousands of usable rows
- `qa_history.thoughts` field starts with `[SANDBOX]` for tool-using rows
- DB joins `qa_history × lectures × chapters × transcript_lines` work
- Vietnamese rows dominate
- `image_base64` column exists (even if truncated)

**If any assumption is wrong, P2 fails silently.** Audit first.

## Audit script

`fine-tune-chatbot/scripts/sft/00_audit.py`:

```python
"""
Data audit: produce real counts before P2 extraction.
Run from repo root with backend env loaded.
"""
import json, os, sys
from collections import Counter
from pathlib import Path

# 1. JSONL log audit
JSONL = Path("logs/qa_history.jsonl")
total = 0
by_route = Counter()
by_lang = Counter()
with_tool = 0
length_buckets = Counter()
short_answer = 0
empty_question = 0
distinct_lectures = set()

if JSONL.exists():
    for line in JSONL.open(encoding="utf-8"):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        total += 1
        by_route[r.get("route", "UNKNOWN")] += 1
        if r.get("tool_used"):
            with_tool += 1
        ans = r.get("answer", "") or ""
        q = r.get("question", "") or ""
        if len(ans) < 20: short_answer += 1
        if len(q) < 5: empty_question += 1
        # crude lang detection
        is_vi = any(c in ans for c in "ăâđêôơưĂÂĐÊÔƠƯ")
        by_lang["vi" if is_vi else "en/other"] += 1
        distinct_lectures.add(r.get("lecture", ""))
        length_buckets[
            "<200" if len(ans) < 200 else
            "200-1000" if len(ans) < 1000 else
            "1000-3000" if len(ans) < 3000 else ">3000"
        ] += 1

# 2. DB audit
import asyncio
from sqlalchemy import select, func
from src.database import tutor_thread_async_session_factory
from src.models.store import QAHistory, Lecture, Chapter, TranscriptLine

async def db_audit():
    async with tutor_thread_async_session_factory() as db:
        qa_count = (await db.execute(select(func.count(QAHistory.id)))).scalar()
        lec_count = (await db.execute(select(func.count(Lecture.id)))).scalar()
        chap_count = (await db.execute(select(func.count(Chapter.id)))).scalar()
        line_count = (await db.execute(select(func.count(TranscriptLine.id)))).scalar()
        with_thoughts = (await db.execute(
            select(func.count(QAHistory.id)).where(QAHistory.thoughts.isnot(None))
        )).scalar()
        with_sandbox = (await db.execute(
            select(func.count(QAHistory.id)).where(QAHistory.thoughts.like("%[SANDBOX]%"))
        )).scalar()
        with_image = (await db.execute(
            select(func.count(QAHistory.id)).where(QAHistory.image_base64.isnot(None))
        )).scalar()
        return {
            "qa_history_rows": qa_count,
            "lectures": lec_count,
            "chapters": chap_count,
            "transcript_lines": line_count,
            "with_thoughts": with_thoughts,
            "with_sandbox_marker": with_sandbox,
            "with_image_truncated": with_image,
        }

db_stats = asyncio.run(db_audit())

# 3. Print report
report = {
    "jsonl_total": total,
    "jsonl_short_answer_dropped": short_answer,
    "jsonl_empty_question_dropped": empty_question,
    "jsonl_usable_estimate": total - short_answer - empty_question,
    "by_route": dict(by_route),
    "by_lang": dict(by_lang),
    "with_tool": with_tool,
    "length_distribution": dict(length_buckets),
    "distinct_lectures_jsonl": len(distinct_lectures),
    **db_stats,
}
print(json.dumps(report, indent=2, ensure_ascii=False))
Path("fine-tune-chatbot/data").mkdir(parents=True, exist_ok=True)
Path("fine-tune-chatbot/data/audit_report.json").write_text(
    json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
)
```

## Required output

`fine-tune-chatbot/data/audit_report.json` with these fields populated.

## Decision matrix

Based on `jsonl_usable_estimate` (after dropping short answers and empty
questions):

| Usable rows | Action |
|---|---|
| ≥ 8000 | Proceed P2 with organic data only |
| 3000–8000 | P2 + mandatory synthetic supplement (target +5000 from teacher model) |
| 1000–3000 | Synthetic-first: 80% synthetic, 20% organic; document in manifest |
| < 1000 | **Block self-hosting**: insufficient data, escalate to product team |

Based on `with_sandbox_marker` (tool-call source rows):

| Sandbox rows | Action |
|---|---|
| ≥ 1500 | Use as-is |
| 500–1500 | Augment with synthetic tool-call traces |
| < 500 | Mandatory synthetic tool-call generation; risk of weak tool calling |

Based on `by_lang["vi"]` ratio:

| Vietnamese ratio | Action |
|---|---|
| ≥ 60% | OK |
| 30–60% | Stratify split to oversample VN; weighted loss |
| < 30% | Generate synthetic VN data from EN translations |

## Schema verification

Run a one-off query to confirm join keys exist:

```python
async def verify_joins():
    async with tutor_thread_async_session_factory() as db:
        # Sample one lecture, check chapter + transcript availability
        lec = (await db.execute(select(Lecture).limit(1))).scalar_one_or_none()
        if not lec:
            return "FAIL: no lectures in DB"
        chaps = (await db.execute(
            select(Chapter).where(Chapter.lecture_id == lec.id)
        )).scalars().all()
        lines = (await db.execute(
            select(TranscriptLine).where(TranscriptLine.lecture_id == lec.id).limit(5)
        )).scalars().all()
        return {
            "sample_lecture_id": lec.id,
            "chapters": len(chaps),
            "transcript_lines_sample": len(lines),
        }
```

If `chapters == 0` or `transcript_lines_sample == 0` for sampled lectures
→ context reconstruction (P2 step 02) impossible → must use questions
without TOC/transcript context, accepting weaker training signal.

## Exit criteria

- [ ] `audit_report.json` generated and committed (small JSON, OK to commit)
- [ ] Decision matrix applied; selected action documented at top of P2 plan
- [ ] If escalation triggered, stop and discuss before P2
- [ ] Schema joins verified; if broken, P2 plan updated to skip context reconstruction
