<div align="center">
  <img src="./heroimage.png" alt="VinLearn - AI Adaptive Learning Platform" width="800"/>

  # VinLearn

  > *"Học đúng thứ bạn yếu, với lộ trình riêng cho bạn — có AI hướng dẫn 24/7"*

  **AI Adaptive Learning Platform — cá nhân hóa lộ trình học cho từng học sinh dựa trên năng lực thực tế.**

  [![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
  [![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
  [![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
  [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
  [![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
  [![LangGraph](https://img.shields.io/badge/LangChain-LangGraph-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://www.langchain.com/)
  [![AWS](https://img.shields.io/badge/AWS-ECS%2FFargate-FF9900?style=for-the-badge&logo=amazonecs&logoColor=white)](https://aws.amazon.com/ecs/)
  [![Terraform](https://img.shields.io/badge/Terraform-IaC-844FBA?style=for-the-badge&logo=terraform&logoColor=white)](https://www.terraform.io/)

  [**🚀 Live Demo**](https://a20-app-049.io.vn) · [**🎬 Video Demo**](https://drive.google.com/file/d/1q0Ce-3aJcJJFBfBRygGXvCH3ofkhUoIW/view?usp=sharing) · [**📑 Pitch Deck**](VinLearn-Pitch.pdf) · [**📐 Architecture**](architecture/) · [**📄 Technical Report**](TECHNICAL_REPORT.md) · [**🤖 AI Logs**](docs/ai-logs.md) · [**📊 Evaluation**](docs/evaluation-report.md) · [**📝 Worklog**](docs/WORKLOG.md)

</div>

---

## 1. Giới thiệu

**VinLearn** là nền tảng học tập thích ứng sử dụng AI, kết hợp learning path cá nhân hóa, AI Tutor theo ngữ cảnh, quiz thông minh và AI Assistant để biến mỗi tương tác thành tín hiệu giúp hệ thống ngày càng hiểu và đồng hành tốt hơn với người học.

Sản phẩm hướng tới học sinh từ cấp 2 đến đại học, đặc biệt những bạn tự học qua tài liệu online mà thiếu lộ trình rõ ràng và không có người hướng dẫn thường xuyên.

---

## 2. Vấn đề

| Vấn đề | Hệ quả |
|---|---|
| Không biết mình yếu ở đâu | Học lan man, không tập trung đúng chỗ |
| Nội dung không phù hợp level | Học quá dễ hoặc quá khó, mất thời gian |
| Không có feedback tức thì | Làm bài xong không biết đúng sai, không hiểu tại sao |
| Không có người hướng dẫn 24/7 | Muốn hỏi lúc nào cũng phải tự tìm |

---

## 3. Giải pháp — Adaptive Learning Loop

Học sinh trải qua vòng lặp thích ứng khép kín: **Onboarding → Placement Assessment → Personalized Path → Learn → Mastery Update → lặp lại.**

| Bước | Mô tả |
|---|---|
| **1. Diagnostic Assessment** | Quiz xác định level và điểm yếu theo từng Knowledge Point |
| **2. Personalized Path** | Planner đề xuất nội dung dựa trên mastery, prerequisite graph và mục tiêu |
| **3. Learn + Instant Feedback** | Học bài, làm quiz, nhận giải thích ngay lập tức từ AI Tutor |
| **4. Mastery Update** | Hệ thống cập nhật điểm mastery theo KP và điều chỉnh lộ trình |

![Onboarding & Assessment Flow](architecture/06-onboarding-assesment.svg)

---

## 4. Tính năng chính

| Tính năng | Mô tả | AI |
|---|---|:---:|
| **Onboarding & Placement** | Đánh giá đầu vào để xác định level và chọn mục tiêu học | ✅ |
| **Adaptive Learning Path** | Lộ trình cá nhân hóa dựa trên KP mastery và prerequisite graph | ✅ |
| **AI Tutor 24/7** | Gia sư AI hỗ trợ giải đáp trong ngữ cảnh bài giảng, chạy code Python sandbox | ✅ |
| **Quiz & Assessment** | Mini quiz, module test, placement test với feedback tức thì | ✅ |
| **Mastery Tracking** | Theo dõi tiến độ theo từng Knowledge Point với IRT scoring | |
| **Guardrail & Safety** | Smart Router phân loại intent, Guardrail Router chặn prompt injection | ✅ |
| **Video Learning** | Xem bài giảng video với progress tracking và inline quiz | |
| **Lecture Q&A** | Hỏi đáp trong context bài giảng, AI trả lời dựa trên transcript + slides | ✅ |

### AI Tutor Overlay

Khi học sinh hover hoặc dừng trên một đoạn nội dung, AI Tutor chủ động gợi ý giải thích. Học sinh có thể hỏi, nhận câu trả lời có trích dẫn, và báo lỗi để cải thiện RAG.

![AI Tutor UX Flow](architecture/07-ai-tutor.svg)

---

## 5. Kiến trúc hệ thống

Hệ thống được chia thành 7 lớp: **Client → CDN/Edge → Application → AI Agent Stack → Data → Observability → CI/CD**, triển khai trên AWS ECS Fargate với Terraform IaC.

![System Overview](architecture/01-system-overview.svg)

| Sơ đồ | Mô tả |
|---|---|
| [01 — System Overview](architecture/01-system-overview.drawio) | Tổng quan 7 lớp: Client, CDN/Edge, Application, AI Stack, Data, Observability, CI/CD |
| [02 — Agentic RAG Pipeline](architecture/02-agentic-rag-pipeline.drawio) | PII → Guardrail → Smart Router → LangGraph → Answer Generator |
| [03 — AWS Infrastructure](architecture/03-aws-infrastructure.drawio) | VPC, ECS Fargate, RDS, ElastiCache, ECR, S3 + CloudFront, CI/CD |
| [04 — Request Lifecycle](architecture/04-request-lifecycle.drawio) | Flow 1: SSR page load · Flow 2: AI Tutor chat |
| [05 — Data Schema](architecture/05-data-schema.drawio) | 4 lớp DB: Product Shell, Canonical Content, Learner State, Agent State |
| [07 — Assessment Flow](architecture/07-assessment-flow.drawio) | 3 phase: Goal Discovery → Placement Test → SKIP / REVIEW / RELEARN |

---

## 6. AI Pipeline & Fine-tuned Models

Mọi câu hỏi từ học sinh đi qua pipeline: **PII Sanitizer → Guardrail Router → Smart Router → LangGraph Agent (ReAct + RAG tools) → Answer Generator → SSE stream về browser.**

![Agentic RAG Pipeline](architecture/02-agentic-rag-pipeline.svg)

### Guardrail Router — Qwen3.5-0.8B LoRA

| Hạng mục | Chi tiết |
|---|---|
| Base model | Qwen3.5-0.8B |
| Phương pháp | LoRA fine-tune (Unsloth) |
| Mục đích | Phân loại safety / topic / action cho mọi user message trước khi vào AI Tutor |
| Output | JSON: `safety_label`, `topic_label`, `action`, `attack_type`, `selected_kp_ids` |
| Dataset | 13,513 samples (EduVidQA, WildGuardMix, JailBreakV-28K, MultiJail, CLINC150, internal) |
| Kết quả | `valid_json_rate=1.0` · `harmful_false_allow_rate=0.0` · `ambiguous_recall=0.9905` |
| Serving | vLLM trên Cloudflare Tunnel, fallback Gemini / OpenAI |
| VRAM | ~1.5 GB peak (RTX 3050 Laptop) |

### Tutor Answer Generator — Qwen3.5-4B LoRA

| Hạng mục | Chi tiết |
|---|---|
| Base model | Qwen3.5-4B |
| Phương pháp | LoRA fine-tune (Unsloth) |
| Mục đích | Sinh câu trả lời cho AI Tutor trong ngữ cảnh bài giảng |
| Đặc điểm | Multilingual (Vi / En), lecture-grounded, không hallucinate ngoài context |
| Serving | vLLM (OpenAI-compatible API) |

### Prerequisite Edge Scoring — DeBERTa / ModernBERT / SciBERT

Xây dựng **prerequisite graph** (quan hệ tiên quyết giữa các Knowledge Point) bằng multi-model scoring:

| Model | Vai trò | Phương pháp |
|---|---|---|
| DeBERTa-v3-large-MNLI | Chấm chiều prerequisite A→B vs B→A | Zero-shot NLI |
| ModernBERT-base | Chấm edge strength qua anchor embedding | Anchor embedding contrast |
| SciBERT | Scoring cho domain khoa học | Masked edge scoring |
| DeBERTa + MoocCubeX | Prerequisite classification | Fine-tune trên MoocCubeX |

**Pipeline:** Raw KP pairs → Multi-model scoring → GPT adjudication → Transitive pruning → PostgreSQL (`prerequisite_edges`).

### Data Flywheel — Continuous Improvement

Mỗi tương tác của học sinh (hiểu / hỏi lại / báo lỗi) được thu thập và phân tích hàng tuần để cải thiện RAG index, prompt và ngưỡng proactive suggestion.

![Data Flywheel](architecture/08-data-flywheel.svg)

---

## 7. Công nghệ

| Thành phần | Công nghệ |
|---|---|
| Frontend | Next.js 14 App Router, React 18, TypeScript 5, Zustand, Tailwind CSS |
| Backend / API | Python 3.12, FastAPI, SQLAlchemy async, Pydantic v2, Alembic |
| Database | PostgreSQL 16 + pgvector, Redis 7 |
| AI Agent | LangChain, LangGraph, Gemini / OpenAI / Anthropic |
| Fine-tuned Models | Qwen3.5-0.8B LoRA (Guardrail), Qwen3.5-4B LoRA (Tutor), DeBERTa / ModernBERT / SciBERT |
| Model Serving | vLLM, Unsloth, DVC |
| Observability | Langfuse, Prometheus, Grafana, Loki |
| Deployment | Docker Compose, AWS ECS / Fargate, Terraform |

---

## 8. Cài đặt và chạy local

### Yêu cầu

- Docker Desktop với Docker Compose v2, hoặc Python 3.12 + Node.js 18+ + PostgreSQL 16 + Redis 7 + `uv`
- Ít nhất 1 LLM API key (Gemini, OpenAI, hoặc Anthropic)

### Docker (khuyến nghị)

```bash
git clone https://github.com/a20-ai-thuc-chien/A20-App-049.git
cd A20-App-049
cp .env.example .env          # điền API keys

docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -m src.scripts.pipeline.import_canonical_artifacts_to_db
docker compose exec backend python -m src.scripts.pipeline.import_product_shell_to_db
```

### Chạy trực tiếp

```bash
# Backend
uv sync && cp .env.example .env
uv run alembic upgrade head
uv run python -m src.scripts.pipeline.import_canonical_artifacts_to_db
uv run python -m src.scripts.pipeline.import_product_shell_to_db
uv run python main.py

# Frontend
cd frontend && npm install
printf "NEXT_PUBLIC_API_URL=http://localhost:8000\n" > .env.local
npm run dev
```

| URL | Mô tả |
|---|---|
| `http://localhost:3000` | Frontend |
| `http://localhost:8000/docs` | Swagger API docs |
| `http://localhost:8000/health` | Health check |

---

## 9. Biến môi trường

> **Không commit `.env`.** Chỉ commit `.env.example`.

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5433/ai_learning
REDIS_URL=redis://:password@localhost:6379/0
SECRET_KEY=replace-with-random-secret
MODEL_PROVIDER=google_genai
DEFAULT_MODEL=gemini-2.0-flash
GEMINI_API_KEY=...
```

---

## 10. Cách sử dụng

| Bước | Hành động | Mô tả |
|:---:|---|---|
| 1 | Đăng ký / Đăng nhập | Tạo tài khoản hoặc đăng nhập |
| 2 | Onboarding | Chọn mục tiêu học: Deep Learning, Computer Vision, NLP |
| 3 | Placement Assessment | Làm bài đánh giá đầu vào để xác định level |
| 4 | Xem lộ trình | Hệ thống đề xuất lộ trình cá nhân hóa |
| 5 | Học bài | Xem video, đọc nội dung, hỏi AI Tutor bất cứ lúc nào |
| 6 | Làm quiz | Mini quiz sau mỗi bài học |
| 7 | Xem feedback | Nhận giải thích chi tiết cho từng câu trả lời |
| 8 | Lộ trình tự cập nhật | Hệ thống điều chỉnh dựa trên kết quả mới |

**Tài khoản demo:** `demo@vinuni.edu.vn` / `DemoPass123!`

---

## 11. Demo & Kết quả

| Hạng mục | Link |
|---|---|
| Live URL | [https://a20-app-049.io.vn](https://a20-app-049.io.vn) |
| Video Demo | [Google Drive](https://drive.google.com/file/d/1q0Ce-3aJcJJFBfBRygGXvCH3ofkhUoIW/view?usp=sharing) |
| Pitch Deck | [VinLearn-Pitch.pdf](VinLearn-Pitch.pdf) |
| Evaluation Report | [docs/evaluation-report.md](docs/evaluation-report.md) |
| AI Logs | [docs/ai-logs.md](docs/ai-logs.md) |
| Golden Eval Dataset | [docs/agent-golden-evals.md](docs/agent-golden-evals.md) |

---

## 12. Team

| Thành viên | Vai trò | Công việc chính |
|---|---|---|
| **Nguyễn Duy Minh Hoàng** | AI/ML Lead | LangGraph ReAct Agent, Agentic RAG pipeline (deeptutor-style), Qwen3.5 LoRA fine-tuning (Guardrail + Tutor), Smart Router, SSE streaming, RoadmapPlanner, Replan feature E2E (frontend → backend), Guardrail Router (multilayer + Lingua language normalization), External research mode (Semantic Scholar API + web search), Langfuse observability (trace ID propagation, span tagging), DVC transcript tracking |
| **Nguyễn Đôn Đức** | Full-stack & DevOps Lead | Frontend UI/UX (design system, i18n 50+ components, tutor hub, admin dashboard, landing page, auth pages), Backend (DB foundation, repository layer, Redis auth, PII guardrail), AWS ECS/Fargate + Terraform, CI/CD (GitHub Actions), Observability (Prometheus/Grafana/Loki) |
| **Nguyễn Lê Minh Luân** | Frontend, UI/UX & Assessment Lead | UI/UX design (landing page, onboarding flow), Onboarding UX redesign (5-step flow: StepGoalSelection, StepKnownTopicsFiltered, StepPlacementTest, ResultGate, frontend store + placement API layer), Placement assessment backend (IRT/CAT, IRTAdaptiveStrategy 3PL-lite CAT, placement router start/submit/results/topic-decision), KG full implementation (kg_concepts, kg_edges, bridges, recommendation engine), Recommendation engine Phase A/B, Redis resilience |

---

## 13. Hạn chế & Hướng phát triển

| # | Hạn chế hiện tại |
|---|---|
| 1 | IRT/BKT mastery scoring đang ở phase-1, chưa có calibration với dữ liệu thực |
| 2 | Nội dung tập trung Computer Vision / Deep Learning, chưa mở rộng nhiều domain |
| 3 | Chưa đo live model accuracy / latency trên production traffic |

| # | Kế hoạch |
|---|---|
| 1 | Chạy IRT calibration với dữ liệu thực — nâng cấp mastery scoring |
| 2 | Thêm domain mới (NLP, Math, Programming) |
| 3 | Mở rộng AI Agent tools (web search, doc retrieval) |
| 4 | A/B testing prompt versions |
| 5 | Dashboard cho giáo viên theo dõi tiến độ lớp học |
| 6 | Mobile app (React Native) |

---

<details>
<summary><strong>Technical Reference</strong></summary>

### Repository Layout

```text
src/
  api/app.py                          FastAPI app registration
  models/                             SQLAlchemy models
  repositories/                       DB access helpers
  routers/                            API endpoints
  services/                           Runtime business logic
  scripts/pipeline/                   Canonical export / import / parity tooling
frontend/
  app/                                Next.js pages / routes
  components/                         React components
  lib/                                API clients and frontend mappers
data/
  courses/                            Course assets, transcripts, slides, videos
  final_artifacts/*/canonical/         Generated canonical JSONL import bundles
docs/                                 Documentation, journals, evaluation
alembic/                              Database migrations
deploy-ecs/                           AWS ECS deployment (Terraform, task defs, observability)
architecture/                         Architecture diagrams (.drawio, .svg)
```

### Database Schema (Active Tables)

| Layer | Tables | Purpose |
|---|---|---|
| Product Shell | `courses`, `course_sections`, `learning_units`, `course_assets` | User-facing course catalog |
| Canonical Content | `concepts_kp`, `question_bank`, `item_calibration`, `prerequisite_edges` | KP graph, question bank |
| Learner State | `learner_mastery_kp`, `goal_preferences`, `waived_units`, `plan_history` | Mastery, progress, planner |
| Agent State | `agent_graph_runs`, `agent_response_payloads`, `agent_route_context` | AI conversation state |

### API Surface

| Area | Endpoints |
|---|---|
| Auth / Onboarding | `/api/auth/*`, `/api/users/me/onboarding` |
| Content | `/api/course-sections`, `/api/learning-units/{id}/content` |
| Quiz | `/api/quiz/start`, `/api/quiz/{id}/answer`, `/api/quiz/{id}/complete` |
| Assessment | `/api/assessment/start`, `/api/assessment/{id}/submit`, `/api/assessment/{id}/results` |
| Learning Path | `/api/learning-path/generate`, `/api/learning-path` |
| AI Tutor | `/api/lectures/ask`, `/api/lectures/{qa_id}/rate` |

### Validation

```bash
uv run python -m src.scripts.pipeline.import_canonical_artifacts_to_db --validate-only
uv run python -m src.scripts.pipeline.check_canonical_runtime_parity
uv run pytest tests/ -q
npm --prefix frontend run type-check
```

### Troubleshooting

| Problem | Fix |
|---|---|
| Content is empty | Run canonical + product shell importers |
| Quiz has no questions | Validate canonical artifacts (item_phase_map, item_kp_map) |
| Planner looks flat | Check `prerequisite_edges`, `unit_kp_map` |
| Tutor can't answer | Restore course assets, run `seed_lectures` |
| No Langfuse traces | Fill root `.env`, restart backend |

### Knowledge Graph — Prerequisite Edge Visualization

Prerequisite graph được build từ multi-model scoring pipeline. Hai biểu đồ dưới đây là output của phase audit (tất cả edges được đề xuất) và phase kept-only (sau transitive pruning).

<details>
<summary>kg_p5_audit.svg — tất cả edges được đề xuất</summary>

![KG Audit](data/final_artifacts/cs224n_cs231n_cs230_v1/kg_visualizations/kg_p5_audit.svg)

</details>

<details>
<summary>kg_p5_kept_only.svg — edges sau transitive pruning</summary>

![KG Kept Only](data/final_artifacts/cs224n_cs231n_cs230_v1/kg_visualizations/kg_p5_kept_only.svg)

</details>

</details>

---

<div align="center">
  <sub>Built with ❤️ by Team A20-App-049 · AI20K Build Phase 2026</sub>
</div>
