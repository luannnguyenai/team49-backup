# AI Adaptive Learning Platform

Adaptive learning platform for course-first learning, lecture-grounded AI tutoring, canonical assessment items, KP-level mastery, and planner audit trails.

## Current Production Contract

The active runtime schema is canonical and course-first. Do not build new product logic on the old `modules`, `topics`, `questions`, `mastery_scores`, or `learning_paths` tables; those runtime tables have been dropped from the production schema.

Authoritative layers:

| Layer | Active tables / artifacts | Purpose |
| --- | --- | --- |
| Product shell | `courses`, `course_sections`, `learning_units`, `course_assets`, `course_overviews` | User-facing course catalog and lesson navigation. |
| Canonical content | `concepts_kp`, `units`, `unit_kp_map`, `question_bank`, `item_calibration`, `item_phase_map`, `item_kp_map`, `prerequisite_edges`, `pruned_edges` | Source-of-truth content, question bank, KP mapping, and prerequisite graph. |
| Learner state | `learner_mastery_kp`, `learning_progress_records`, `completed_units`, `waived_units`, `goal_preferences` | KP mastery, progress, skip/waive audit, and selected course goals. |
| Planner audit | `plan_history`, `rationale_log`, `planner_session_state` | Planner decisions, scoring rationale, abandon/resume state, and session continuity. |
| Tutor store | `lectures`, `chapters`, `transcript_lines`, `qa_history` | Lecture Q&A context and history. |

Generated JSONL under `data/final_artifacts/*/canonical/` is bootstrap/import data. PostgreSQL is the authoritative application database after import.

## What Works Today

- Course discovery and learning-unit pages use `courses/course_sections/learning_units`.
- Quiz, assessment, and module-test selection read canonical `question_bank` joined with `item_phase_map` and `item_kp_map`.
- Assessment evidence writes canonical interactions and updates `learner_mastery_kp`.
- Planner reads `learning_units`, `unit_kp_map`, `prerequisite_edges`, and `learner_mastery_kp`.
- Skip/waive decisions are audited in `waived_units` when the runtime has unit-level evidence.
- Abandon/resume state is stored in `planner_session_state.current_unit_id`, `current_stage`, `current_progress`, and `last_activity`.
- Mastery staleness is applied on-read by inflating uncertainty; raw `learner_mastery_kp` evidence is not overwritten just because a user was inactive.

## Scoring Status

Current mastery scoring is phase-1 KP posterior scoring, not validated production IRT/BKT.

- One answered canonical item updates all mapped KPs via `item_kp_map.weight`.
- If `item_calibration` has priors, the update uses a documented 2PL-lite residual: predicted probability from `difficulty_prior`, `discrimination_prior`, and `guessing_prior`; observed answer minus predicted probability drives the `theta_mu` delta.
- If calibration priors are missing, the service falls back to neutral parameters rather than fabricating fitted IRT values.
- Every update shrinks `theta_sigma` conservatively and recomputes `mastery_mean_cached`.
- Planner gates use `mastery_lcb = sigmoid((theta_mu - theta_sigma) / sqrt(1 + theta_sigma^2))`, with staleness applied on-read before the LCB calculation.
- `item_calibration` stores priors and reserved calibrated parameters, but true 1PL/2PL/3PL calibration still requires enough real or explicitly synthetic interaction data plus a calibration job.
- Do not claim production IRT/BKT accuracy until calibration has run and been validated.

See [Production DB Integration Handoff](docs/PRODUCTION_DB_INTEGRATION_HANDOFF.md) for field-level integration rules and [Schema Branch Snapshot](docs/SCHEMA_BRANCH_SNAPSHOT_2026-04-23.md) for table-by-table context.

## System Architecture

```text
Next.js App Router frontend
        |
        v
FastAPI routers
        |
        v
Service layer
  - content_service: course sections and learning units
  - quiz_service / assessment_service / module_test_service: canonical item selection
  - canonical_mastery_service: KP-level mastery updates
  - recommendation_engine: canonical planner output and audit writes
  - history_service: canonical interaction history
  - llm_service: lecture-grounded AI tutor
        |
        v
PostgreSQL + Redis + data/courses assets
```

