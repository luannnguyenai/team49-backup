# Refactor Plan — A20-App-049

> Mục tiêu: dọn sạch tech debt trước khi phát triển tính năng mới.
> Thứ tự ưu tiên: bảo mật → kiến trúc → hiệu năng → cosmetic.

---

## Phase 1 — Quick Wins (< 30 phút tổng)

Các thay đổi nhỏ, độc lập, không rủi ro — làm ngay.

### 1.1 Fix Dockerfile CMD

**File:** `Dockerfile`

`CMD` hiện tại gọi `python src/api/app.py` nhưng file đó không có `__main__` block nữa — container sẽ import rồi thoát ngay. Thực tế `docker-compose.yml` override bằng `command:` riêng nên không ảnh hưởng production, nhưng `Dockerfile` standalone sẽ broken.

```dockerfile
# Trước
CMD ["uv", "run", "python", "src/api/app.py"]

# Sau
CMD ["uv", "run", "python", "-m", "uvicorn", "src.api.app:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

---

### 1.2 Xóa `LOG_LEVEL` trùng trong `.env`

**File:** `.env` (line 70 — duplicate của line 42)

Xóa dòng thứ hai.

---

### 1.3 Làm sạch `config.py` aliases

**File:** `src/config.py` (lines 52–59)

Hiện tại có các module-level alias:
```python
ANTHROPIC_API_KEY = settings.anthropic_api_key
OPENAI_API_KEY    = settings.openai_api_key
GEMINI_API_KEY    = settings.gemini_api_key
DEFAULT_MODEL     = settings.default_model
FAST_MODEL        = settings.fast_model
MODEL_PROVIDER    = settings.model_provider
LOG_LEVEL         = settings.log_level
```

`DEFAULT_MODEL`, `FAST_MODEL`, `MODEL_PROVIDER` đang được dùng trong `llm_service.py` và `router.py`. Giữ lại 3 cái này. Xóa `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `LOG_LEVEL` (không có file nào import).

**Kiểm tra trước khi xóa:**
```bash
grep -r "ANTHROPIC_API_KEY\|OPENAI_API_KEY\|GEMINI_API_KEY\|LOG_LEVEL" src/ --include="*.py"
```

---

## Phase 2 — Security (làm trước khi deploy lên bất kỳ môi trường nào)

### 2.1 Bảo vệ endpoint `/api/seed`

**File:** `src/routers/content.py:120`

Endpoint xóa toàn bộ `modules` + `topics` cascade, hiện tại **không cần auth**.

```python
# Trước
async def api_seed_data(db: AsyncSession = Depends(get_async_db)):

# Sau
async def api_seed_data(
    db: AsyncSession = Depends(get_async_db),
    _user: User = Depends(get_current_user),
):
    if not settings.debug:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seed endpoint only available in debug mode.",
        )
```

Cần import thêm: `from src.routers.auth import get_current_user` và `from src.models.user import User`.

---

### 2.2 Thêm auth cho Lecture Q&A routes (tuỳ chọn)

**File:** `src/api/app.py` (routes `/api/lectures/*`, `/api/progress/*`)

Hiện tại các route này public hoàn toàn — progress lưu theo `session_id` tự sinh, không gắn user account. Cân nhắc:

- **Giữ public** nếu muốn anonymous users dùng được AI Tutor mà không cần đăng ký.
- **Thêm auth** nếu muốn gắn lịch sử học với tài khoản người dùng.

> **Quyết định cần owner xác nhận** trước khi implement.

---

## Phase 3 — Database / Performance

### 3.1 Thêm indexes cho foreign keys

**File:** Tạo migration mới

Các bảng `qa_history`, `chapters`, `transcript_lines` filter nặng theo `lecture_id` nhưng không có explicit index.

```bash
uv run alembic revision --autogenerate -m "add_lecture_fk_indexes"
```

Sau đó chỉnh file migration:
```python
def upgrade() -> None:
    op.create_index("ix_qa_history_lecture_id",     "qa_history",      ["lecture_id"])
    op.create_index("ix_chapters_lecture_id",        "chapters",        ["lecture_id"])
    op.create_index("ix_transcript_lines_lecture_id","transcript_lines",["lecture_id"])

def downgrade() -> None:
    op.drop_index("ix_qa_history_lecture_id",      table_name="qa_history")
    op.drop_index("ix_chapters_lecture_id",         table_name="chapters")
    op.drop_index("ix_transcript_lines_lecture_id", table_name="transcript_lines")
```

