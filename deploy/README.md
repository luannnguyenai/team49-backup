# Deploy Folder — Railway Demo

Kế hoạch deploy demo 1–2 tuần lên **Railway**.

Files:
- `DEPLOYMENT_PLAN.md`: kiến trúc + bước deploy Railway từ đầu đến hết.
- `PRODUCTION_CHECKLIST.md`: checklist trước/trong/sau deploy.
- `ENVIRONMENT_MATRIX.md`: biến môi trường cần set cho mỗi service Railway.
- `.env.production.example`: template env (copy giá trị qua Railway dashboard, **không commit secret thật**).
- `railway.toml`: config build/deploy mặc định cho service backend.

Tóm tắt quyết định:
- 1 Railway project, 4 service: `backend`, `frontend`, `postgres` (pgvector), `redis`.
- Public domain Railway cấp sẵn (`*.up.railway.app`), HTTPS auto.
- Migration + import seed chạy 1 lần qua Railway shell sau khi deploy.
- $5 trial credit / Hobby plan đủ cho demo.

Khi nào KHÔNG dùng plan này:
- Cần production thật, traffic cao, SLA → quay về VM + Docker Compose (xem git history).