## Tech Stack

| Area | Technology |
| --- | --- |
| Backend | Python 3.12, FastAPI, SQLAlchemy async, Pydantic v2, Alembic |
| Frontend | Next.js 14 App Router, React 18, TypeScript 5, Zustand, Axios, Tailwind CSS |
| Data | PostgreSQL 16, Redis 7, repository `data/` for bootstrap/import and course assets |
| AI tutor | LangChain/LangGraph with Gemini, OpenAI, or Anthropic provider |
| Tooling | `uv`, pytest, npm, Playwright, Docker Compose |

## Repository Layout

```text
src/
  api/app.py                         FastAPI app registration
  models/
    canonical.py                     Canonical content tables
    course.py                        Product course/section/unit tables
    learning.py                      Learner, planner, session, interaction tables
    store.py                         Tutor lecture/Q&A tables
  repositories/                      DB access helpers
  routers/                           API endpoints
  services/                          Runtime business logic
  scripts/pipeline/                  Canonical export/import/parity tooling
frontend/
  app/                               Next.js pages/routes
  components/                        React components
  lib/                               API clients and frontend mappers
  types/                             Frontend DTOs
data/
  courses/                           Course assets, transcripts, slides, videos
  final_artifacts/*/canonical/        Generated canonical JSONL import bundles
docs/
  PRODUCTION_DB_INTEGRATION_HANDOFF.md
  SCHEMA_BRANCH_SNAPSHOT_2026-04-23.md
  LEGACY_SCHEMA_CLEANUP_PLAN.md
```

## Setup

### Requirements

- Docker Desktop with Docker Compose v2, or local Python 3.12, Node.js 18+, PostgreSQL 16, Redis 7, and `uv`.
- At least one LLM API key for AI Tutor.
- Canonical bootstrap artifacts under `data/final_artifacts/.../canonical/`.
- Course assets under `data/courses/<course>/` for tutor/video functionality.

### Environment

```bash
cp .env.example .env
```

Minimum values:

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/ai_learning
REDIS_URL=redis://:password@localhost:6379/0
SECRET_KEY=replace-with-random-secret
MODEL_PROVIDER=google_genai
DEFAULT_MODEL=gemini-2.0-flash
GEMINI_API_KEY=...
```

Use the external SQL Server connection fields only if the integration layer explicitly supports that backend. The current application ORM path is PostgreSQL.

Forgot-password email delivery uses Resend. For local or production setup, configure:

```env
RESEND_API_KEY=re_...
EMAIL_FROM=noreply@your-verified-domain.com
FRONTEND_BASE_URL=http://localhost:3000
PASSWORD_RESET_TOKEN_TTL_MINUTES=30
RATE_LIMIT_FORGOT_PASSWORD_PER_HOUR=5
```

See [Forgot Password + Resend Setup Guide](docs/forgot-password-resend.md) for Resend setup and the full reset flow.

LangFuse tracing is optional and fail-safe. The `.env.example` files already match the current LangFuse SDK naming:

```env
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
# Optional backward-compatible alias for older local configs
LANGFUSE_HOST=https://cloud.langfuse.com
NEXT_PUBLIC_LANGFUSE_HOST=https://cloud.langfuse.com
```

Notes:

- `LANGFUSE_BASE_URL` is the preferred backend variable from current LangFuse docs.
- `LANGFUSE_HOST` is kept only as a compatibility alias for older repo/local setups.
- `NEXT_PUBLIC_LANGFUSE_HOST` is frontend UI/embed configuration only; it does not enable backend tracing.
- For non-EU Cloud or self-hosted LangFuse, change `LANGFUSE_BASE_URL` to the correct region/host.

### Run With Docker

```bash
docker compose up -d --build
docker compose exec backend alembic upgrade head
```

Import canonical content and product shell:

```bash
docker compose exec backend python -m src.scripts.pipeline.import_canonical_artifacts_to_db
docker compose exec backend python -m src.scripts.pipeline.import_product_shell_to_db
docker compose exec backend python -m src.scripts.pipeline.check_canonical_runtime_parity
```

AI Tutor lecture store, if needed:

```bash
docker compose exec backend python -m scripts.seed_lectures
```

Open:

| URL | Purpose |
| --- | --- |
| `http://localhost:3000` | Frontend |
| `http://localhost:8000/docs` | Swagger |
| `http://localhost:8000/health` | Backend health |

