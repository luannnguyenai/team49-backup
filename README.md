<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/FastAPI-0.135+-009688?style=for-the-badge&logo=fastapi&logoColor=white"/>
  <img src="https://img.shields.io/badge/Next.js-14-000000?style=for-the-badge&logo=nextdotjs&logoColor=white"/>
  <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white"/>
  <img src="https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white"/>
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white"/>
</p>

<h1 align="center">AI Adaptive Learning Platform</h1>

<p align="center">
  Nền tảng học tập thích nghi kết hợp AI — cá nhân hóa lộ trình học, hỗ trợ hỏi đáp theo ngữ cảnh bài giảng (Video + Transcript + Slide) và đánh giá kiến thức tự động theo mô hình Bayesian Knowledge Tracing & IRT.
</p>

---

## Mục lục

- [Giới thiệu](#giới-thiệu)
- [Tính năng chính](#tính-năng-chính)
- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
- [Tech Stack](#tech-stack)
- [Cấu trúc dự án](#cấu-trúc-dự-án)
- [Cài đặt & Chạy](#cài-đặt--chạy)
  - [Docker (Khuyên dùng)](#docker-khuyên-dùng)
  - [Cài đặt thủ công](#cài-đặt-thủ-công)
- [Biến môi trường](#biến-môi-trường)
- [API Reference](#api-reference)
- [Thuật toán cốt lõi](#thuật-toán-cốt-lõi)
- [Troubleshooting](#troubleshooting)

---

## Giới thiệu

**A20-App-049** là nền tảng học tập thích nghi (adaptive learning) sử dụng AI để:

- **Cá nhân hóa lộ trình học** — Hệ thống tự động đề xuất thứ tự học dựa trên điểm mastery hiện tại, mức độ sẵn sàng và deadline mục tiêu của người học.
- **AI Tutor theo ngữ cảnh** — Đặt câu hỏi tại bất kỳ thời điểm nào trong video bài giảng, AI phân tích transcript + slide tại đúng frame đó và trả lời real-time.
- **Đánh giá kiến thức thông minh** — Hệ thống quiz/assessment 3 tầng (formative → summative → module gate), sử dụng mô hình IRT 2PL và Bloom's Taxonomy để đo lường năng lực chính xác.
- **Theo dõi tiến trình học tập** — Dashboard hiển thị Mastery Score, weak knowledge components, xu hướng điểm số và lịch sử tương tác.

Hiện tại, nội dung học tập tập trung vào khóa **CS231n — Deep Learning for Computer Vision** (Stanford) với 18 bài giảng, transcript, slide và ngân hàng câu hỏi đầy đủ.

---

## Tính năng chính

### AI Tutor (Q&A theo bài giảng)
- Xem video bài giảng, đặt câu hỏi tại bất kỳ timestamp nào
- AI truy xuất transcript + slide tại đúng thời điểm đó làm context
- Phân loại câu hỏi tự động: lý thuyết bài giảng / toán học / lập trình
- Thực thi code Python trong sandbox an toàn cho bài toán tính toán
- Streaming real-time với hỗ trợ LaTeX/KaTeX cho công thức toán
- Rating câu trả lời (👍/👎) để cải thiện chất lượng

### Hệ thống đánh giá 3 tầng

| Loại | Mục đích | Số câu | Cơ chế |
|------|----------|--------|--------|
| **Quiz** | Kiểm tra nhanh theo topic | 10 câu | EMA mastery update |
| **Assessment** | Đánh giá tổng quát | 5 câu/topic | IRT 2PL scoring |
| **Module Test** | Cổng kiểm tra năng lực | 5 câu/topic | Pass/Fail ≥ 70% |

### Lộ trình học thích nghi
- Topological sort theo dependency graph của topics
- Gán action dựa trên mastery: `skip` / `quick_review` / `standard_learn` / `deep_practice` / `remediate`
- Bin-packing timeline vào số giờ/tuần người học có thể dành
- Tự động hoàn thành learning path item khi mastery ≥ 76%

### Theo dõi tiến trình
- Checkpoint video: `unwatched` → `watched` (80%) → `quiz_completed`
- Lịch sử tất cả phiên học với breakdown từng câu hỏi
- Phân tích weak Knowledge Components và misconceptions
- Thống kê: tổng phiên, điểm trung bình, xu hướng cải thiện

---

## Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                         │
│                  Next.js 14 (App Router)                    │
│         Auth / Dashboard / Tutor / Learn / History          │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP / SSE (streaming)
┌──────────────────────────▼──────────────────────────────────┐
│                        API LAYER                            │
│              FastAPI (async) — port 8000                    │
│  /auth  /content  /quiz  /assessment  /learning-path  ...   │
└────────┬──────────────────┬───────────────────┬─────────────┘
         │                  │                   │
┌────────▼────────┐ ┌───────▼───────┐ ┌─────────▼─────────┐
│  SERVICE LAYER  │ │  AI/LLM LAYER │ │    DATA LAYER     │
│                 │ │               │ │                   │
│ QuizService     │ │ LangGraph     │ │ PostgreSQL 16     │
│ AssessmentSvc   │ │ Agent         │ │ (asyncpg/ORM)     │
│ MasteryEval     │ │               │ │                   │
│ RecommendEng    │ │ Tools:        │ │ Redis 7           │
│ TimelineBuilder │ │ - Transcript  │ │ (rate limiting)   │
│ HistoryService  │ │ - Slides      │ │                   │
│                 │ │ - Sandbox     │ │ data/CS231n/      │
└─────────────────┘ └───────────────┘ └───────────────────┘
```

### Luồng dữ liệu học tập

```
User xem video
      │
      ▼
Đặt câu hỏi tại timestamp T
      │
      ▼
LangGraph Agent:
  1. Retrieve transcript[T-30s : T+30s]
  2. Retrieve slides[T]
  3. Classify question type
  4. Answer with context (streaming)
      │
      ▼
User hoàn thành quiz/assessment
      │
      ▼
MasteryEvaluator (BKT + EMA)
      │
      ▼
RecommendationEngine update lộ trình
      │
      ▼
TimelineBuilder tính lịch tuần tiếp theo
```

---

## Tech Stack

### Backend
| Thành phần | Công nghệ | Phiên bản |
|-----------|-----------|-----------|
| Web Framework | FastAPI | 0.135+ |
| ORM | SQLAlchemy (async) | 2.0+ |
| DB Driver | asyncpg | latest |
| Validation | Pydantic | 2.12+ |
| Migrations | Alembic | latest |
| LLM Orchestration | LangChain + LangGraph | latest |
| LLM Providers | Google Gemini / OpenAI / Anthropic | — |
| Auth | python-jose + passlib[bcrypt] | latest |
| Package Manager | uv | latest |
| ML/Math | numpy, scipy, pandas, sympy | latest |

### Frontend
| Thành phần | Công nghệ | Phiên bản |
|-----------|-----------|-----------|
| Framework | Next.js (App Router) | 14 |
| Language | TypeScript | 5 |
| Styling | Tailwind CSS | 3.4 |
| State | Zustand | 4.5 |
| Forms | React Hook Form + Zod | 7.5 |
| HTTP | Axios | 1.7 |
| Markdown | react-markdown | latest |
| Dark Mode | next-themes | latest |

### Infrastructure
| Thành phần | Công nghệ |
|-----------|-----------|
| Database | PostgreSQL 16 |
| Cache / Rate-Limit | Redis 7 |
| Containerization | Docker + Docker Compose v2 |
| CI/CD | GitHub Actions |
| Linting | Ruff (Python), ESLint (TS) |

---

## Cấu trúc dự án

```
A20-App-049/
│
├── src/                          # Backend Python
│   ├── api/
│   │   └── app.py                # FastAPI entry point, route registration
│   ├── models/                   # SQLAlchemy ORM models
│   │   ├── user.py               # User account
│   │   ├── content.py            # Module, Topic, Question, KnowledgeComponent
│   │   └── learning.py           # Session, Interaction, MasteryScore, LearningPath
│   ├── routers/                  # Thin API route handlers
│   │   ├── auth.py               # /api/auth/*
│   │   ├── content.py            # /api/modules/*, /api/topics/*
│   │   ├── quiz.py               # /api/quiz/*
│   │   ├── assessment.py         # /api/assessment/*
│   │   ├── module_test.py        # /api/module-test/*
│   │   ├── learning_path.py      # /api/learning-path/*
│   │   └── history.py            # /api/history/*
│   ├── services/                 # Business logic
│   │   ├── llm_service.py        # LangGraph AI Tutor agent
│   │   ├── router.py             # Question type classifier
│   │   ├── sandbox.py            # Secure Python code execution
│   │   ├── quiz_service.py       # Quiz question selection & grading
│   │   ├── assessment_service.py # IRT 2PL scoring
│   │   ├── mastery_evaluator.py  # BKT + EMA mastery calculation
│   │   ├── recommendation_engine.py  # Learning path generation
│   │   ├── timeline_builder.py   # Weekly schedule bin-packing
│   │   └── history_service.py    # Session analytics
│   ├── schemas/                  # Pydantic request/response DTOs
│   ├── dependencies/
│   │   └── auth.py               # get_current_user() FastAPI dependency
│   ├── database.py               # Async SQLAlchemy engine + session
│   └── config.py                 # Pydantic Settings (env vars)
│
├── frontend/                     # Next.js 14 frontend
│   └── app/
│       ├── (auth)/               # Login, Register
│       ├── (protected)/          # Dashboard, Tutor, Learn, History, Profile
│       ├── quiz/                 # Quiz pages
│       ├── assessment/           # Assessment pages
│       ├── module-test/          # Module test pages
│       └── onboarding/           # Onboarding flow
│
├── scripts/
│   ├── seed.py                   # Seed curriculum (modules, topics, questions)
│   ├── seed_lectures.py          # Seed CS231n lectures từ JSON metadata
│   └── ingest_cs231n.py          # Ingest raw lecture data
│
├── alembic/                      # Database migration scripts
│   └── versions/
│       ├── 20260411_initial_schema.py
│       ├── 20260414_add_rating_to_qa_history.py
│       └── 20260415_add_checkpoint_state.py
│
├── data/                         # Lecture data (KHÔNG commit vào git)
│   ├── CS231n/
│   │   ├── videos/               # .mp4 bài giảng
│   │   ├── transcripts/          # .json transcript
│   │   ├── ToC_Summary/          # .json mục lục + tóm tắt
│   │   └── slides/               # .png slide
│   ├── modules.json
│   ├── topics.json
│   └── question_bank.json
│
├── prompts/                      # LLM prompt templates (versioned)
├── tests/                        # Pytest test suite
├── docs/                         # Documentation
│
├── Dockerfile                    # Backend container image
├── docker-compose.yml            # Dev stack (hot reload)
├── docker-compose.prod.yml       # Production overrides
├── Makefile                      # Common tasks shortcuts
├── pyproject.toml                # Python project config (uv, ruff, pytest)
├── .env.example                  # Environment variable template
└── alembic.ini                   # Alembic config
```

---

## Cài đặt & Chạy

### Yêu cầu hệ thống

- **Docker Desktop** ≥ 4.x và **Docker Compose v2** (khuyên dùng)
- Hoặc thủ công: Python 3.12+, Node.js 18+, PostgreSQL 16, Redis 7, [uv](https://docs.astral.sh/uv/)
- **API key** của ít nhất một LLM provider (Gemini, OpenAI, hoặc Anthropic)
- Thư mục dữ liệu `data/CS231n/` (tải từ Google Drive của nhóm)

---

### Docker (Khuyên dùng)

#### Bước 1 — Cấu hình môi trường

```bash
cp .env.example .env
```

Mở `.env` và điền các giá trị bắt buộc:

```env
# LLM — chọn ít nhất một
GEMINI_API_KEY=AIza...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Provider đang dùng
MODEL_PROVIDER=google_genai          # hoặc: openai, anthropic
DEFAULT_MODEL=gemini-2.0-flash

# Database
POSTGRES_PASSWORD=your_strong_db_password
DATABASE_URL=postgresql+asyncpg://postgres:your_strong_db_password@db:5432/ai_learning

# Redis
REDIS_PASSWORD=your_strong_redis_password
REDIS_URL=redis://:your_strong_redis_password@redis:6379/0

# JWT — tạo bằng: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your_32_char_random_secret_key
```

#### Bước 2 — Tải dữ liệu bài giảng CS231n

Tải thư mục `data/` từ Google Drive của nhóm và giải nén vào thư mục gốc:

```
data/
├── CS231n/
│   ├── videos/       # .mp4
│   ├── transcripts/  # .json
│   ├── ToC_Summary/  # .json
│   └── slides/       # .png
├── modules.json
├── topics.json
└── question_bank.json
```

> Nếu chưa có `data/`, backend vẫn khởi động — chỉ tính năng AI Tutor không có nội dung để truy vấn.

#### Bước 3 — Khởi chạy toàn bộ stack

```bash
docker compose up -d
```

> Lần đầu build image mất ~3-5 phút. Theo dõi:

```bash
docker compose logs -f backend   # xem log realtime
docker compose ps                 # kiểm tra trạng thái healthy
```

#### Bước 4 — Migrate và seed dữ liệu

Sau khi tất cả services `healthy`, chạy:

```bash
# Tạo schema database
docker compose exec backend uv run alembic upgrade head

# Seed chương trình học (modules, topics, questions)
docker compose exec backend uv run python scripts/seed.py

# Seed bài giảng CS231n (18 bài)
docker compose exec backend uv run python scripts/seed_lectures.py
```

> Các lệnh seed có thể chạy nhiều lần (idempotent).

#### Bước 5 — Truy cập ứng dụng

| URL | Mô tả |
|-----|-------|
| `http://localhost:3000` | Giao diện chính (Next.js) |
| `http://localhost:8000/docs` | Swagger API documentation |
| `http://localhost:8000/redoc` | ReDoc API documentation |
| `http://localhost:8000/health` | Health check endpoint |

#### Dừng dịch vụ

```bash
docker compose down        # dừng, giữ nguyên data volumes
docker compose down -v     # dừng + xóa toàn bộ data (reset hoàn toàn)
```

---

### Cài đặt thủ công

#### Backend

```bash
# Cài uv nếu chưa có
curl -LsSf https://astral.sh/uv/install.sh | sh

# Tạo virtualenv và cài dependencies
uv sync

# Cấu hình môi trường
cp .env.example .env
# Sửa .env với thông tin PostgreSQL, Redis, API keys đã cài local

# Chạy migrations
uv run alembic upgrade head

# Seed dữ liệu
uv run python scripts/seed.py
uv run python scripts/seed_lectures.py

# Khởi động server (development)
uv run python main.py
# hoặc: uv run uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend

```bash
cd frontend

# Cài dependencies
npm install

# Cấu hình API URL
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Dev server
npm run dev

# Production build
npm run build && npm start
```

---

### Makefile shortcuts

```bash
make dev           # Khởi động dev stack (hot reload)
make dev-build     # Rebuild images rồi start
make down          # Dừng containers
make migrate       # Chạy database migrations
make seed          # Seed toàn bộ curriculum data
make test          # Chạy test suite
make logs          # Tail logs tất cả services
make shell-be      # Shell vào backend container
make db-shell      # Mở psql trong database container
```

---

## Biến môi trường

### Bắt buộc

| Biến | Mô tả |
|------|-------|
| `GEMINI_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | API key của LLM provider |
| `MODEL_PROVIDER` | Provider đang dùng: `google_genai`, `openai`, `anthropic` |
| `DATABASE_URL` | PostgreSQL connection string (asyncpg) |
| `POSTGRES_PASSWORD` | Mật khẩu PostgreSQL |
| `REDIS_URL` | Redis connection string |
| `REDIS_PASSWORD` | Mật khẩu Redis |
| `SECRET_KEY` | Secret key 32 ký tự cho JWT signing |

### Tùy chọn (có giá trị mặc định)

| Biến | Mặc định | Mô tả |
|------|----------|-------|
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Thời hạn access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Thời hạn refresh token |
| `RATE_LIMIT_LOGIN_PER_MINUTE` | `5` | Giới hạn login attempts/IP/phút |
| `DB_POOL_SIZE` | `10` | SQLAlchemy connection pool size |
| `DB_MAX_OVERFLOW` | `20` | Max overflow connections |
| `DEFAULT_MODEL` | `gemini-2.0-flash` | Model mặc định cho AI Tutor |
| `LOG_LEVEL` | `INFO` | Log level (DEBUG/INFO/WARNING/ERROR) |
| `BACKEND_PORT` | `8000` | Backend server port |
| `FRONTEND_PORT` | `3000` | Frontend server port |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend URL từ phía frontend |

---

## API Reference

### Authentication

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/api/auth/register` | Đăng ký tài khoản mới |
| `POST` | `/api/auth/login` | Đăng nhập, nhận JWT tokens |
| `POST` | `/api/auth/refresh` | Refresh access token hết hạn |
| `GET` | `/api/users/me` | Lấy thông tin user hiện tại |
| `PUT` | `/api/users/me/onboarding` | Cập nhật onboarding preferences |

### Content & Curriculum

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `GET` | `/api/modules` | Danh sách tất cả modules |
| `GET` | `/api/modules/{id}` | Chi tiết module + danh sách topics |
| `GET` | `/api/topics/{id}` | Chi tiết topic + prerequisite graph |
| `GET` | `/api/topics/{id}/content` | Tài liệu học (markdown + videos) |

### AI Tutor (Lecture Q&A)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `GET` | `/api/lectures` | Danh sách bài giảng |
| `GET` | `/api/lectures/{id}/toc` | Mục lục bài giảng (chapters + timestamps) |
| `POST` | `/api/lectures/ask` | Đặt câu hỏi tại timestamp — **streaming SSE** |
| `GET` | `/api/lectures/qa-history` | Lịch sử Q&A |
| `POST` | `/api/history/{qa_id}/rate` | Đánh giá câu trả lời (👍/👎) |

### Quiz (Formative Assessment)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/api/quiz/start` | Bắt đầu quiz session |
| `POST` | `/api/quiz/{session_id}/answer` | Trả lời câu hỏi đơn lẻ |
| `POST` | `/api/quiz/{session_id}/complete` | Hoàn thành quiz + tính mastery |
| `GET` | `/api/quiz/history` | Lịch sử các quiz đã làm |

### Assessment (Summative)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/api/assessment/start` | Bắt đầu assessment |
| `POST` | `/api/assessment/{session_id}/submit` | Nộp tất cả câu trả lời |
| `GET` | `/api/assessment/{session_id}/results` | Kết quả assessment |

### Module Test (Proficiency Gate)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/api/module-test/start` | Bắt đầu module test |
| `POST` | `/api/module-test/{session_id}/submit` | Nộp bài + chấm điểm |
| `GET` | `/api/module-test/{session_id}/results` | Kết quả + remediation plan |

### Learning Path

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/api/learning-path/generate` | Tạo lộ trình học cá nhân hóa |
| `GET` | `/api/learning-path` | Lấy lộ trình hiện tại |
| `GET` | `/api/learning-path/timeline` | Lịch học theo tuần |
| `PUT` | `/api/learning-path/{id}/status` | Cập nhật trạng thái item |

### History & Analytics

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `GET` | `/api/history` | Lịch sử phiên học (có phân trang + filter) |
| `GET` | `/api/history/{session_id}/detail` | Chi tiết từng câu hỏi trong phiên |

---

## Thuật toán cốt lõi

### Mastery Scoring

**EMA (Exponential Moving Average)** — dùng trong Quiz:
```
new_mastery = old_mastery × 0.3 + quiz_score × 0.7
```

**Bloom-Weighted Scoring** — dùng trong Assessment:
```
score = Σ (bloom_weight[i] × correct[i]) / Σ bloom_weight[i]

Trọng số: remember=1, understand=2, apply=3, analyze=4
```

**IRT 2PL (2-Parameter Logistic)** — chọn câu hỏi phù hợp:
```
P(θ | a, b) = 1 / (1 + exp(-a × (θ - b)))

θ = ability estimate, a = discrimination, b = difficulty threshold
```

### Mastery Levels

| Level | Điểm | Ý nghĩa |
|-------|------|---------|
| `not_started` | 0% | Chưa bắt đầu |
| `novice` | 1–39% | Mới tiếp cận |
| `developing` | 40–59% | Đang phát triển |
| `proficient` | 60–75% | Khá thành thạo |
| `mastered` | 76–100% | Thành thạo |

### Learning Path Actions

| Action | Điều kiện | Thời gian ước tính |
|--------|-----------|-------------------|
| `skip` | mastery ≥ 90% | 0 giờ |
| `quick_review` | mastery 76–89% | 0.5× estimated_hours |
| `standard_learn` | mastery 50–75% | 1× estimated_hours |
| `deep_practice` | mastery < 50% | 1.5× estimated_hours |
| `remediate` | failed module test | 2× estimated_hours |

---

## Troubleshooting

| Vấn đề | Nguyên nhân | Giải pháp |
|--------|-------------|-----------|
| Backend không start | Thiếu API key | Kiểm tra `GEMINI_API_KEY` trong `.env` |
| `Cannot connect to database` | PostgreSQL chưa ready | Chờ thêm 30s, kiểm tra `docker compose ps`, chạy lại migration |
| Frontend báo API lỗi | Backend chưa chạy | `curl http://localhost:8000/health` để kiểm tra |
| Port đã bị chiếm | Conflict với service khác | Đổi `BACKEND_PORT`/`FRONTEND_PORT` trong `.env` |
| Lỗi migration | Schema đã tồn tại | Chạy `docker compose down -v` rồi khởi động lại |
| AI Tutor không có nội dung | Thiếu data CS231n | Tải `data/` từ Google Drive nhóm và chạy `seed_lectures.py` |
| Lỗi `image not found` (Mac M1/M2) | Architecture mismatch | Thêm `platform: linux/amd64` vào service trong `docker-compose.yml` |
| Streaming AI bị ngắt | Timeout nginx/proxy | Tăng `proxy_read_timeout` hoặc dùng kết nối trực tiếp |

---

## Liên hệ & Đóng góp

Dự án được phát triển bởi nhóm **A20 — AI Thực Chiến**.

Để báo lỗi hoặc đề xuất tính năng, vui lòng tạo issue trên GitHub repository.
