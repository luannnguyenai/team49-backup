# Deploy Folder — Railway + AWS S3 (Demo 1–2 tuần)

Hybrid deployment cho demo:
- **Railway**: app stack (backend FastAPI, frontend Next.js, Postgres+pgvector, Redis)
- **AWS S3**: video assets (~14GB) — backend redirect 302 đến presigned URL

## Files

| File | Mục đích |
|---|---|
| `DEPLOYMENT_PLAN.md` | Plan chi tiết 12 phần, step-by-step từ 0 đến deploy + smoke test |
| `PRODUCTION_CHECKLIST.md` | Checklist tick từng bước, dùng kèm khi thực thi |
| `ENVIRONMENT_MATRIX.md` | Toàn bộ env vars cho từng service Railway + AWS |
| `.env.production.example` | Template env (không commit secret thật) |

## Quick start

1. Đọc `DEPLOYMENT_PLAN.md` mục **0–2** để hiểu phạm vi.
2. Sửa code 4 chỗ ở mục **7. Code Patches** (bắt buộc trước khi deploy).
3. Setup AWS S3 theo mục **3** (~30 phút, có thể chạy upload background).
4. Setup Railway theo mục **4** (~60 phút).
5. Seed data theo mục **5**.
6. Smoke test theo mục **6**.
7. Tick `PRODUCTION_CHECKLIST.md` song song.

## Cost estimate

| Item | 2 tuần |
|---|---|
| Railway (Hobby + usage) | ~$7 |
| AWS S3 (storage + egress) | ~$1.50 |
| LLM API (tách biệt) | ~$1–3 |
| **Total** | **~$10–15** |

## Quyết định đã chốt

- Postgres = **custom service từ image `pgvector/pgvector:pg16`** (Railway plugin mặc định KHÔNG có pgvector → blocker)
- Frontend `NEXT_PUBLIC_API_URL` = **build arg trên Railway** (không phải runtime env)
- Backend service-to-service dùng **`${{backend.RAILWAY_PRIVATE_DOMAIN}}`**
- Video phục vụ qua **S3 presigned URL** (TTL 1h), `serve_data_asset` redirect 302
- Slides PDF + JSON metadata vẫn nằm trong image backend (~300MB OK)

## Out of scope

TLS thủ công, reverse proxy, observability stack, CI/CD pipeline, backup automation, CloudFront CDN, HA. Demo dùng built-in Railway features.

Khi cần production thật → migrate sang Full AWS (App Runner + RDS + ElastiCache) hoặc VM + Docker Compose. Plan này không cover.