### Run Locally

```bash
uv sync
uv run alembic upgrade head
uv run python -m src.scripts.pipeline.import_canonical_artifacts_to_db
uv run python -m src.scripts.pipeline.import_product_shell_to_db
uv run python -m src.scripts.pipeline.check_canonical_runtime_parity
uv run python main.py
```

Frontend:

```bash
cd frontend
npm install
printf "NEXT_PUBLIC_API_URL=http://localhost:8000\n" > .env.local
npm run dev
```

## API Surface

| Area | Endpoints | Data contract |
| --- | --- | --- |
| Auth/onboarding | `/api/auth/*`, `/api/users/me/onboarding` | Onboarding writes `goal_preferences`; forgot password uses Resend-backed `/api/auth/forgot-password/request` and `/api/auth/forgot-password/confirm`. |
| Content | `/api/course-sections`, `/api/course-sections/{id}`, `/api/learning-units/{id}/content` | Product shell reads `course_sections` and `learning_units` linked to canonical unit IDs. |
| Quiz | `/api/quiz/start`, `/api/quiz/{session_id}/answer`, `/api/quiz/{session_id}/complete` | Uses canonical learning unit IDs and `question_bank` phase `mini_quiz`. |
| Assessment | `/api/assessment/start`, `/api/assessment/{session_id}/submit`, `/api/assessment/{session_id}/results` | Uses `learning_unit_ids`; results return `learning_unit_results`. |
| Review / placement-lite | `/api/review/start`, `/api/placement-lite/start` | Runtime support for long-return quick checks and placement-lite recalibration. Both reuse assessment session submission. |
| Module test | `/api/module-test/start`, `/api/module-test/{session_id}/submit`, `/api/module-test/{session_id}/results` | Uses section/unit semantics and canonical item selection. |
| Learning path | `/api/learning-path/generate`, `/api/learning-path`, `/api/learning-path/timeline`, `/api/learning-path/{id}/status` | Planner returns unit-grain path, writes `plan_history`, `rationale_log`, and `planner_session_state`. |
| Learning session | `/api/learning-session/resume`, `/api/learning-session/learning-units/{id}/progress` | Stores current unit/stage/progress for abandon/resume and returns the resume route. |
| History | `/api/history`, `/api/history/{session_id}/detail` | Canonical interactions link via `interactions.canonical_item_id -> question_bank.item_id`. |
| Tutor | `/api/lectures/*` | Lecture transcript/slide Q&A path; separate from canonical planner content. |

## LLM Tracing

The app uses a LangFuse root-span-first pattern for traced AI flows:

- create one LangFuse SDK root observation per user-visible AI task
- propagate stable attributes such as `langfuse_user_id`, `langfuse_session_id`, and `langfuse_tags`
- run LangChain/LangGraph callbacks inside that active context
- persist tutor `trace_id` on `qa_history` so thumbs-up/down feedback can be attached back to the same trace

Current traced flows:

- Tutor streaming: `/api/lectures/ask`
- Tutor rating to LangFuse score linkage: `/api/lectures/{qa_id}/rate`
- Assessment AI summary generation
- Onboarding prior-analysis across both LangChain-backed and direct OpenAI branches

Tutor traces also expose internal child observations for:

- context fetch
- route selection
- transcript-window retrieval
- QA persistence

Local smoke check:

