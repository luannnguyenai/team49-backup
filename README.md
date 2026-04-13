# AI Adaptive Learning Platform

Nền tảng học tập thích nghi kết hợp AI để cá nhân hóa lộ trình học, hỗ trợ hỏi đáp đa phương thức theo ngữ cảnh bài giảng (Video + Transcript + Slide), và đánh giá kiến thức tự động.

---

## Tổng quan kiến trúc

| Thành phần | Công nghệ | Cổng |
|---|---|---|
| Backend API | FastAPI + SQLAlchemy (asyncpg) | `8000` |
| Frontend | Next.js 14 (App Router) | `3000` |
| Database | PostgreSQL 16 | `5432` |
| Cache / Rate-limit | Redis 7 | `6379` |

---

## Yêu cầu trước khi chạy

- **Docker Desktop** (≥ 4.x) và **Docker Compose v2**
- **GEMINI_API_KEY** — bắt buộc để các tính năng AI hoạt động
- (Tuỳ chọn) `ANTHROPIC_API_KEY` hoặc `OPENAI_API_KEY` nếu dùng provider khác
- Thư mục dữ liệu bài giảng `data/CS231n/` (xem hướng dẫn bên dưới)

---

## Chạy demo nhanh với Docker (Khuyên dùng)

### Bước 1 — Cấu hình môi trường

```bash
cp .env.example .env
```

Mở `.env` và điền giá trị thực:

```env
# Bắt buộc
GEMINI_API_KEY=AIza...

# Đặt mật khẩu ngẫu nhiên cho DB/Redis
POSTGRES_PASSWORD=your_strong_db_password
REDIS_PASSWORD=your_strong_redis_password
DATABASE_URL=postgresql+asyncpg://postgres:your_strong_db_password@localhost:5432/ai_learning
REDIS_URL=redis://:your_strong_redis_password@localhost:6379/0

# Bảo mật JWT (tạo bằng: python -c "import secrets; print(secrets.token_hex(32))")
SECRET_KEY=your_32_char_random_secret
```

> Các biến còn lại trong `.env.example` có giá trị mặc định hợp lý, không cần thay đổi để chạy demo.

### Bước 2 — Tải dữ liệu bài giảng CS231n

Tải thư mục `data/` từ Google Drive của nhóm và giải nén vào thư mục gốc của dự án. Cấu trúc cần có:

```
data/
├── CS231n/
│   ├── videos/          # File .mp4 mỗi bài giảng
│   ├── transcripts/     # File .json transcript
│   ├── ToC_Summary/     # File .json mục lục + tóm tắt
│   └── slides/          # File .png slide (tuỳ chọn)
├── modules.json
├── topics.json
└── question_bank.json
```

> Nếu chưa có thư mục `data/`, backend vẫn khởi động nhưng tính năng AI Tutor sẽ không có bài giảng để truy vấn.

### Bước 3 — Khởi chạy tất cả dịch vụ

```bash
docker compose up -d
```

Lần đầu sẽ build image (~3-5 phút). Theo dõi trạng thái:

```bash
docker compose logs -f backend   # xem log backend
docker compose ps                 # kiểm tra health
```

Chờ đến khi tất cả dịch vụ có trạng thái `healthy`.

### Bước 4 — Chạy migrations và seed dữ liệu

Mở terminal khác và chạy lần lượt:

```bash
# 1. Chạy Alembic migration (tạo bảng)
docker compose exec backend uv run alembic upgrade head

# 2. Seed chương trình học (modules, topics, questions)
docker compose exec backend uv run python scripts/seed.py

# 3. Seed bài giảng CS231n (18 bài)
docker compose exec backend uv run python scripts/seed_lectures.py
```

> Các lệnh seed có thể chạy nhiều lần (idempotent — không tạo dữ liệu trùng).

### Bước 5 — Truy cập ứng dụng

| URL | Mô tả |
|---|---|
| `http://localhost:3000` | Giao diện chính (Next.js) |
| `http://localhost:8000/docs` | Swagger API docs |
| `http://localhost:8000/health` | Health check backend |

---

## Hướng dẫn sử dụng tính năng chính

### Đăng ký / Đăng nhập
Truy cập `http://localhost:3000` → Tạo tài khoản mới → Hoàn thành onboarding.

### AI Tutor (`/tutor`)
- Chọn bài giảng CS231n từ danh sách
- Phát video đến thời điểm muốn hỏi
- Đặt câu hỏi — AI sẽ phân tích frame video + transcript + slide tại thời điểm đó
- Hỗ trợ streaming real-time, LaTeX/KaTeX cho công thức toán học

### Học tập thích nghi (`/learn`)
- Học theo module và topic
- Hệ thống theo dõi điểm Mastery Score (BKT algorithm)

### Kiểm tra kiến thức
- `/quiz` — Quiz ngắn theo topic
- `/assessment` — Kiểm tra toàn diện
- `/module-test` — Kiểm tra cuối module

### Lịch sử học (`/history`)
Xem lại toàn bộ tiến trình, câu hỏi đã hỏi và kết quả kiểm tra.

---

## Cài đặt thủ công (không dùng Docker)

Yêu cầu: Python 3.12+, Node.js 18+, PostgreSQL 16, Redis 7, [uv](https://docs.astral.sh/uv/)

### Backend

```bash
# Cài dependencies
uv sync

# Chạy migrations
uv run alembic upgrade head

# Seed dữ liệu
uv run python scripts/seed.py
uv run python scripts/seed_lectures.py

# Khởi động backend
uv run python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --workers 2
```

### Frontend

```bash
cd frontend
cp .env.example .env.local    # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev                    # dev server tại :3000
# hoặc: npm run build && npm start
```

---

## Cấu trúc dự án

```
.
├── src/
│   ├── api/            # FastAPI routes, app entry point
│   ├── models/         # SQLAlchemy ORM models
│   ├── services/       # Business logic (AI, quiz, learning path...)
│   └── config.py       # Pydantic settings
├── frontend/           # Next.js 14 App Router
│   └── app/
│       ├── (auth)/     # Login, Register
│       ├── (protected)/# Dashboard, Tutor, Learn, History, Profile
│       ├── quiz/
│       ├── assessment/
│       └── module-test/
├── scripts/
│   ├── seed.py             # Seed curriculum (modules, topics, questions)
│   ├── seed_lectures.py    # Seed CS231n lectures
│   └── ingest_cs231n.py    # Ingest raw lecture data
├── alembic/            # DB migration files
├── data/               # Lecture videos, transcripts, ToC (không commit)
├── docker-compose.yml
├── Dockerfile
└── .env.example
```

---

## Dừng dịch vụ

```bash
docker compose down          # dừng, giữ data volumes
docker compose down -v       # dừng + xoá toàn bộ data (reset hoàn toàn)
```

---

## Troubleshooting

| Vấn đề | Giải pháp |
|---|---|
| Backend không start | Kiểm tra `GEMINI_API_KEY` đã đặt trong `.env` |
| `Cannot connect to database` | Chờ thêm 30s cho PostgreSQL healthy, rồi chạy lại migration |
| Frontend báo API lỗi | Đảm bảo backend đang chạy: `curl http://localhost:8000/health` |
| Port đã bị chiếm | Đổi `BACKEND_PORT` / `FRONTEND_PORT` trong `.env` |
| Lỗi `image not found` (Mac M1/M2) | Thêm `platform: linux/amd64` vào service trong `docker-compose.yml` |
