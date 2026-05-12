# Feature: Admin Observability

## Architecture liên quan
- [System Architecture](./architecture.md)
- Mục nên xem: `2. Kiến trúc ứng dụng`, `11. Observability architecture`, `12. Deployment architecture`

## 1. Mục tiêu
Admin observability cung cấp metrics, logs, và tracing để team có thể theo dõi sức khỏe hệ thống, hành vi LLM flows, và tình trạng vận hành mà không phải debug mù.

## 2. User/problem this solves
Khi hệ thống có assessment, planner, tutor, agent, và deploy ECS, vận hành gặp ba vấn đề:
- không biết endpoint nào đang chậm/lỗi;
- không biết trace LLM nào gây issue;
- không có admin surface để xem nhanh tình trạng.

Feature này biến hệ thống từ "có chạy" thành "có thể vận hành".

## 3. System scope
Backend:
- `src/middleware/prometheus.py`
- `src/middleware/request_logger.py`
- `src/core/observability.py`
- `src/routers/admin.py`
- `src/api/app.py`

Frontend:
- `frontend/app/admin/*`
- `frontend/lib/admin-api.ts`
- `frontend/components/admin/*`

Infra/docs:
- `admin-dashboard/*`
- `deploy-ecs/observability/*`

## 4. Architecture & flow

```text
FastAPI app
  -> /metrics via Prometheus instrumentator
  -> JSON access logs via middleware
  -> LangFuse root-span-first tracing cho tutor/onboarding/assessment
  -> admin router tổng hợp links/health/status
  -> admin frontend hiển thị KPI và external dashboards
```

Trong prod ECS, observability stack nối với Prometheus, Loki, Grafana, LangFuse Cloud, CloudWatch.

## 5. Key components
- `setup_prometheus(app)`: expose `/metrics`.
- `AccessLogMiddleware`: ghi `logs/access.jsonl`.
- `src/core/observability.py`: central helper cho LangFuse metadata, root span, callback, score linkage.
- `qa_history.langfuse_trace_id`: nối feedback user với trace.
- admin pages: traffic, system, users, llm, langfuse.

## 6. Data model / contracts
Observability ở đây không chỉ là log file:
- Prometheus metrics cho HTTP và tutor stream
- LangFuse metadata: `langfuse_user_id`, `langfuse_session_id`, `langfuse_tags`
- JSON access logs bỏ qua `/metrics`, `/health`
- admin API trả `prometheus_url` và các operational links

Feedback tutor có thể map thành LangFuse score `user_thumb`.

## 7. Technical decisions
- Dùng root-span-first pattern cho LangFuse thay vì callback rời rạc.
- Giữ Prometheus và LangFuse bổ trợ nhau: metrics cho system, traces cho LLM flow.
- Centralize observability helper trong một module để tránh mỗi service wire một kiểu.
- Admin UI là thin operational surface, không biến nó thành monitoring platform tự chế.

## 8. Risks / trade-offs
- Trace có thể gây noisy data nếu metadata không chuẩn.
- Observability quá nhiều điểm sẽ tăng maintenance cost.
- Cần fail-safe: LangFuse lỗi không được block business flow.
- Admin pages phụ thuộc external URLs/tooling nên cần rõ ranh giới giữa app và platform.

## 9. Testing / validation
Backend:
- `tests/test_tutor_observability.py`
- `tests/test_langfuse_observability.py`
- `tests/services/test_assessment_ai_summary.py`
- `tests/test_onboarding_endpoints.py` (LangFuse branches)

Frontend:
- `frontend/tests/unit/admin/*`

Manual/ops docs:
- `docs/agent-ops-runbook.md`
- `deploy-ecs/observability/*`

## 10. Demo-worthy points
- Rất hợp cho technical report theo hướng production engineering.
- Cho thấy hệ thống AI được instrumented bài bản, không phải hộp đen.
- Có thể combine với agent/tutor trong report để nói về observability của LLM workflows.