1. Fill `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_BASE_URL` in root `.env`.
2. Restart backend.
3. Call one tutor request, one onboarding prior-analysis request, and one assessment summary request.
4. Rate a tutor answer.
5. Confirm traces and the `user_thumb` score appear in LangFuse.

The `langfuse/skills` GitHub repo is an agent-environment helper for coding assistants. It is not an application runtime dependency for this repo.

## Validation

Useful checks before handing work to another teammate:

```bash
uv run python -m src.scripts.pipeline.import_canonical_artifacts_to_db --validate-only
uv run python -m src.scripts.pipeline.import_product_shell_to_db --validate-only
uv run python -m src.scripts.pipeline.check_canonical_runtime_parity
uv run pytest tests/services/test_assessment_canonical_cutover.py tests/services/test_module_test_canonical_cutover.py -q
npm --prefix frontend run type-check
```

Known test caveat: the route contract suite using `httpx.ASGITransport(app=app)` has shown an existing request hang in this branch. Service-level canonical runtime tests are the reliable regression signal until that harness is fixed.

## Synthetic Demo Data

Deterministic demo users can be generated after canonical content and product shell are imported:

```bash
.venv/bin/python -m src.scripts.pipeline.reset_demo_accounts
.venv/bin/python -m src.scripts.pipeline.reset_synthetic_cohort
.venv/bin/python -m src.scripts.pipeline.generate_synthetic_demo_users --dataset all
```

The source of truth is hand-authored JSON in `data/synthetic/*/scenarios.json`. The Python script only validates scenarios, resolves real course/unit/item IDs, writes resettable JSONL snapshots, and optionally imports them. Demo login accounts use `@vinuni.edu.vn` and password `DemoPass123!`; the 30-user synthetic cohort is separate from those 9 demo accounts.

## Historical Docs

Files under `docs/superpowers/plans/` and `docs/superpowers/specs/` are implementation history unless the file explicitly says it is the active contract. They may mention transitional feature flags, compatibility fallbacks, or dropped tables. Treat these as audit context, not production design authority.

Active references:

- [Production DB Integration Handoff](docs/PRODUCTION_DB_INTEGRATION_HANDOFF.md)
- [Schema Branch Snapshot](docs/SCHEMA_BRANCH_SNAPSHOT_2026-04-23.md)
- [Legacy Schema Cleanup Plan](docs/LEGACY_SCHEMA_CLEANUP_PLAN.md)
- [THINGS NEED FIX](THINGS%20NEED%20FIX.md)

## Troubleshooting

| Problem | Likely cause | Fix |
| --- | --- | --- |
| Backend starts but content is empty | Canonical artifacts or product shell were not imported | Run canonical importer, product shell importer, then parity check. |
| Quiz/assessment has no questions | Missing `item_phase_map` or `item_kp_map` rows for selected unit/phase | Validate canonical artifacts and inspect `question_bank` joins. |
| Planner recommendations look flat | Sparse prerequisite graph, missing KP mastery, or only neutral calibration priors | Check `prerequisite_edges`, `unit_kp_map`, `item_calibration`, and current `learner_mastery_kp` distribution. |
| Tutor cannot answer lecture-specific questions | Missing `data/courses/<course>/transcripts` or lecture seed | Restore course assets and run `scripts.seed_lectures`. |
| LangFuse UI link works but no backend traces appear | Missing LangFuse keys, wrong `LANGFUSE_BASE_URL`, or backend was not restarted | Fill root `.env`, prefer `LANGFUSE_BASE_URL`, restart backend, then hit a traced LLM endpoint. |
| Docs mention `modules/topics/questions` as active | Historical doc, not current contract | Use the active references above. |

## Contribution Notes

- Run `bash scripts/setup_hooks.sh` before opening a PR so AI prompt logging hooks are installed.
- Do not commit `.ai-log/*.jsonl`.
- Do not reintroduce dropped legacy runtime tables for new product work.
- Keep new learner/planner logic KP-level and learning-unit-level, not topic/module-level.