---

## Phase 4 — Kiến trúc (effort cao, làm theo sprint riêng)

### 4.1 Gộp dual database engine (async + sync)

**Vấn đề:** Hiện tại có 2 SQLAlchemy engine chạy song song:

| File | Engine | Driver | Dùng cho |
|---|---|---|---|
| `src/database.py` | async | asyncpg | Tất cả routers mới (auth, quiz, assessment…) |
| `src/models/store.py` | sync | psycopg2 | Lecture Q&A routes (`app.py`) + ingestion scripts |

Hệ quả:
- 2 connection pool cạnh tranh tài nguyên
- `LearningProgress` chỉ tồn tại trong sync model → future migrations sẽ không auto-detect
- Mixing sync/async trong cùng event loop dễ gây blocking

**Kế hoạch migrate:**

**Bước 1** — Thêm async models tương đương trong `src/models/`:
- `src/models/lecture.py` — `Lecture`, `Chapter`, `TranscriptLine`
- `src/models/qa.py` — `QAHistory`, `LearningProgress`

**Bước 2** — Refactor `src/api/app.py` lecture routes sang dùng `AsyncSession`:
```python
# Trước (sync)
@app.get("/api/lectures")
def list_lectures(db: Session = Depends(get_db)):
    return db.query(Lecture).all()

# Sau (async)
@app.get("/api/lectures")
async def list_lectures(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(Lecture))
    return result.scalars().all()
```

**Bước 3** — Refactor `src/services/llm_service.py` sang async DB calls (phức tạp nhất — streaming response).

**Bước 4** — Refactor `src/services/ingestion.py` standalone script giữ sync hoặc chạy via `asyncio.run()`.

**Bước 5** — Xóa `src/models/store.py` sau khi tất cả đã migrate.

> ⚠️ Phase này có risk cao. Cần test kỹ trên local trước khi merge. Ước tính 1–2 ngày.

---

## Phase 5 — Dọn env / infra (cosmetic)

### 5.1 Xóa hoặc dùng Redis vars

**File:** `.env`, `docker-compose.yml`

`REDIS_URL`, `REDIS_PASSWORD`, `REDIS_PORT` được khai báo nhưng không có code nào sử dụng. Hai lựa chọn:

- **Xóa** khỏi `.env.example` và `docker-compose.yml` nếu chưa có kế hoạch dùng Redis.
- **Giữ + implement** nếu sắp dùng Redis cho session caching / rate limiting.

---

## Checklist

```
Phase 1 — Quick Wins
[ ] 1.1 Fix Dockerfile CMD
[ ] 1.2 Xóa LOG_LEVEL duplicate trong .env
[ ] 1.3 Xóa unused aliases trong config.py

Phase 2 — Security
[ ] 2.1 Thêm auth guard cho /api/seed
[ ] 2.2 Quyết định: auth cho lecture routes? (cần xác nhận)

Phase 3 — Performance
[ ] 3.1 Alembic migration thêm lecture_id indexes

Phase 4 — Architecture
[ ] 4.1 Bước 1: Thêm async models cho Lecture/QA
[ ] 4.2 Bước 2: Migrate lecture routes sang async
[ ] 4.3 Bước 3: Migrate llm_service sang async DB
[ ] 4.4 Bước 4: Refactor ingestion script
[ ] 4.5 Bước 5: Xóa store.py

Phase 5 — Cleanup
[ ] 5.1 Xóa/implement Redis vars
```

---

## Ghi chú

- Phase 1–3 có thể làm song song, không phụ thuộc nhau.
- Phase 4 phụ thuộc Phase 3 (cần migration trước).
- Phase 4 nên làm trên branch riêng, tránh merge khi chưa test kỹ.
- Không cần làm tất cả trước khi phát triển tính năng mới — Phase 1 + 2.1 + 3.1 là đủ để code sạch và an toàn.
