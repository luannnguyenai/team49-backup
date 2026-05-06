# Deploy Checklist — Render + AWS

Tick song song khi thực thi `DEPLOYMENT_PLAN.md`. Chỉ chuyển nhóm tiếp theo khi nhóm trước đã pass.

## Pre-deploy

- [ ] Repo đã push lên GitHub, branch deploy sẵn sàng.
- [ ] Backend `Dockerfile` bind `0.0.0.0:${PORT:-8000}` (không hard-code 8000).
- [ ] Frontend `frontend/Dockerfile` build standalone, listen `$PORT` nếu Render yêu cầu.
- [ ] Có tài khoản Render đã link GitHub.
- [ ] Có tài khoản AWS với quota đủ cho S3 + CloudFront.
- [ ] Đã chọn AWS region (ví dụ `ap-southeast-1`).
- [ ] Đã chọn LLM provider, có API key còn quota.
- [ ] Đã chọn email provider (nếu bật forgot-password) và verify sender.
- [ ] `SECRET_KEY` random 64 hex đã generate (`openssl rand -hex 32`).
- [ ] Đã chốt domain layout dự kiến (`app.<domain>`, `api.<domain>`, `cdn.<domain>`).

## AWS asset infra

- [ ] S3 bucket private đã tạo, Block Public Access bật.
- [ ] Versioning bucket bật (nếu muốn rollback asset).
- [ ] `aws s3 sync ./data/courses s3://<bucket>/courses` chạy thành công.
- [ ] Đã ghi lại object count và total size trên S3.
- [ ] CloudFront distribution đã tạo, dùng OAC, S3 vẫn private.
- [ ] CloudFront cho phép `GET`, `HEAD`, redirect HTTP→HTTPS.
- [ ] CloudFront range request hoạt động (MP4 seek được).
- [ ] (Tùy chọn) CloudFront key pair tạo cho signed URL, private key lưu an toàn.
- [ ] (Tùy chọn) CloudFront Response Headers Policy set CORS nếu frontend fetch range qua XHR.

## Render database + cache

- [ ] Render PostgreSQL đã tạo, region đúng.
- [ ] `CREATE EXTENSION IF NOT EXISTS vector;` chạy OK.
- [ ] `SELECT extname ... 'vector'` trả về `vector`.
- [ ] Render Redis/Key Value đã tạo, có `REDIS_URL`.

## Backend deploy

- [ ] Render Web Service `a20-backend` deploy thành công (Docker, root `Dockerfile`).
- [ ] Health check path `/health` set đúng.
- [ ] Env backend đầy đủ:
  - [ ] `DATABASE_URL` prefix `postgresql+asyncpg://`.
  - [ ] `REDIS_URL`.
  - [ ] `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`.
  - [ ] `CORS_ORIGINS` JSON array hợp lệ.
  - [ ] `FRONTEND_BASE_URL`.
  - [ ] `MODEL_PROVIDER` + API key tương ứng.
  - [ ] `DEBUG=false`, `LOG_LEVEL=INFO`.
  - [ ] `ASSET_STORAGE_PROVIDER=s3`.
  - [ ] `AWS_REGION`, `AWS_S3_BUCKET`, `AWS_S3_PREFIX`, `CLOUDFRONT_DOMAIN`.
  - [ ] (Tùy chọn) `CLOUDFRONT_KEY_PAIR_ID`, `CLOUDFRONT_PRIVATE_KEY` nếu dùng signed URL.
- [ ] `curl https://<backend>.onrender.com/health` → 200.
- [ ] Logs backend không có secret và không lỗi lặp.

## Database migration + bootstrap pipeline

- [ ] `scripts/render_bootstrap.sh` đã được tạo và chạy local container thành công (idempotent).
- [ ] Trên Render shell: `bash scripts/render_bootstrap.sh` exit code 0.
  - [ ] 1/8 alembic upgrade head OK.
  - [ ] 2/8 seed canonical product shell OK (hoặc skipped if populated).
  - [ ] 3/8 seed CS231n lectures OK (hoặc skipped).
  - [ ] 4/8 import canonical artifacts schema v2 OK.
  - [ ] 5/8 backfill schema v2 OK.
  - [ ] 6/8 validate schema v2 OK.
  - [ ] 7/8 canonical runtime parity OK.
  - [ ] 8/8 create admin/demo accounts OK.
- [ ] Verify counts sau bootstrap:
  - [ ] `SELECT COUNT(*) FROM learning_units` > 0.
  - [ ] `SELECT COUNT(*) FROM lectures` > 0.
  - [ ] `SELECT COUNT(*) FROM users WHERE role='admin'` >= 1.
- [ ] Verify parity S3 ↔ DB: `storage_key`/`video_filename` trong DB khớp object thật trên S3 (Phase 14.1).

## Frontend deploy

- [ ] Render Web Service `a20-frontend` deploy thành công (Docker, root `frontend/`).
- [ ] Env frontend đầy đủ:
  - [ ] `NEXT_PUBLIC_API_URL` = backend URL.
  - [ ] `API_INTERNAL_URL` (nếu dùng).
  - [ ] `NODE_ENV=production`, `NEXT_TELEMETRY_DISABLED=1`.
- [ ] `curl https://<frontend>.onrender.com/api/health` → 200.
- [ ] Frontend rebuild nếu đổi `NEXT_PUBLIC_API_URL`.

## Smoke test functional

- [ ] Home page load.
- [ ] Register + login OK.
- [ ] (Nếu bật email) Forgot password gửi mail, link mở `/reset-password?token=...` đúng.
- [ ] Reset password thành công, mật khẩu cũ fail, mật khẩu mới login được.
- [ ] Course catalog load.
- [ ] Ít nhất 1 learning unit load.
- [ ] Video URL trả về dạng CloudFront, không phải `/data/...`.
- [ ] Video play + seek được.
- [ ] 1 quiz/session start + submit OK.
- [ ] Tutor endpoint trả response từ LLM.
- [ ] Browser console không gọi `localhost`.
- [ ] Không có mixed content HTTP.

## Custom domain (sau khi mua)

- [ ] `app.<domain>` map vào Render frontend, TLS active.
- [ ] `api.<domain>` map vào Render backend, TLS active.
- [ ] `cdn.<domain>` map vào CloudFront, ACM cert ở `us-east-1`.
- [ ] Backend env update: `CORS_ORIGINS`, `FRONTEND_BASE_URL`, `CLOUDFRONT_DOMAIN`.
- [ ] Frontend env update: `NEXT_PUBLIC_API_URL`, `API_INTERNAL_URL` + redeploy.
- [ ] Smoke test toàn bộ flow lại bằng domain thật.

## Final production-readiness

- [ ] `DEBUG=false` trên backend.
- [ ] CORS chỉ allow domain frontend hợp lệ.
- [ ] S3 bucket vẫn private.
- [ ] CloudFront là entrypoint duy nhất cho asset.
- [ ] Backend không proxy video bytes.
- [ ] AWS Budget alert đã bật.
- [ ] CloudFront usage metric visible.
- [ ] Render service plans known + billing đã review.
- [ ] Note 3 domain final để share demo.
- [ ] Note git commit SHA đang chạy.
- [ ] Theo dõi logs 30 phút đầu.
- [ ] Theo dõi LLM cost burn rate.
- [ ] Note known issues vào `THINGS NEED FIX.md` hoặc tracker.
