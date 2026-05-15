<div align="center">
  <img src="./heroimage.png" alt="AI Adaptive Learning Platform" width="800"/>

  # AI Adaptive Learning Platform

  > *"Học đúng thứ bạn yếu, với lộ trình riêng cho bạn — có AI hướng dẫn 24/7"*

  **Nền tảng học tập thích ứng sử dụng AI — cá nhân hóa lộ trình học cho từng học sinh dựa trên năng lực thực tế.**

  [![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
  [![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
  [![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
  [![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
  [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
  [![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
  [![LangChain](https://img.shields.io/badge/LangChain-LangGraph-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://www.langchain.com/)
  [![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docs.docker.com/compose/)
  [![AWS](https://img.shields.io/badge/AWS-ECS%2FFargate-FF9900?style=for-the-badge&logo=amazonecs&logoColor=white)](https://aws.amazon.com/ecs/)
  [![Terraform](https://img.shields.io/badge/Terraform-IaC-844FBA?style=for-the-badge&logo=terraform&logoColor=white)](https://www.terraform.io/)
  [![Langfuse](https://img.shields.io/badge/Langfuse-Tracing-4F46E5?style=for-the-badge)](https://langfuse.com/)

  ---

  [**:rocket: Live Demo**](https://a20-app-049.io.vn) · [**:books: Architecture**](docs/architecture.md) · [**:robot: AI Logs**](docs/ai-logs.md) · [**:bar_chart: Evaluation**](docs/evaluation-report.md) · [**:memo: Worklog**](docs/WORKLOG.md) · [**:notebook: Journal**](docs/JOURNAL.md)

</div>

---

## :link: Quick Links

| Hạng mục | Link |
|---|---|
| :globe_with_meridians: Live URL | [https://a20-app-049.io.vn](https://a20-app-049.io.vn) |
| :clapper: Demo Video | _Đang cập nhật_ |
| :bar_chart: Pitch Deck | _Đang cập nhật_ |
| :triangular_ruler: Architecture | [docs/architecture.md](docs/architecture.md) |
| :robot: AI Logs | [docs/ai-logs.md](docs/ai-logs.md) |
| :clipboard: Worklog | [docs/WORKLOG.md](docs/WORKLOG.md) |
| :notebook: Weekly Journal | [docs/JOURNAL.md](docs/JOURNAL.md) |
| :white_check_mark: Evaluation Report | [docs/evaluation-report.md](docs/evaluation-report.md) |

---

## :bulb: 1. Giới thiệu dự án

**AI Adaptive Tutor** là nền tảng học tập cá nhân hóa, nơi AI đóng vai trò gia sư 24/7 — hướng dẫn học sinh học đúng thứ họ cần, đúng thời điểm, dựa trên năng lực thực tế được đo lường liên tục.

Sản phẩm hướng tới học sinh từ cấp 2 đến đại học, đặc biệt những bạn tự học qua tài liệu online mà thiếu lộ trình rõ ràng và không có người hướng dẫn thường xuyên.

---

## :warning: 2. Vấn đề cần giải quyết

> **80% học sinh tự học online không có lộ trình rõ ràng và không biết mình yếu ở đâu.**

| Vấn đề | Hệ quả |
|---|---|
| :x: Không biết mình yếu ở đâu | Học lan man, không tập trung đúng chỗ |
| :x: Nội dung không phù hợp level | Học quá dễ hoặc quá khó, mất thời gian |
| :x: Không có feedback tức thì | Làm bài xong không biết đúng sai, không hiểu tại sao |
| :x: Không có người hướng dẫn 24/7 | Muốn hỏi lúc nào cũng phải tự tìm |

**Kết quả:** Học sinh mất động lực, học không hiệu quả, không tối ưu được thời gian.

---

## :rocket: 3. Giải pháp

AI Adaptive Tutor giải quyết bằng **vòng lặp học tập thích ứng (Adaptive Learning Loop)**:

```
  +-------------------+       +---------------------+       +------------------+
  | 1. Đánh giá       | ----> | 2. Lộ trình         | ----> | 3. Học + Quiz    |
  | năng lực (KP)     |       | cá nhân hóa         |       | + AI Tutor       |
  +-------------------+       +---------------------+       +------------------+
         ^                                                          |
         |                  +---------------------+                 |
         +----------------- | 4. Cập nhật mastery | <---------------+
                            | + điều chỉnh path   |
                            +---------------------+
```

| Bước | Mô tả |
|---|---|
| :one: **Diagnostic Assessment** | Quiz xác định level và điểm yếu theo từng Knowledge Point (KP) |
| :two: **Personalized Path** | Planner tự động đề xuất nội dung học dựa trên mastery, prerequisite graph và mục tiêu |
| :three: **Learn + Instant Feedback** | Học bài, làm quiz, nhận giải thích ngay lập tức bằng AI tutor |
| :four: **Mastery Update** | Hệ thống cập nhật điểm mastery theo KP và điều chỉnh lộ trình |

---

## :star2: 4. Tính năng chính

| Tính năng | Mô tả | AI-powered |
|---|---|:---:|
| :dart: **Onboarding & Placement** | Đánh giá đầu vào để xác định level và chọn mục tiêu học | :white_check_mark: |
| :compass: **Adaptive Learning Path** | Lộ trình cá nhân hóa dựa trên KP mastery và prerequisite graph | :white_check_mark: |
| :robot: **AI Tutor 24/7** | Gia sư AI hỗ trợ giải đáp trong ngữ cảnh bài giảng, chạy code Python sandbox | :white_check_mark: |
| :pencil2: **Quiz & Assessment** | Mini quiz, module test, placement test với feedback tức thì | :white_check_mark: |
| :chart_with_upwards_trend: **Mastery Tracking** | Theo dõi tiến độ theo từng Knowledge Point với IRT scoring | |
| :shield: **Guardrail & Safety** | Smart Router phân loại intent, Guardrail Router chặn prompt injection | :white_check_mark: |
| :tv: **Video Learning** | Xem bài giảng video với progress tracking và inline quiz | |
| :speech_balloon: **Lecture Q&A** | Hỏi đáp trong context bài giảng, AI trả lời dựa trên transcript + slides | :white_check_mark: |

---

## :building_construction: 5. Kiến trúc hệ thống

```text
User (Browser)
      |
      v
+-------------------------------------------+
| Next.js 14 App Router (Frontend)          |
| React 18 · TypeScript 5 · Tailwind CSS   |
+-------------------------------------------+
      |
      v
+-------------------------------------------+
| FastAPI (Backend API)                     |
| Python 3.12 · Pydantic v2 · Alembic      |
+-------------------------------------------+
      |
      +--------> Service Layer
      |            |-- content_service (course, sections, units)
      |            |-- quiz_service / assessment_service
      |            |-- canonical_mastery_service (KP mastery)
      |            |-- recommendation_engine (planner + audit)
      |            |-- llm_service (AI Tutor — LangGraph ReAct Agent)
      |            +-- guardrail_router (safety + topic classification)
      |
      +--------> PostgreSQL 16 (canonical content, learner state, planner)
      +--------> Redis 7 (cache, sessions)
      +--------> LLM Providers (Gemini, OpenAI, Anthropic)
      +--------> Langfuse (LLM observability & tracing)
```

:point_right: Chi tiết: [**docs/architecture.md**](docs/architecture.md) (Mermaid diagrams, data flow, deployment)

---

## :wrench: 6. Công nghệ sử dụng

| Thành phần | Công nghệ |
|---|---|
| :art: Frontend | Next.js 14 App Router, React 18, TypeScript 5, Zustand, Tailwind CSS |
| :gear: Backend/API | Python 3.12, FastAPI, SQLAlchemy async, Pydantic v2, Alembic |
| :floppy_disk: Database | PostgreSQL 16, Redis 7 |
| :brain: AI Agent/LLM | LangChain, LangGraph, Gemini / OpenAI / Anthropic |
| :mag: Observability | Langfuse (LLM tracing), Prometheus, Grafana, Loki |
| :cloud: Deployment | Docker Compose, AWS ECS/Fargate, Terraform |
| :test_tube: Testing | pytest, Playwright, golden eval dataset (50+ cases) |

---

## :computer: 7. Cài đặt và chạy local

### Yêu cầu

- Docker Desktop với Docker Compose v2, hoặc Python 3.12, Node.js 18+, PostgreSQL 16, Redis 7, `uv`
- Ít nhất 1 LLM API key (Gemini, OpenAI, hoặc Anthropic)

### Cách 1: Docker (khuyến nghị) :whale:

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

### Cách 2: Chạy trực tiếp :zap:

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
| :globe_with_meridians: `http://localhost:3000` | Frontend |
| :page_facing_up: `http://localhost:8000/docs` | Swagger API docs |
| :heartbeat: `http://localhost:8000/health` | Health check |

---

## :key: 8. Biến môi trường

> :warning: **Không commit file `.env`.** Chỉ commit `.env.example`.

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5433/ai_learning
REDIS_URL=redis://:password@localhost:6379/0
SECRET_KEY=replace-with-random-secret
MODEL_PROVIDER=google_genai
DEFAULT_MODEL=gemini-2.0-flash
GEMINI_API_KEY=...
```

Xem `.env.example` để biết đầy đủ các biến môi trường.

---

## :joystick: 9. Cách sử dụng sản phẩm

### Luồng chính: Học tập thích ứng

| Bước | Hành động | Mô tả |
|:---:|---|---|
| 1 | :door: **Đăng ký / Đăng nhập** | Tạo tài khoản hoặc đăng nhập |
| 2 | :dart: **Onboarding** | Chọn mục tiêu học (Deep Learning, Computer Vision, NLP) |
| 3 | :pencil: **Placement Assessment** | Làm bài đánh giá đầu vào (5-10 câu) để xác định level |
| 4 | :world_map: **Xem lộ trình** | Hệ thống đề xuất lộ trình cá nhân hóa dựa trên kết quả |
| 5 | :books: **Học bài** | Xem video bài giảng, đọc nội dung, hỏi AI Tutor bất cứ lúc nào |
| 6 | :pencil2: **Làm quiz** | Sau mỗi bài học, làm mini quiz để kiểm tra hiểu bài |
| 7 | :bulb: **Xem feedback** | Nhận giải thích chi tiết cho từng câu trả lời |
| 8 | :arrows_counterclockwise: **Cập nhật lộ trình** | Hệ thống tự động điều chỉnh lộ trình dựa trên kết quả mới |

### :bust_in_silhouette: Tài khoản demo

| | |
|---|---|
| **Email** | `demo@vinuni.edu.vn` |
| **Password** | `DemoPass123!` |

---

## :movie_camera: 10. Demo và kết quả

| Hạng mục | Link / Thông tin |
|---|---|
| :globe_with_meridians: **Live URL** | [https://a20-app-049.io.vn](https://a20-app-049.io.vn) |
| :clapper: **Video Demo** | _Đang cập nhật_ |
| :white_check_mark: **Evaluation Report** | [docs/evaluation-report.md](docs/evaluation-report.md) |
| :robot: **AI Logs** | [docs/ai-logs.md](docs/ai-logs.md) |
| :test_tube: **Golden Eval Dataset** | 50+ test cases ([docs/agent-golden-evals.md](docs/agent-golden-evals.md)) |
| :shield: **Guardrail Router** | 13,513 samples safety/topic classification |

---

## :bar_chart: 11. Evaluation

> Chi tiết: [**docs/evaluation-report.md**](docs/evaluation-report.md)

| Loại đánh giá | Số lượng | Mô tả |
|---|---|---|
| :white_check_mark: API Contract Tests | 13+ | Kiểm tra HTTP route contracts |
| :gear: Service Logic Tests | 10+ | Kiểm tra business logic |
| :robot: Golden Eval Cases | 50+ | Kiểm tra hành vi AI Agent (10+ categories) |
| :shield: Guardrail Dataset | 13,513 | Kiểm tra phân loại safety/topic |
| :arrows_counterclockwise: Integration Tests | 5+ | Kiểm tra luồng end-to-end |

**Failure cases** và cách xử lý được ghi nhận trong [docs/evaluation-report.md](docs/evaluation-report.md).

---

## :busts_in_silhouette: 12. Team & Phân công công việc

| Thành viên | Vai trò | Công việc chính |
|---|---|---|
| _Tên thành viên 1_ | _Vai trò_ | _Mô tả công việc_ |
| _Tên thành viên 2_ | _Vai trò_ | _Mô tả công việc_ |
| _Tên thành viên 3_ | _Vai trò_ | _Mô tả công việc_ |
| _Tên thành viên 4_ | _Vai trò_ | _Mô tả công việc_ |

> :pencil2: Vui lòng cập nhật bảng trên với thông tin thực tế của team.

---

## :crystal_ball: 13. Hạn chế và hướng phát triển

### Hạn chế hiện tại

| # | Hạn chế | Ghi chú |
|---|---|---|
| 1 | IRT/BKT mastery scoring đang ở phase-1 | Chưa có calibration job với dữ liệu thực |
| 2 | Golden eval dataset kiểm tra hành vi expected | Chưa đo live model accuracy/latency |
| 3 | Route contract test suite có lỗi request hang | Service-level tests là regression signal chính |
| 4 | Nội dung học tập trung Computer Vision / Deep Learning | Chưa mở rộng nhiều domain |

### Hướng phát triển

| # | Kế hoạch | Giá trị |
|---|---|---|
| 1 | :chart_with_upwards_trend: Chạy IRT calibration với dữ liệu thực | Nâng cấp mastery scoring chính xác |
| 2 | :books: Thêm domain mới (NLP, Math, Programming) | Mở rộng phạm vi học tập |
| 3 | :mag: Mở rộng AI Agent tools (web search, doc retrieval) | Agent thông minh hơn |
| 4 | :test_tube: A/B testing prompt versions | Tối ưu chất lượng AI tutor |
| 5 | :chart_with_upwards_trend: Dashboard cho giáo viên | Theo dõi tiến độ lớp học |
| 6 | :iphone: Mobile app (React Native) | Hỗ trợ học trên điện thoại |

---

<details>
<summary><strong>:books: Technical Reference (click để mở)</strong></summary>

### Tài liệu kỹ thuật chi tiết

- [Production DB Integration Handoff](docs/PRODUCTION_DB_INTEGRATION_HANDOFF.md)
- [Schema Branch Snapshot](docs/SCHEMA_BRANCH_SNAPSHOT_2026-04-23.md)
- [Forgot Password + Resend Setup](docs/forgot-password-resend.md)
- [ECS Deployment Guide](deploy-ecs/README.md)

### Current Production Contract

The active runtime schema is canonical and course-first. Do not build new product logic on the old `modules`, `topics`, `questions`, `mastery_scores`, or `learning_paths` tables.

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

</details>

---

<div align="center">
  <sub>Built with :heart: by Team A20-App-049 | AI20K Build Phase 2026</sub>
</div>
