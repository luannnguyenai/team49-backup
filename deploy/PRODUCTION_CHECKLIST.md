# Demo Deploy Checklist — Railway

Tick song song khi thực thi `DEPLOYMENT_PLAN.md`.

- [ ] Repo đã push lên GitHub, branch deploy sẵn sàng
- [ ] `Dockerfile` (backend) và `frontend/Dockerfile` build được standalone
- [ ] Backend bind `0.0.0.0:$PORT` (Railway inject `PORT` runtime)
- [ ] Có tài khoản Railway + đã link GitHub
- [ ] Có tài khoản Resend + sender/domain đã verify
- [ ] Đã chọn LLM provider, có API key còn quota (OpenAI / Anthropic / Gemini)
- [ ] `SECRET_KEY` random 64 hex đã generate (`openssl rand -hex 32`)

## Deploy Day

- [ ] Tạo Railway project từ GitHub repo
- [ ] Add service `backend` (root context `/`)
- [ ] Add service `frontend` (root context `frontend/`)
- [ ] Add Postgres plugin
- [ ] Add Redis plugin
- [ ] Generate public domain cho `backend` và `frontend`
- [ ] Bật `CREATE EXTENSION vector;` trên Postgres
- [ ] Set env vars `backend` (DATABASE_URL prefix `postgresql+asyncpg://`, REDIS_URL, SECRET_KEY, CORS_ORIGINS, LLM key, Resend vars, DEBUG=false)
- [ ] Set env vars `frontend` (NEXT_PUBLIC_API_URL = backend domain, NODE_ENV=production)
- [ ] Trigger redeploy frontend sau khi `NEXT_PUBLIC_API_URL` đúng
- [ ] Chạy `alembic upgrade head` trên backend shell
- [ ] Chạy `import_canonical_artifacts_to_db`
- [ ] Chạy `import_product_shell_to_db`
- [ ] Chạy `check_canonical_runtime_parity`

## Smoke Test

- [ ] Backend `/health` → 200
- [ ] Frontend `/api/health` → 200
- [ ] Frontend home load
- [ ] Register + login OK
- [ ] Forgot password sends Resend email and reset link opens `/reset-password?token=...`
- [ ] Reset password succeeds, old password fails, new password logs in
- [ ] Course catalog load
- [ ] 1 learning unit load
- [ ] 1 quiz start + submit
- [ ] Tutor endpoint trả về response từ LLM

## Smoke Test

- [ ] Note 2 public domain để share demo
- [ ] Note git commit SHA đang chạy
- [ ] Theo dõi logs 30 phút đầu
- [ ] Theo dõi credit usage Railway hằng ngày
- [ ] Note known issues + LLM cost burn rate
