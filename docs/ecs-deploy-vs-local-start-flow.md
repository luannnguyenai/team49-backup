# ECS Deploy Vs Local `start.sh` Flow

## Mục đích

Tài liệu này đối chiếu flow deploy trên ECS với flow khởi chạy local bằng `start.sh`, để giải thích vì sao cùng một codebase nhưng hành vi production có thể khác localhost.

## Bảng So Sánh Flow-By-Flow

| Giai đoạn | `start.sh` localhost | ECS deploy workflow | Khác biệt thực tế |
|---|---|---|---|
| 1. Entry point tổng | Chạy một script orchestration duy nhất tại [start.sh](/D:/VSCODE/VINAI/A20-App-049/start.sh:1) | Chạy chuỗi GitHub Actions `CI -> Build & Push -> Deploy ECS Production` tại [build-push.yml](/D:/VSCODE/VINAI/A20-App-049/.github/workflows/build-push.yml:1) và [deploy-ecs-prod.yml](/D:/VSCODE/VINAI/A20-App-049/.github/workflows/deploy-ecs-prod.yml:1) | Local là bring-up toàn stack; ECS là release pipeline |
| 2. Prerequisite check | Kiểm tra Docker, Compose, `.env`, API keys, data folders tại [start.sh](/D:/VSCODE/VINAI/A20-App-049/start.sh:42) | Hầu như không có equivalent; workflow giả định runner, vars, secrets đã đúng | Local fail sớm do môi trường dev; ECS fail muộn ở runtime nếu config thiếu |
| 3. Hạ tầng phụ trợ | Tự start `db` và `redis` qua Docker Compose tại [docker-compose.yml](/D:/VSCODE/VINAI/A20-App-049/docker-compose.yml:54) và [docker-compose.yml](/D:/VSCODE/VINAI/A20-App-049/docker-compose.yml:76) | Không tạo DB/Redis; dùng RDS + ElastiCache đã tồn tại trong AWS | Local tự dựng dependencies; ECS tiêu thụ managed infra có sẵn |
| 4. Build backend image | Có thể build ngầm qua `docker compose up -d --build` tại [start.sh](/D:/VSCODE/VINAI/A20-App-049/start.sh:184) | Build/push image riêng tại [build-push.yml](/D:/VSCODE/VINAI/A20-App-049/.github/workflows/build-push.yml:95) | ECS tách build khỏi runtime, image immutable theo SHA |
| 5. Build frontend image | Local dev thường chỉ dựng deps/dev server, không phải production standalone tại [docker-compose.yml](/D:/VSCODE/VINAI/A20-App-049/docker-compose.yml:140) | Build production standalone image với build args tại [build-push.yml](/D:/VSCODE/VINAI/A20-App-049/.github/workflows/build-push.yml:103) | Local frontend dev và ECS frontend prod chạy rất khác nhau |
| 6. Start backend process | Compose command: `alembic upgrade head && uvicorn --reload` tại [docker-compose.yml](/D:/VSCODE/VINAI/A20-App-049/docker-compose.yml:108) | ECS backend service chỉ start app container từ task def tại [backend-service.json.tpl](/D:/VSCODE/VINAI/A20-App-049/cicd/taskdefs/backend-service.json.tpl:10) | Local nhét migrate vào startup command; ECS tách migrate ra one-off task |
| 7. Start frontend process | Local: `npm run dev` hot reload tại [docker-compose.yml](/D:/VSCODE/VINAI/A20-App-049/docker-compose.yml:146) | ECS: production standalone `node server.js` qua image runner tại [frontend/Dockerfile](/D:/VSCODE/VINAI/A20-App-049/frontend/Dockerfile:68) và [frontend-service.json.tpl](/D:/VSCODE/VINAI/A20-App-049/cicd/taskdefs/frontend-service.json.tpl:10) | Local dùng dev server; ECS dùng prebuilt production server |
| 8. Migrations | `start.sh` chạy `docker compose exec -T backend uv run alembic upgrade head` tại [start.sh](/D:/VSCODE/VINAI/A20-App-049/start.sh:223) | Workflow render taskdef migrate rồi `aws ecs run-task` tại [deploy-ecs-prod.yml](/D:/VSCODE/VINAI/A20-App-049/.github/workflows/deploy-ecs-prod.yml:177), [backend-migrate.json.tpl](/D:/VSCODE/VINAI/A20-App-049/cicd/taskdefs/backend-migrate.json.tpl:14), [run-ecs-task.sh](/D:/VSCODE/VINAI/A20-App-049/cicd/scripts/run-ecs-task.sh:10) | Local migrate inside running backend container; ECS migrate in disposable Fargate task |
| 9. Seed canonical/product shell | Tự chạy `scripts/seed.py` nếu `learning_units` rỗng tại [start.sh](/D:/VSCODE/VINAI/A20-App-049/start.sh:253) và [seed.py](/D:/VSCODE/VINAI/A20-App-049/scripts/seed.py:51) | Chạy trong `Initialize ECS Production` qua `seed-core` task nếu bật `run_seed_core=true` tại [init-ecs-prod.yml](/D:/VSCODE/VINAI/A20-App-049/.github/workflows/init-ecs-prod.yml:158) | Local đọc canonical mặc định từ repo; ECS materialize canonical bundle từ S3 rồi import |
| 10. Seed lectures | `start.sh` còn có bước riêng gọi `scripts/seed_lectures.py` nếu bảng `lectures` rỗng tại [start.sh](/D:/VSCODE/VINAI/A20-App-049/start.sh:267) | Trong ECS, lecture runtime được seed bên trong `scripts/seed.py` của `seed-core` task tại [backend-seed-core.json.tpl](/D:/VSCODE/VINAI/A20-App-049/cicd/taskdefs/backend-seed-core.json.tpl:18) | Hai flow đều không còn dùng `ToC_Summary`; lecture runtime được dựng từ canonical units + transcripts/image assets |
| 11. Schema v2 sync/backfill/validate | Chạy import canonical artifacts, backfill, validate, parity check tại [start.sh](/D:/VSCODE/VINAI/A20-App-049/start.sh:278) | Chạy trong `Initialize ECS Production` qua `sync-schema-v2` task nếu bật `run_sync_schema_v2=true` tại [init-ecs-prod.yml](/D:/VSCODE/VINAI/A20-App-049/.github/workflows/init-ecs-prod.yml:179) | ECS và local đều có parity/backfill path, nhưng local hiện vẫn còn vài bước orchestration dư |
| 12. Admin/demo accounts | Tạo account bằng `src.scripts.create_seed_accounts` tại [start.sh](/D:/VSCODE/VINAI/A20-App-049/start.sh:397) | Chạy trong `Initialize ECS Production` qua `run_seed_accounts=true` tại [init-ecs-prod.yml](/D:/VSCODE/VINAI/A20-App-049/.github/workflows/init-ecs-prod.yml:200) | Không còn là khác biệt cứng giữa local và ECS |
| 13. Config source | `.env` + compose env tại [docker-compose.yml](/D:/VSCODE/VINAI/A20-App-049/docker-compose.yml:24) | GitHub `vars` + Secrets Manager `secrets[]` tại [deploy-ecs-prod.yml](/D:/VSCODE/VINAI/A20-App-049/.github/workflows/deploy-ecs-prod.yml:64) và [backend-service.json.tpl](/D:/VSCODE/VINAI/A20-App-049/cicd/taskdefs/backend-service.json.tpl:45) | Hai môi trường có thể khác hoàn toàn về values dù cùng code |
| 14. File/data source | Mount toàn repo vào `/app` tại [docker-compose.yml](/D:/VSCODE/VINAI/A20-App-049/docker-compose.yml:116) | Chạy image build sẵn, không source mount | Code/path/data local tồn tại runtime; ECS chỉ có những gì đã copy vào image |
| 15. Asset strategy | Local vẫn kiểm tra dữ liệu trong `/app/data` tại [start.sh](/D:/VSCODE/VINAI/A20-App-049/start.sh:321) | ECS backend dùng `ASSET_STORAGE_PROVIDER=s3`, `CLOUDFRONT_DOMAIN` tại [backend-service.json.tpl](/D:/VSCODE/VINAI/A20-App-049/cicd/taskdefs/backend-service.json.tpl:27) | Local có thể sống nhờ filesystem; ECS nghiêng về S3/CloudFront |
| 16. Health gating | Local chờ DB healthy rồi probe backend nội bộ `http://127.0.0.1:8000/health` tại [start.sh](/D:/VSCODE/VINAI/A20-App-049/start.sh:206) và [start.sh](/D:/VSCODE/VINAI/A20-App-049/start.sh:236) | ECS dùng `ecs wait services-stable`, `describe-target-health`, rồi smoke HTTP public tại [wait-ecs-service.sh](/D:/VSCODE/VINAI/A20-App-049/cicd/scripts/wait-ecs-service.sh:8) và [smoke-ecs.sh](/D:/VSCODE/VINAI/A20-App-049/cicd/scripts/smoke-ecs.sh:23) | Local check process/container; ECS check ALB routing + external readiness |
| 17. Observability | Có thể dựng Prometheus/Grafana/Loki local tại [start.sh](/D:/VSCODE/VINAI/A20-App-049/start.sh:363) | Không start observability trong app deploy workflow | Local monitoring là optional sidecar stack; ECS release không đụng vào nó |
| 18. Failure mode phổ biến | Thiếu Docker, thiếu `.env`, migrate fail, seed fail | IAM thiếu quyền, task def/env sai, Secrets Manager sai, ALB health fail, smoke route sai | ECS fail nhiều ở integration boundary; local fail nhiều ở developer setup |
| 19. Thành phẩm cuối | Một môi trường dev/prod-like local có data được tự bơm vào | Một release production cập nhật task definition/service/image | `start.sh` tạo trạng thái dùng được từ số 0; ECS deploy chỉ promote artifact vào infra |

## Kết Luận Ngắn

Điểm khác biệt cốt lõi là: `start.sh` không chỉ “start app”, mà còn “chuẩn bị dữ liệu và môi trường”. ECS deploy thì không.

Vì vậy nếu local chạy ổn còn ECS lỗi, nghi ngờ đầu tiên nên là:

- Dữ liệu bootstrap/seed chỉ có ở local
- Secrets hoặc vars production khác `.env`
- Runtime đang phụ thuộc file trong repo
- Local startup có migrate, seed, backfill mà ECS chưa làm

## Gợi Ý Debug

Khi thấy hành vi khác nhau giữa localhost và ECS, kiểm tra theo thứ tự:

1. `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, provider API keys có giống kỳ vọng production không
2. `/api/course-sections` trên ECS trả rỗng hay lỗi vì thiếu seed/bootstrap
3. Code runtime có còn đọc `data/` trong filesystem hay không
4. One-off migrate và bootstrap task có thực sự chạy xong hay chưa
5. Build-time frontend vars có đúng với environment production không
