# Environment Matrix — Railway + AWS S3

Set qua Railway dashboard (**Service → Variables**), không commit `.env` thật.

Cú pháp Railway reference cross-service: `${{ServiceName.VAR}}`.

---

## Service `backend` (FastAPI)

### Database
| Variable | Value | Note |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://ailearning:<PASSWORD>@${{postgres.RAILWAY_PRIVATE_DOMAIN}}:5432/ai_learning` | **Prefix bắt buộc `postgresql+asyncpg://`** vì SQLAlchemy async. Railway service tên `postgres` (custom) cấp `RAILWAY_PRIVATE_DOMAIN`. |

### Cache / Session
| Variable | Value | Note |
|---|---|---|
| `REDIS_URL` | `${{Redis.REDIS_URL}}` | Railway plugin Redis cấp sẵn (đã có password) |

### Auth & Security
| Variable | Value | Note |
|---|---|---|
| `SECRET_KEY` | random 64 hex | `openssl rand -hex 32` |
| `ALGORITHM` | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | |
| `RATE_LIMIT_LOGIN_PER_MINUTE` | `5` | |

### CORS
| Variable | Value | Note |
|---|---|---|
| `CORS_ORIGINS` | `["https://<frontend>.up.railway.app"]` | JSON array, **chính xác origin** frontend Railway. Parser ở `src/config.py:163` chấp nhận JSON array hoặc CSV. |

### LLM
| Variable | Value | Note |
|---|---|---|
| `MODEL_PROVIDER` | `openai` / `anthropic` / `gemini` | Chọn 1 |
| `DEFAULT_MODEL` | `gpt-4o-mini` | |
| `FAST_MODEL` | `gpt-4o-mini` | |
| `OPENAI_API_KEY` | `sk-...` | Nếu `MODEL_PROVIDER=openai` |
| `ANTHROPIC_API_KEY` | `sk-ant-...` | Nếu `MODEL_PROVIDER=anthropic` |
| `GEMINI_API_KEY` | `AIza...` | Nếu `MODEL_PROVIDER=gemini` |

### Runtime tuning
| Variable | Value | Note |
|---|---|---|
| `DEBUG` | `false` | **Bắt buộc false** trong production |
| `LOG_LEVEL` | `INFO` | `WARNING` nếu logs quá ồn |
| `DB_POOL_SIZE` | `5` | Demo nhỏ, không cần lớn |
| `DB_MAX_OVERFLOW` | `10` | |
| `DB_ECHO` | `false` | Tránh log SQL spam |
| `PORT` | (Railway inject) | Backend đọc qua CMD shell `${PORT:-8000}` |

### AWS S3 (cho video redirect)
| Variable | Value | Note |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | `AKIA...` | IAM user `ai-learning-backend-demo` |
| `AWS_SECRET_ACCESS_KEY` | `<secret>` | |
| `AWS_REGION` | `us-east-1` | Trùng region bucket |
| `S3_VIDEO_BUCKET` | `ai-learning-videos-demo` | Tên bucket đã tạo |
| `S3_PRESIGNED_URL_TTL` | `3600` | TTL presigned URL (giây) |

---

## Service `frontend` (Next.js)

### Build args (Settings → Build → Build Args)
| Variable | Value | Note |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `https://<backend>.up.railway.app` | **Build arg, KHÔNG phải runtime env** vì `NEXT_PUBLIC_*` bake vào bundle JS. Đổi → phải redeploy. |
| `API_INTERNAL_URL` | `http://${{backend.RAILWAY_PRIVATE_DOMAIN}}:8000` | Server-side rewrites trong `next.config.mjs` dùng biến này |

### Runtime env (Settings → Variables)
| Variable | Value | Note |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `https://<backend>.up.railway.app` | Cũng set runtime để consistency |
| `API_INTERNAL_URL` | `http://${{backend.RAILWAY_PRIVATE_DOMAIN}}:8000` | |
| `NODE_ENV` | `production` | |
| `PORT` | (Railway inject) | Next standalone đọc tự động |
| `HOSTNAME` | `0.0.0.0` | Đã set trong Dockerfile |

---

## Service `postgres` (custom, image `pgvector/pgvector:pg16`)

| Variable | Value | Note |
|---|---|---|
| `POSTGRES_USER` | `ailearning` | |
| `POSTGRES_PASSWORD` | random 24 char | `openssl rand -base64 24` |
| `POSTGRES_DB` | `ai_learning` | |
| `PGDATA` | `/var/lib/postgresql/data/pgdata` | Volume mount path subdir |

Volume: 5GB tại `/var/lib/postgresql/data`.

Sau khi service up, vào shell chạy 1 lần:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```
(Image `pgvector/pgvector:pg16` đã có extension binary, chỉ cần `CREATE EXTENSION`.)

---

## Plugin `Redis`

Railway tự cấp:
- `REDIS_URL` (đã có password và TLS nếu có)
- `REDIS_PRIVATE_URL`

Backend dùng `${{Redis.REDIS_URL}}`.

---

## Lưu ý quan trọng

### Driver scheme Postgres
Railway custom service Postgres cấp env `DATABASE_URL` dạng `postgresql://...` qua reference. Code dùng SQLAlchemy async → **phải `postgresql+asyncpg://`**. Vì vậy KHÔNG dùng reference `${{postgres.DATABASE_URL}}`, mà tự construct:
```
postgresql+asyncpg://<user>:<password>@${{postgres.RAILWAY_PRIVATE_DOMAIN}}:5432/<db>
```

### `NEXT_PUBLIC_*` là build-time
- `NEXT_PUBLIC_API_URL` bake vào bundle JS lúc `npm run build`.
- Đổi giá trị → **phải redeploy frontend**.
- Set ở **Build Args**, không chỉ Variables.

### `RAILWAY_PRIVATE_DOMAIN`
- Railway tự cấp domain private dạng `<service>.railway.internal` cho mỗi service.
- Reference qua `${{<service>.RAILWAY_PRIVATE_DOMAIN}}`.
- Chỉ resolve trong Railway internal network, không qua public internet → free egress.

### CORS
- `CORS_ORIGINS` phải đúng origin frontend Railway sau khi generate domain.
- Nếu sau này gắn custom domain → cập nhật lại + redeploy backend.

### S3 region
- `AWS_REGION` phải trùng region bucket. Sai region → presigned URL sai signature → 403.

### Không cần biến cũ
Loại bỏ khỏi production env:
- `POSTGRES_*` (chỉ Postgres service cần, không phải backend)
- `REDIS_PASSWORD` (Redis plugin tự quản qua URL)
- `BACKEND_PORT`, `FRONTEND_PORT` (Railway inject `PORT`)
- `NEXT_PUBLIC_API_URL=http://localhost:8000` (giá trị dev)
