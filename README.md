# AI Adaptive Learning Platform

Nền tảng học tập thích ứng sử dụng AI, giúp cá nhân hóa lộ trình học cho từng học sinh dựa trên năng lực thực tế.

## Quick Links

| Hạng mục | Link |
|---|---|
| Live URL | [https://a20-app-049.io.vn](https://a20-app-049.io.vn) |
| Demo Video | _Đang cập nhật_ |
| Pitch Deck | _Đang cập nhật_ |
| Architecture | [docs/architecture.md](docs/architecture.md) |
| AI Logs | [docs/ai-logs.md](docs/ai-logs.md) |
| Worklog | [docs/WORKLOG.md](docs/WORKLOG.md) |
| Weekly Journal | [docs/JOURNAL.md](docs/JOURNAL.md) |
| Evaluation Report | [docs/evaluation-report.md](docs/evaluation-report.md) |

---

## 1. Giới thiệu dự án

**AI Adaptive Tutor** là nền tảng học tập cá nhân hóa, nơi AI đóng vai trò gia sư 24/7 — hướng dẫn học sinh học đúng thứ họ cần, đúng thời điểm, dựa trên năng lực thực tế được đo lường liên tục.

Sản phẩm hướng tới học sinh từ cấp 2 đến đại học, đặc biệt những bạn tự học qua tài liệu online mà thiếu lộ trình rõ ràng và không có người hướng dẫn thường xuyên.

## 2. Vấn đề cần giải quyết

Học sinh tự học hiện tại gặp các vấn đề:

- **Không biết mình yếu ở đâu** — thiếu công cụ đánh giá năng lực chính xác
- **Nội dung học không phù hợp level** — học quá dễ hoặc quá khó, mất thời gian
- **Không có feedback tức thì** — làm bài xong không biết đúng sai, không hiểu tại sao
- **Không có người hướng dẫn 24/7** — muốn hỏi lúc nào cũng phải tự tìm

Hệ quả: học sinh học lan man, mất động lực, không tối ưu được thời gian học.

## 3. Giải pháp

AI Adaptive Tutor giải quyết bằng vòng lặp học tập thích ứng:

1. **Đánh giá năng lực** — Diagnostic quiz xác định level và điểm yếu theo từng Knowledge Point (KP)
2. **Lộ trình cá nhân hóa** — Planner tự động đề xuất nội dung học dựa trên mastery thực tế, prerequisite graph và mục tiêu cá nhân
3. **Học + Feedback tức thì** — Học bài, làm quiz, nhận giải thích ngay lập tức bằng AI tutor
4. **Cập nhật mastery** — Mỗi lần trả lời, hệ thống cập nhật điểm mastery theo KP và điều chỉnh lộ trình

## 4. Tính năng chính

- **Onboarding & Placement Assessment** — Đánh giá đầu vào để xác định level và chọn mục tiêu học
- **Adaptive Learning Path** — Lộ trình học cá nhân hóa dựa trên KP mastery và prerequisite graph
- **AI Tutor 24/7** — Gia sư AI hỗ trợ giải đáp trong ngữ cảnh bài giảng, có thể chạy code Python sandbox
- **Quiz & Assessment** — Mini quiz, module test, placement test với feedback tức thì
- **Mastery Tracking** — Theo dõi tiến độ theo từng Knowledge Point với IRT scoring
- **Guardrail & Safety** — Smart Router phân loại intent, Guardrail Router chặn prompt injection và off-topic
- **Video Learning** — Xem bài giảng video với progress tracking và inline quiz
- **Lecture Q&A** — Hỏi đáp trong context bài giảng, AI trả lời dựa trên transcript + slides

## 5. Kiến trúc hệ thống

```text
User (Browser)
      │
      ▼
Next.js 14 App Router (Frontend)
      │
      ▼
FastAPI (Backend API)
      │
      ├──► Service Layer
      │       ├── content_service (course, sections, units)
      │       ├── quiz_service / assessment_service
      │       ├── canonical_mastery_service (KP mastery)
      │       ├── recommendation_engine (planner + audit)
      │       ├── llm_service (AI Tutor — LangGraph ReAct Agent)
      │       └── guardrail_router (safety + topic classification)
      │
      ├──► PostgreSQL 16 (canonical content, learner state, planner audit)
      ├──► Redis 7 (cache, sessions)
      └──► External LLM Providers (Gemini, OpenAI, Anthropic)
```

Chi tiết: [docs/architecture.md](docs/architecture.md)

## 6. Công nghệ sử dụng

| Thành phần | Công nghệ |
|---|---|
| Frontend | Next.js 14 App Router, React 18, TypeScript 5, Zustand, Tailwind CSS |
| Backend/API | Python 3.12, FastAPI, SQLAlchemy async, Pydantic v2, Alembic |
| Database | PostgreSQL 16, Redis 7 |
| AI Agent/LLM | LangChain, LangGraph, Gemini / OpenAI / Anthropic |
| Observability | Langfuse (LLM tracing), Prometheus, Grafana, Loki |
| Deployment | Docker Compose, AWS ECS/Fargate, Terraform |
| Testing | pytest, Playwright, golden eval dataset (50+ cases) |

## 7. Cài đặt và chạy local

### Yêu cầu

- Docker Desktop với Docker Compose v2, hoặc Python 3.12, Node.js 18+, PostgreSQL 16, Redis 7, `uv`
- Ít nhất 1 LLM API key (Gemini, OpenAI, hoặc Anthropic)

### Cách 1: Docker (khuyến nghị)

```bash
git clone https://github.com/a20-ai-thuc-chien/A20-App-049.git
cd A20-App-049
cp .env.example .env
# Điền API keys vào .env

docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -m src.scripts.pipeline.import_canonical_artifacts_to_db
docker compose exec backend python -m src.scripts.pipeline.import_product_shell_to_db
```

### Cách 2: Chạy trực tiếp

```bash
# Backend
uv sync
cp .env.example .env
uv run alembic upgrade head
uv run python -m src.scripts.pipeline.import_canonical_artifacts_to_db
uv run python -m src.scripts.pipeline.import_product_shell_to_db
uv run python main.py

# Frontend
cd frontend
npm install
printf "NEXT_PUBLIC_API_URL=http://localhost:8000\n" > .env.local
npm run dev
```

### Truy cập

| URL | Mô tả |
|---|---|
| `http://localhost:3000` | Frontend |
| `http://localhost:8000/docs` | Swagger API docs |
| `http://localhost:8000/health` | Health check |

## 8. Biến môi trường

Không commit file `.env`. Chỉ commit `.env.example`.

Biến chính:

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5433/ai_learning
REDIS_URL=redis://:password@localhost:6379/0
SECRET_KEY=replace-with-random-secret
MODEL_PROVIDER=google_genai
DEFAULT_MODEL=gemini-2.0-flash
GEMINI_API_KEY=...
```

Xem `.env.example` để biết đầy đủ các biến môi trường.

## 9. Cách sử dụng sản phẩm

### Luồng chính: Học tập thích ứng

1. **Đăng ký / Đăng nhập** — Tạo tài khoản hoặc đăng nhập
2. **Onboarding** — Chọn mục tiêu học (ví dụ: Deep Learning, Computer Vision, NLP)
3. **Placement Assessment** — Làm bài đánh giá đầu vào (5-10 câu) để xác định level
4. **Xem lộ trình** — Hệ thống đề xuất lộ trình học cá nhân hóa dựa trên kết quả đánh giá
5. **Học bài** — Xem video bài giảng, đọc nội dung, hỏi AI Tutor bất cứ lúc nào
6. **Làm quiz** — Sau mỗi bài học, làm mini quiz để kiểm tra hiểu bài
7. **Xem feedback** — Nhận giải thích chi tiết cho từng câu trả lời
8. **Cập nhật lộ trình** — Hệ thống tự động điều chỉnh lộ trình dựa trên kết quả mới

### Tài khoản demo

Email: `demo@vinuni.edu.vn` | Password: `DemoPass123!`

## 10. Demo và kết quả

- **Live URL:** [https://a20-app-049.io.vn](https://a20-app-049.io.vn)
- **Video Demo:** _Đang cập nhật_
- **Evaluation Report:** [docs/evaluation-report.md](docs/evaluation-report.md)
- **AI Logs:** [docs/ai-logs.md](docs/ai-logs.md)
- **Golden Eval Dataset:** 50+ test cases cho agent behavior ([docs/agent-golden-evals.md](docs/agent-golden-evals.md))
- **Guardrail Router:** 13,513 samples cho safety/topic classification

## 11. Evaluation

Chi tiết: [docs/evaluation-report.md](docs/evaluation-report.md)

Tóm tắt:

| Loại đánh giá | Số lượng | Mô tả |
|---|---|---|
| API Contract Tests | 13+ | Kiểm tra HTTP route contracts |
| Service Logic Tests | 10+ | Kiểm tra business logic |
| Golden Eval Cases | 50+ | Kiểm tra hành vi AI Agent |
| Guardrail Dataset | 13,513 | Kiểm tra phân loại safety/topic |
| Integration Tests | 5+ | Kiểm tra luồng end-to-end |

Failure cases và cách xử lý được ghi nhận trong [docs/evaluation-report.md](docs/evaluation-report.md).

## 12. Team & Phân công công việc

| Thành viên | Vai trò | Công việc chính |
|---|---|---|
| _Tên thành viên 1_ | _Vai trò_ | _Mô tả công việc_ |
| _Tên thành viên 2_ | _Vai trò_ | _Mô tả công việc_ |
| _Tên thành viên 3_ | _Vai trò_ | _Mô tả công việc_ |
| _Tên thành viên 4_ | _Vai trò_ | _Mô tả công việc_ |

> Vui lòng cập nhật bảng trên với thông tin thực tế của team.

## 13. Hạn chế và hướng phát triển

### Hạn chế hiện tại

- IRT/BKT mastery scoring đang ở phase-1 (posterior scoring), chưa có calibration job với dữ liệu thực
- Golden eval dataset kiểm tra hành vi expected, chưa đo live model accuracy/latency quantitatively
- Route contract test suite có lỗi request hang (httpx.ASGITransport) — service-level tests là regression signal chính
- Nội dung học hiện tập trung vào Computer Vision / Deep Learning, chưa mở rộng nhiều domain

### Hướng phát triển

- Chạy IRT calibration job với dữ liệu interaction thực để nâng cấp mastery scoring
- Thêm domain mới (NLP, Mathematics, Programming)
- Mở rộng AI Agent với thêm tools (web search, document retrieval)
- A/B testing prompt versions để tối ưu chất lượng AI tutor
- Dashboard cho giáo viên theo dõi tiến độ lớp học
- Mobile app (React Native)

---

## Technical Reference

Các tài liệu kỹ thuật chi tiết:

- [Production DB Integration Handoff](docs/PRODUCTION_DB_INTEGRATION_HANDOFF.md)
- [Schema Branch Snapshot](docs/SCHEMA_BRANCH_SNAPSHOT_2026-04-23.md)
- [Forgot Password + Resend Setup](docs/forgot-password-resend.md)
- [ECS Deployment Guide](deploy-ecs/README.md)

### Current Production Contract

The active runtime schema is canonical and course-first. Do not build new product logic on the old `modules`, `topics`, `questions`, `mastery_scores`, or `learning_paths` tables; those runtime tables have been dropped from the production schema.

Authoritative layers:

| Layer | Active tables / artifacts | Purpose |
|---|---|---|
| Product shell | `courses`, `course_sections`, `learning_units`, `course_assets`, `course_overviews` | User-facing course catalog and lesson navigation |
| Canonical content | `concepts_kp`, `units`, `unit_kp_map`, `question_bank`, `item_calibration`, `item_kp_map`, `prerequisite_edges`, `pruned_edges` | Source-of-truth content, question bank, KP mapping, and prerequisite graph |
| Learner state | `learner_mastery_kp`, `learning_progress_records`, `completed_units`, `waived_units`, `goal_preferences` | KP mastery, progress, skip/waive audit, and selected course goals |
| Planner audit | `plan_history`, `rationale_log`, `planner_session_state` | Planner decisions, scoring rationale, abandon/resume state |
| Tutor store | `lectures`, `chapters`, `transcript_lines`, `qa_history` | Lecture Q&A context and history |

### Repository Layout

```text
src/
  api/app.py                         FastAPI app registration
  models/                            SQLAlchemy models (canonical, course, learning, store)
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
docs/                                Documentation, journals, evaluation
alembic/                             Database migrations (26+ versions)
deploy-ecs/                          AWS ECS deployment (Terraform, task defs, observability)
```

### API Surface

| Area | Endpoints | Mô tả |
|---|---|---|
| Auth/Onboarding | `/api/auth/*`, `/api/users/me/onboarding` | Đăng ký, đăng nhập, forgot password, onboarding goals |
| Content | `/api/course-sections`, `/api/learning-units/{id}/content` | Course catalog và learning unit content |
| Quiz | `/api/quiz/start`, `/api/quiz/{id}/answer`, `/api/quiz/{id}/complete` | Mini quiz với canonical question bank |
| Assessment | `/api/assessment/start`, `/api/assessment/{id}/submit`, `/api/assessment/{id}/results` | Placement assessment và results |
| Learning Path | `/api/learning-path/generate`, `/api/learning-path`, `/api/learning-path/timeline` | Adaptive learning path generation |
| Learning Session | `/api/learning-session/resume`, `/api/learning-session/learning-units/{id}/progress` | Abandon/resume và progress tracking |
| AI Tutor | `/api/lectures/ask`, `/api/lectures/{qa_id}/rate` | Lecture Q&A streaming với rating |
| History | `/api/history`, `/api/history/{id}/detail` | Interaction history |

### LLM Tracing

LangFuse root-span-first pattern cho traced AI flows:
- Tutor streaming: `/api/lectures/ask`
- Rating linkage: `/api/lectures/{qa_id}/rate`
- Assessment AI summary generation
- Onboarding prior-analysis

### Validation

```bash
uv run python -m src.scripts.pipeline.import_canonical_artifacts_to_db --validate-only
uv run python -m src.scripts.pipeline.import_product_shell_to_db --validate-only
uv run python -m src.scripts.pipeline.check_canonical_runtime_parity
uv run pytest tests/services/test_assessment_canonical_cutover.py tests/services/test_module_test_canonical_cutover.py -q
npm --prefix frontend run type-check
```

### Synthetic Demo Data

```bash
.venv/bin/python -m src.scripts.pipeline.reset_demo_accounts
.venv/bin/python -m src.scripts.pipeline.reset_synthetic_cohort
.venv/bin/python -m src.scripts.pipeline.generate_synthetic_demo_users --dataset all
```

Demo accounts: `@vinuni.edu.vn`, password `DemoPass123!`

### Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| Backend starts but content is empty | Canonical artifacts not imported | Run canonical + product shell importers |
| Quiz has no questions | Missing `item_phase_map` or `item_kp_map` | Validate canonical artifacts |
| Planner looks flat | Sparse prerequisite graph | Check `prerequisite_edges`, `unit_kp_map` |
| Tutor can't answer lecture questions | Missing transcripts | Restore course assets, run `seed_lectures` |
| No LangFuse traces | Missing keys or wrong URL | Fill root `.env`, restart backend |

### Contribution Notes

- Run `bash scripts/setup_hooks.sh` before opening a PR
- Do not commit `.ai-log/*.jsonl`
- Do not reintroduce dropped legacy runtime tables
- Keep new logic KP-level and learning-unit-level
