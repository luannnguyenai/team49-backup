# Environment Matrix — Railway

Set qua Railway dashboard (**Service → Variables**), không commit `.env` thật.

## Service `backend` (FastAPI)

| Variable | Value | Note |
|---|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` rồi sửa scheme thành `postgresql+asyncpg://...` | SQLAlchemy async driver |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` | Railway cấp sẵn |
| `SECRET_KEY` | random 64 hex | `openssl rand -hex 32` |
| `ALGORITHM` | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | |
| `RATE_LIMIT_LOGIN_PER_MINUTE` | `5` | |
| `CORS_ORIGINS` | `["https://<frontend>.up.railway.app"]` | JSON array |
| `MODEL_PROVIDER` | `openai` / `anthropic` / `gemini` | |
| `DEFAULT_MODEL` | `gpt-4o-mini` | |
| `FAST_MODEL` | `gpt-4o-mini` | |
| `OPENAI_API_KEY` | `sk-...` | Nếu dùng OpenAI |
| `ANTHROPIC_API_KEY` | | Nếu dùng Anthropic |
| `GEMINI_API_KEY` | | Nếu dùng Gemini |
| `DEBUG` | `false` | **Bắt buộc false** |
| `LOG_LEVEL` | `INFO` | |
| `DB_POOL_SIZE` | `5` | Demo nhỏ |
| `DB_MAX_OVERFLOW` | `10` | |
| `PORT` | (Railway inject) | Backend phải bind `0.0.0.0:$PORT` |

## Service `frontend` (Next.js)

| Variable | Value | Note |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `https://<backend>.up.railway.app` | Bake vào build, đổi → phải redeploy |
| `NODE_ENV` | `production` | |
| `PORT` | (Railway inject) | Next start phải dùng `$PORT` |

## Postgres plugin

Railway cấp sẵn:
- `DATABASE_URL` (scheme `postgresql://`)
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`

Sau khi plugin up, chạy 1 lần:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## Redis plugin

Railway cấp sẵn:
- `REDIS_URL` (đã có password)

## Lưu ý

- `DATABASE_URL` Railway cấp dạng `postgresql://...`. SQLAlchemy async cần `postgresql+asyncpg://...`. Sửa bằng cách set `DATABASE_URL` thủ công, copy giá trị từ Postgres plugin và đổi prefix.
- `CORS_ORIGINS` phải JSON array hợp lệ, parse bởi `src/config.py`.
- Đổi `NEXT_PUBLIC_API_URL` → frontend phải rebuild (Railway tự trigger khi env đổi).
- Không cần `POSTGRES_*`, `REDIS_PASSWORD` riêng vì plugin tự quản lý credential qua `DATABASE_URL` / `REDIS_URL`.
