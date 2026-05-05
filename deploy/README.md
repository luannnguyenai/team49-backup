# Deploy Folder — Render + AWS Assets

Kế hoạch deploy app lên **Render** (frontend + backend + Postgres + Redis), data/video lớn đặt trên **AWS S3** và stream qua **CloudFront**. Sau khi mua domain, gắn custom domain cho frontend, backend, CDN.

## Files

- `DEPLOYMENT_PLAN.md`: kế hoạch theo phase, mỗi phase 1 task, có DoD checklist + files touch + isolation guard.
- `PRODUCTION_CHECKLIST.md`: checklist trước/trong/sau deploy, dùng song song với plan.
- `ENVIRONMENT_MATRIX.md`: env variables cho backend Render, frontend Render, Postgres, Redis, AWS asset delivery.
- `.env.production.example`: template env, không commit secret thật.
- `RENDER_AWS_CONFIG_GUIDE.md`: hướng dẫn từng bước để config AWS S3/CloudFront và Render services.
- `MANUAL_DEPLOY_STEPS.md`: checklist thao tác tay theo thứ tự để bạn tự deploy AWS + Render.
- `PLATFORM_ANALYSIS.md`: phân tích nền tảng và trade-off (Render vs Railway vs AWS), giữ làm tham khảo.
- `railway.toml`: **DEPRECATED** — config Railway cũ, không dùng cho plan hiện tại.

## Quyết định hiện tại

- 1 Render account/project chứa 2 web service: `a20-backend`, `a20-frontend`.
- 1 Render PostgreSQL + extension `vector`.
- 1 Render Redis/Key Value.
- 1 AWS S3 private bucket cho course/video assets.
- 1 AWS CloudFront distribution stream asset trực tiếp về browser.
- Backend không proxy video bytes; chỉ tạo CloudFront URL/metadata.
- Asset delivery config-driven qua `ASSET_STORAGE_PROVIDER=local|s3` để giữ local dev không bị phá.
- Custom domain (`app.<domain>`, `api.<domain>`, `cdn.<domain>`) gắn sau khi mua tên miền.

## Khi nào KHÔNG dùng plan này

- Cần production lớn, multi-region, SLA cao → cân nhắc full AWS (App Runner/ECS) hoặc kiến trúc khác (xem `PLATFORM_ANALYSIS.md`).
- Cần DRM/protected video pipeline → cần phase mở rộng ngoài scope plan này.
