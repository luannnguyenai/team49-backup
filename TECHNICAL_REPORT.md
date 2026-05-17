# Báo cáo Kỹ thuật — AI Adaptive Learning Platform

## 1. Tóm tắt tổng quan

AI Adaptive Learning Platform là một hệ thống học tập thích ứng cho các khóa AI/ML, kết hợp course platform, canonical knowledge graph, assessment runtime và AI tutor/agent. Codebase hiện tại được tổ chức theo hướng course-first: frontend Next.js phục vụ trải nghiệm học, backend FastAPI quản lý API/runtime, PostgreSQL là nguồn dữ liệu chính, Redis hỗ trợ cache/rate limit/token denylist, và các pipeline offline sinh canonical artifacts từ transcript/course data.

Hệ thống không chỉ là chatbot gắn vào bài học. Lớp AI được chia thành nhiều pipeline: tutor streaming theo ngữ cảnh lecture, agentic RAG cho learning copilot, guardrail router, PII guardrail, structured routing, tool execution, evidence/citation handling, và observability bằng Langfuse/Prometheus. Lớp adaptive learning dựa trên canonical content schema: knowledge points, learning units, item bank, item calibration, item-KP map, phase map, prerequisite edges và learner mastery state.

Báo cáo này được viết sau khi khảo sát các file chính trong repo, gồm `src/api/app.py`, `src/config.py`, `src/services/*`, `src/models/*`, `src/routers/*`, `frontend/*`, `src/scripts/pipeline/*`, Docker/Compose, Terraform/ECS docs, tests và README.

![Sơ đồ tổng quan hệ thống](architecture/01-system-overview.svg)

## 2. Stack công nghệ

### 2.1 Backend

| Lớp | Công nghệ | Mục đích sử dụng |
|---|---|---|
| Runtime | Python 3.12 | Runtime ứng dụng backend |
| API framework | FastAPI | REST API, streaming NDJSON, endpoint static/data asset |
| Data validation | Pydantic v2, pydantic-settings | Schema request/response và config môi trường |
| ORM | SQLAlchemy 2 async | Truy cập PostgreSQL bất đồng bộ qua `AsyncSession` |
| Migrations | Alembic | Quản lý phiên bản schema database |
| Database driver | asyncpg, psycopg | Async cho app và checkpoint LangGraph Postgres |
| Auth | JWT, python-jose, passlib bcrypt | Access/refresh token, hash password, dependency auth |
| Background/runtime helpers | Typer, scripts | Import dữ liệu, calibration, validation, seed |
| LLM orchestration | LangChain, LangGraph | Graph tutor, graph `/api/agent`, routing tool |
| LLM providers | OpenAI-compatible, Gemini, Anthropic hooks | Chat model registry có thể cấu hình + fallback |
| Observability | Langfuse, Prometheus, JSON access logs | Trace LLM, metric stream, observability cho admin |

### 2.2 Frontend

| Lớp | Công nghệ | Mục đích sử dụng |
|---|---|---|
| Framework | Next.js 14 App Router | Routing trang, layout, server/client component |
| UI runtime | React 18 | UI tương tác cho learning, agent, assessment, admin |
| Ngôn ngữ | TypeScript 5 | API client có kiểu, contract UI, state |
| Styling | Tailwind CSS, design token global | Theme, layout responsive, component tái sử dụng |
| State | Zustand | Auth, onboarding, course catalog, learning path |
| HTTP | Axios + Fetch streaming | REST call, refresh JWT, streaming NDJSON cho agent |
| Forms/validation | react-hook-form, zod | Form auth/onboarding, validation có kiểu |
| Visualization | ReactFlow, dagre, Recharts | Graph roadmap, biểu đồ dashboard |
| Icons | lucide-react | Icon điều khiển và navigation |
| Tests | Vitest, Testing Library, Playwright | Test unit, route, component, E2E |

### 2.3 Dữ liệu, hạ tầng, vận hành

| Thành phần | Công nghệ | Mục đích sử dụng |
|---|---|---|
| DB chính | PostgreSQL 16 + image pgvector | Dữ liệu app, canonical content, learner state, agent state |
| Cache/limit | Redis 7 | Rate limit, token denylist, shared runtime state |
| Object/asset | Local `/data` ở dev, S3 + CloudFront ở prod | Video, transcript, slide và asset khóa học |
| Container | Docker, Docker Compose | Image dev local và production |
| Cloud target | AWS ECS Fargate | Service frontend/backend |
| IaC | Terraform | VPC, ALB, ECS, RDS, Redis/Valkey, S3, CloudFront, IAM, observability |
| CI/CD | GitHub Actions (workflow draft + active) | Build, push, render task definition, deploy ECS |
| Quản lý artifact ML | DVC | Adapter fine-tuned, dataset, transcript, artifact đã xử lý |

## 3. Kiến trúc repository

```text
src/
  api/app.py                    Khởi tạo FastAPI, middleware, đăng ký router
  config.py                     Settings Pydantic tập trung, config provider/runtime
  models/                       Bảng ORM SQLAlchemy
  schemas/                      Contract API kiểu Pydantic
  routers/                      Các module endpoint API
  repositories/                 Lớp truy cập dữ liệu bao quanh SQLAlchemy
  services/                     Business logic, orchestration AI, planner, assessment
  prompts/agent/                Prompt YAML cho agent và guardrail router
  scripts/pipeline/             Pipeline export/import/validation cho canonical data

frontend/
  app/                          Route và layout Next.js
  components/                   UI dùng chung và component domain
  features/                     Module cấp feature: agent, learning-path, course platform
  lib/                          API client, adapter, helper runtime
  stores/                       Store Zustand
  tests/                        Test unit, route và E2E

data/
  bootstrap/                    JSON bootstrap cho course shell
  courses/                      Transcript/asset đã xử lý (track bằng DVC)
  final_artifacts.dvc           Tracking bundle canonical artifact

alembic/                        Database migration
architecture/                   Diagram hệ thống và AI pipeline
deploy-ecs/                     Thiết kế deploy AWS ECS/Terraform
cicd/                           Template CI/CD ECS và script hỗ trợ
docs/                           Worklog, eval report, runbook, ghi chú kiến trúc
tests/                          Test backend unit/integration/contract/pipeline
```

Repo có cấu trúc phân lớp rõ:

1. Router dịch contract HTTP sang service call.
2. Service triển khai business behavior và AI orchestration.
3. Repository cô lập pattern truy cập dữ liệu.
4. Model biểu diễn cấu trúc database.
5. Schema định nghĩa contract API và tool.
6. Script vật chất hoá artifact offline thành bảng runtime.

## 4. Kiến trúc runtime backend

### 4.1 Cấu trúc ứng dụng FastAPI

`src/api/app.py` là entrypoint ứng dụng. File này build app FastAPI, đăng ký CORS, Prometheus metric, JSON access log, static mount, domain exception handler, hook lifecycle Redis và toàn bộ router.

Các nhóm API đã đăng ký:

| Router | Trách nhiệm |
|---|---|
| `auth`, `users` | Đăng ký, login, refresh, logout, current user |
| `onboarding` | Onboarding nhiều bước (goal, course, giờ học, deadline) |
| `courses`, `content` | Catalog khóa học, overview khóa học, nội dung learning unit |
| `assessment`, `placement_deprecated`, `placement_lite`, `placement_assessment` | Runtime placement/assessment (canonical + tương thích legacy) |
| `quiz`, `module_test` | Runtime quiz inline và module test cuối module |
| `learning_path`, `learning_session`, `history` | Kết quả planner, tiến độ, lịch sử session |
| `agent`, `agent_ops` | Learning copilot, conversation, action, thao tác graph |
| `chat_models` | Availability của chat model |
| `admin` | Dữ liệu admin dashboard (13 endpoint, gated theo role) |
| `replan`, `review` | Workflow replan và service review |
| `test_support` | Endpoint helper cho test integration/contract |

App cũng giữ lại các endpoint hướng lecture (legacy):

| Endpoint | Mục đích |
|---|---|
| `/api/lectures` | Liệt kê các row lecture legacy |
| `/api/lectures/{lecture_id}/toc` | Mục lục lecture |
| `/api/lectures/ask` | Phản hồi tutor streaming qua LangGraph |
| `/api/lectures/qa-history` | Lịch sử Q&A |
| `/api/history/{qa_id}/rate` | Điểm feedback của user, forward sang Langfuse |

### 4.2 Mẫu truy cập database

`src/database.py` định nghĩa hai async engine:

1. `engine` có pool dùng cho route FastAPI async thông thường.
2. `tutor_thread_engine` dùng NullPool cho tutor streaming helper gọi `asyncio.run()` từ sync generator/thread path.

Việc tách hai engine tránh lỗi asyncpg cross-event-loop ở route tutor streaming.

Dependency `get_async_db()` commit khi success và rollback khi exception. Service cần kiểm soát chi tiết hơn vẫn có thể gọi `flush`, `commit`, hoặc method repository trực tiếp trong boundary transaction cấp route.

### 4.3 Cấu hình

`src/config.py` tập trung:

- Settings LLM provider/model: default model, fast model, provider, reasoning effort, request timeout, retry.
- Endpoint OpenAI-compatible Qwen.
- Guardrail router endpoint, model, API key, service token Cloudflare Access, fallback provider/model và cooldown.
- Key/host Langfuse.
- Settings pool database.
- JWT, rate limit login/password-reset và thời gian sống của token.
- Mode delivery asset: `/data` local hoặc S3/CloudFront.
- Redis URL.
- CORS origin.
- Feature flag và weight cho knowledge graph/planner.
- Tham số chiến lược selection placement/CAT/IRT.

Cấu hình dựa trên pydantic-settings và đọc `.env` với UTF-8.

### 4.4 Mô hình lỗi

`src/exceptions.py` định nghĩa domain exception hierarchy. Service raise domain exception, không chạm HTTP; `src/exception_handlers.py` map sang `JSONResponse` ở app boundary (`app.add_exception_handler(DomainError, domain_exception_handler)`).

| Exception | HTTP | Khi nào raise |
|---|---|---|
| `DomainError` | 500 | Base class, không raise trực tiếp |
| `NotFoundError` | 404 | Resource không tồn tại |
| `ValidationError` | 422 | Input semantically invalid |
| `ConflictError` | 409 | State conflict (pending action đã commit, duplicate, …) |
| `ForbiddenError` | 403 | Ownership/role violation |
| `InsufficientDataError` | 409 | Không đủ data để chạy (chưa placement, chưa progress, …) |

Pattern tách layer HTTP khỏi business logic, giúp service test được mà không cần FastAPI test client.

## 5. Kiến trúc dữ liệu

Codebase sử dụng mô hình dữ liệu nhiều lớp thay vì một schema content đơn lẻ.

### 5.1 Lớp Product Shell

Định nghĩa chính ở `src/models/course.py`.

| Bảng | Mục đích |
|---|---|
| `courses` | Row catalog khóa học hiển thị cho user |
| `course_overviews` | Metadata overview marketing/learning |
| `course_sections` | Hierarchy lecture/module |
| `learning_units` | Đơn vị học cấp product, liên kết tới canonical unit |
| `course_assets` | Metadata video/transcript/slide/thumbnail |
| `learning_progress_records` | Tiến độ user theo learning unit |
| `tutor_context_bindings` | Liên kết learning unit với context tutor |
| `legacy_lecture_mappings` | Cầu nối từ bảng lecture cũ sang course platform mới |

Lớp product shell được tối ưu cho navigation UI, trang course, màn hình học và delivery asset.

### 5.2 Lớp Canonical Content

Định nghĩa chính ở `src/models/canonical.py`.

| Bảng | Mục đích |
|---|---|
| `concepts_kp` | Catalog knowledge point toàn cục |
| `units` | Learning unit canonical xuất từ artifact khóa học |
| `unit_kp_map` | Map unit↔KP kèm metadata coverage |
| `question_bank` | Nội dung item đánh giá canonical |
| `item_calibration` | Prior + tham số calibrated cho difficulty/discrimination/guessing |
| `item_phase_map` | Mức phù hợp của item theo phase placement/quiz/module-test |
| `item_kp_map` | Q-matrix item↔KP |
| `prerequisite_edges` | Edge prerequisite được giữ |
| `pruned_edges` | Edge bị reject, giữ lại để audit |
| `ingest_runs` | Audit lần ingest |
| `calibration_runs`, `item_calibration_history` | Audit calibration và hỗ trợ rollback |
| `item_exposure_stats` | Counter exposure cho adaptive selection |
| `human_review_queue` | Queue HITL cho quyết định content/graph chưa chắc chắn |

Lớp này là nguồn cho adaptive assessment, search, planner, citation agent và tool prerequisite path.

### 5.3 Trạng thái học viên

Định nghĩa chính ở `src/models/learning.py`.

| Bảng | Mục đích |
|---|---|
| `sessions` | Session assessment, quiz, module test, practice |
| `interactions` | Sự kiện phản hồi theo từng câu hỏi |
| `learner_mastery_kp` | Trạng thái dạng posterior cho cặp User × KP |
| `goal_preferences` | Khóa đã chọn, trạng thái goal và placement |
| `waived_units` | Skip/waiver đã audit |
| `plan_history` | Snapshot output planner |
| `rationale_log` | Lý do planner theo từng unit |
| `planner_session_state` | Trạng thái planner duy trì giữa các lần replan |

### 5.4 Trạng thái Agent

Định nghĩa ở `src/models/agent_conversation.py` và `src/models/agent_graph.py`.

| Bảng | Mục đích |
|---|---|
| `agent_conversations` | Metadata conversation và thread id |
| `agent_conversation_messages` | Message user/assistant đã persist |
| `agent_conversation_memories` | Tóm tắt memory đã compact |
| `agent_graph_runs` | Tracking graph run idempotent |
| `agent_response_payloads` | Payload response đã lưu |
| `agent_pending_actions` | Action đang chờ xác nhận |
| `agent_trace_events` | Sự kiện trace/audit của graph |

Tổng thể cho phép resumable action, idempotency, phát hiện conflict, lịch sử conversation và memory compaction.

## 6. Pipeline dữ liệu canonical

Runtime DB được nuôi bởi chuỗi offline stage P1→P5. Toàn bộ 24 script tại `src/scripts/pipeline/`. DVC track artifact lớn ở `data/bootstrap.dvc`, `data/final_artifacts.dvc`, `data/courses/**/*.dvc`, `data/guardrail_router/**/*.dvc`. Prompt offline cho từng stage nằm ở `prompts/` (gốc repo): `1_question_bank.txt`, `2_item_calibration.txt`, `3_quality_assurance.txt`, `4_item_phase_map.txt`, `lecture_extraction_prompt.txt`.

![Sơ đồ data flywheel](architecture/08-data-flywheel.svg)

### 6.1 Pipeline Stages P1 → P5

| Stage | Scripts | Output |
|---|---|---|
| P1 — Sanitize raw artifacts | `sanitize_p1_artifacts.py` + service `p1_artifact_sanitizer.py` | Clean transcript/lecture extraction |
| P2 — Build calibration inputs | `build_p2_input.py` | Inputs cho item calibration/QA |
| P3 — Sanitize + segment | `sanitize_p3a_inputs.py`, `cut_p3b_video_segments.py`, `normalize_p3c_to_p4.py`, service `p3_input_sanitizer.py` | Video segments, normalized item bank |
| P4 — Canonical artifact | (output từ P3 normalize) | Canonical JSONL bundle |
| P5 — Bootstrap + bundle | `build_p5_input.py`, `build_p5_append_bootstrap.py`, `export_final_ingest_bundle.py` | `data/final_artifacts/` (DVC-tracked) |
| Visualize | `visualize_kg.py` | Knowledge graph render |
| Demo / synthetic | `generate_synthetic_demo_users.py`, `reset_synthetic_cohort.py`, `reset_demo_accounts.py` | Synthetic cohort cho eval |
| Eval dataset | `prepare_eval_aihub_dataset.py` | Dataset cho external eval |
| Legacy bridge | `backfill_product_canonical_links.py`, `export_legacy_runtime_data.py`, `check_legacy_schema_usage.py`, `check_legacy_cleanup_readiness.py`, `validate_legacy_cleanup_targets.py` | Migration từ legacy schema |

### 6.2 Canonical Artifact Import

`src/scripts/pipeline/import_canonical_artifacts_to_db.py` import JSONL từ P5 bundle vào canonical tables.

Input files:

- `concepts_kp.jsonl`, `units.jsonl`, `unit_kp_map.jsonl`
- `question_bank.jsonl`, `item_calibration.jsonl`
- `item_phase_map.jsonl`, `item_kp_map.jsonl`
- `prerequisite_edges.jsonl`, `pruned_edges.jsonl`
- `manifest.json`

Đặc tính triển khai:

- Deterministic natural key cho idempotent upsert.
- Manifest count check trước import.
- Unknown column / missing PK fail validation.
- `item_phase_map.suitability_score` normalize ordinal (high/medium/low) → numeric.
- Post-import DB count verification đảm bảo artifact/runtime parity.

### 6.3 Product Shell Import

`src/scripts/pipeline/import_product_shell_to_db.py` build product UI table từ:

- `data/bootstrap/courses.json`
- `data/bootstrap/overviews.json`
- canonical `units.jsonl`

Sinh stable UUID, course section từ lecture group, learning unit slug từ canonical unit id, và product `learning_units` link ngược về `canonical_unit_id`. Tách lớp navigation human-friendly khỏi canonical id ground truth.

### 6.4 Validation & Parity Scripts

`check_canonical_runtime_parity.py`, `check_legacy_*`, `validate_legacy_cleanup_targets.py`. Backend test (`tests/pipeline/*`) cover các script này như production code, không phải notebook ad-hoc.

## 7. Kiến trúc AI

Lớp AI có ba surface runtime chính:

1. Lecture tutor streaming qua `/api/lectures/ask`.
2. AI Learning Copilot qua `/api/agent/chat` và `/api/agent/chat/stream`.
3. AI summary cho assessment qua `/api/assessment/{session_id}/summary`.

### 7.1 Pipeline Lecture Tutor

Triển khai chủ yếu ở `src/services/llm_service.py` và expose qua `src/api/app.py`.

![Sơ đồ AI Tutor](architecture/07-ai-tutor.svg)

Luồng tổng quát:

```text
User question
  -> JWT user extraction when available
  -> lecture/canonical context validation
  -> chat model availability check
  -> PII input sanitization
  -> language normalization
  -> lecture/canonical context fetch
  -> guardrail router scope packet
  -> smart route_question
  -> SIMPLE direct answer or COMPLEX LangGraph path
  -> transcript/context window assembly
  -> optional image/frame context
  -> LangGraph agent with execute_python tool
  -> output PII sanitization
  -> NDJSON streaming to browser
  -> QA history persistence
  -> Langfuse/Prometheus metrics
```

Graph tutor gọn nhẹ:

```text
START -> agent -> tools? -> agent -> END
             \-> give_up -> END
```

Tool support:

- `execute_python(code)` chạy trong `src/services/sandbox.py`: subprocess Python isolated với env `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1` để cap CPU; có timeout và giới hạn output size; không phải REPL persistent.
- Số lần gọi tool có cap để tránh vòng lặp vô hạn.
- Nếu local OpenAI-compatible model không support tool calling, runtime degrade graceful (trả lời không có tool).

System prompt của tutor enforce: scope theo lecture, citation timestamp, kháng prompt injection, trả lời chỉ dựa trên context, output cùng ngôn ngữ với user và sử dụng tool toán/code khi cần.

### 7.2 Pipeline Agentic RAG Copilot

Triển khai chính ở:

- `src/routers/agent.py`
- `src/services/agent_graph_service.py`
- `src/services/agentic_rag_pipeline.py`
- `src/services/agent_tool_nodes.py`
- `src/services/agent_router_factory.py`
- `src/services/agent_structured_router.py`
- `src/prompts/agent/agentic_rag.yaml`

![Pipeline Agentic RAG](architecture/02-agentic-rag-pipeline.svg)

Surface `/api/agent` hỗ trợ:

- chat đồng bộ
- streaming chat NDJSON
- CRUD conversation
- đọc/xóa memory
- tra unit context
- snippet transcript
- search unit
- yêu cầu path
- tiếp tục pending action
- workflow assessment
- start assessment và action request replan

Node trong production graph:

```text
START
  -> route_intent
  -> canonicalize_slots
  -> policy_guard
  -> agentic_rag OR dispatch
  -> await_confirmation? -> commit_action?
  -> END
```

Vẫn còn fallback node để giữ tương thích với test/bootstrap router cũ:

```text
rag_decide_tool -> rag_execute_tool -> rag_observe -> END
```

Các stage cốt lõi của agent:

| Stage | Trách nhiệm |
|---|---|
| Guardrail pre-route | Quyết định scope/safety trước khi trả lời/hành động |
| Route intent | Phân loại mục tiêu user thành business intent |
| Slot canonicalization | Resolve topic, unit id, scope path, xử lý ambiguity |
| Policy guard | Áp ràng buộc action/retrieval |
| Agentic RAG | Think → act → observe → respond theo 1 tool path có grounding |
| Dispatch | Intent ngoài RAG: assessment/replan/path switch |
| Await confirmation | Interrupt LangGraph cho action cần xác nhận |
| Commit action | Validate và áp action đã được phê duyệt |

### 7.3 Lớp Tool của Agent

`AgentToolNodes` expose các internal tool có kiểm soát:

| Nhóm Tool | Mục đích |
|---|---|
| `find_content` | Search canonical unit trong path hiện tại / cho phép |
| `lecture_context` | Lấy summary lecture/unit và context kiểu transcript |
| `user_learning_context` | Lấy progress, current unit, weak area, recent activity |
| `planner_decision` | Giải thích yêu cầu prerequisite/planner |
| `assessment_proposal` | Chuẩn bị workflow/action assessment |
| `replan_proposal` | Render action scope-builder cho replan |
| `path_switch_proposal` | Render action chuyển path |
| prerequisite path action | Build chain prerequisite có thứ tự tới unit mục tiêu |

Lớp tool xử lý rõ ràng:

- search trong path hiện tại vs path mở rộng
- phát hiện match yếu
- card ambiguity
- dựng citation
- action prerequisite path
- chấm chất lượng evidence
- scope chỉ học rồi vs toàn lecture
- fallback learner context cho yêu cầu deictic như "video học gần nhất"

### 7.4 Kiến trúc Prompt

`src/prompts/agent/agentic_rag.yaml` thiết kế module, tách rạch ròi trách nhiệm:

| Module Prompt | Trách nhiệm |
|---|---|
| `route.system` | Phân loại intent và ràng buộc slot/routing |
| `thinking.system` | Memo plan nội bộ, không hiển thị cho user |
| `acting.system` | Chọn đúng 1 tool call |
| `observing.system` | Validate chất lượng evidence từ tool |
| `responding.system` | Quy tắc trả lời cuối có grounding |
| `assistant_help.system` | Trả lời nhẹ kiểu help/greeting/capability |
| `notices` | Copy báo lỗi ổn định |

Pattern thiết kế prompt dễ maintain:

- tách rời trách nhiệm
- output trung gian có cấu trúc
- module prompt tái sử dụng
- policy ngôn ngữ rõ ràng
- kháng prompt injection
- quy tắc trả lời ưu tiên evidence
- tách routing action ra khỏi sinh câu trả lời

### 7.5 Guardrail Router

Triển khai ở `src/services/guardrail_router.py`.

Guardrail router nhận input:

- message của user
- feature type: tutor hoặc agent
- mức/scope id
- summary scope được phép
- KP candidate
- context gần đây
- text đã chọn

Trả về quyết định JSON có kiểu:

```json
{
  "safety_label": "SAFE",
  "topic_label": "ON_TOPIC",
  "action": "ALLOW_LESSON_ANSWER",
  "attack_type": "none",
  "selected_kp_ids": []
}
```

Các action được hỗ trợ:

- `ALLOW_LESSON_ANSWER`
- `SOFT_REFUSE_REDIRECT`
- `ASK_CLARIFY`
- `SAFETY_REFUSE`

Hành vi runtime:

- Ưu tiên gọi endpoint HTTP OpenAI-compatible, kèm header Cloudflare Access (tuỳ chọn).
- Đánh dấu endpoint unhealthy sau khi fail, skip trong giai đoạn cooldown.
- Fallback sang provider/model đã cấu hình.
- Parse/normalize output model về schema Pydantic chặt chẽ.

### 7.6 PII và An toàn

Các path AI dùng `PIIGuardrailService` để sanitize input/output. Guardrail trong prompt tutor và agent thêm các biện pháp chặn:

- rò rỉ prompt ẩn
- override role/system
- override schema
- override scope
- prompt injection từ transcript/OCR/message cũ
- trả lời off-topic không được hỗ trợ
- hallucination ngoài context đã retrieve

### 7.7 Tool nghiên cứu ngoài

Khi user chọn `tool_mode=web/papers` trên Agent UI, agent route qua `src/services/agent_external_research_service.py`:

- DuckDuckGo HTML scrape (không cần API key).
- Semantic Scholar API cho academic paper.
- arXiv query parser.
- Retry/backoff cho transient error.

`agent_external_citation_manager.py` normalize external citation thành cùng structured source-card schema với internal citation, để frontend render thống nhất.

### 7.8 Agent Service Map

Agent surface dùng 37 file service riêng (`src/services/agent_*.py`). Sections 7.1–7.7 mô tả các module trọng tâm; bảng dưới liệt kê đầy đủ để tra cứu.

| Service | Vai trò |
|---|---|
| `agent_action_service.py`, `agent_action_commit_service.py` | Pending action lifecycle, idempotent commit |
| `agent_assessment_workflow.py` | Workflow tạo/bắt đầu assessment từ agent |
| `agent_checkpointer_factory.py` | LangGraph Postgres checkpointer cho thread state |
| `agent_context_service.py`, `agent_unit_context_service.py` | Resolve scope, allowed courses, unit context |
| `agent_conversation_service.py`, `agent_title_generator.py` | CRUD conversation, auto-gen title |
| `agent_evidence_quality.py` | Chấm chất lượng evidence từ tool output |
| `agent_external_research_service.py`, `agent_external_citation_manager.py` | Web/papers tool mode (xem 7.7) |
| `agent_graph_router.py`, `agent_graph_service.py`, `agent_graph_contracts.py`, `agent_router_factory.py` | LangGraph runtime + routing factory |
| `agent_lock_service.py` | Distributed lock cho graph run (Redis) |
| `agent_memory_compaction_service.py`, `agent_thread_memory_state.py`, `agent_tutor_memory_service.py` | Compact memory đa lượt, persist thread state |
| `agent_navigation_service.py`, `agent_path_catalog.py`, `agent_path_switch_service.py` | Path catalog + path-switch action |
| `agent_pending_action_decision.py`, `agent_pending_action_janitor.py` | Quyết định pending action, dọn dẹp expired |
| `agent_policy_service.py` | Policy guard (xem 7.2) |
| `agent_prerequisite_path_service.py` | Build chain prerequisite theo edge có scope |
| `agent_prompt_manager.py` | Load + cache prompt module từ YAML |
| `agent_query_normalizer.py`, `agent_slot_resolver.py` | Chuẩn hoá query, resolve slot/ambiguity |
| `agent_requirement_service.py` | Kiểm tra điều kiện trước action |
| `agent_response_composer.py` | Compose answer cuối kèm citation/action |
| `agent_search_service.py`, `agent_search_scope_service.py` | Canonical search trong scope (current/expanded) |
| `agent_structured_router.py` | Intent router output Pydantic schema |
| `agent_tool_nodes.py` | Tool node (xem 7.3) |
| `agent_user_learning_context_service.py` | Pull learner state cho tool `user_learning_context` |
| `agentic_rag_pipeline.py`, `agentic_rag_tools.py`, `agentic_rag_contracts.py` | RAG pipeline + contract Pydantic |
| `agent_error_codes.py` | Mã lỗi chuẩn cho agent response |

## 8. Đánh giá, Mastery và Planner

Subsystem assessment có 3 runtime tách biệt (Placement, Quiz, Module Test) cùng dùng canonical item bank nhưng khác selection strategy và scoring scope. Mastery update và Planner đứng sau, share cùng learner state.

![Sơ đồ onboarding & assessment](architecture/06-onboarding-assesment.svg)

### 8.1 Placement / Assessment Runtime

Triển khai chính ở `src/services/assessment_service.py`.

Luồng start:

```text
learning_unit_ids hoặc canonical_unit_ids
  -> resolve canonical unit id
  -> load question pool theo phase
  -> áp depth policy
  -> chọn strategy
  -> tạo Session(session_type=assessment)
  -> trả về canonical question
```

Depth policy:

| Depth | Số câu tối đa | Câu/unit | Độ khó | Item application |
|---|---:|---:|---|---|
| quick | 15 | 2 | easy, medium | không |
| standard | 30 | 3 | easy, medium, hard | không |
| deep | 50 | 5 | easy, medium, hard | có |

Luồng submission:

```text
answer kèm canonical_item_id
  -> validate canonical item
  -> ghi interaction
  -> cập nhật KP mastery
  -> tính score theo unit
  -> phân loại skip/review/relearn
  -> lưu kết quả placement assessment
  -> trả về kết quả kèm weak KP và quyết định topic
```

Ngưỡng quyết định:

- `skip`: score ≥ 70%
- `review`: score ≥ 50%
- `relearn`: score < 50%

### 8.2 Runtime Quiz

`src/services/quiz_service.py` xử lý inline quiz cuối learning unit:

- Scope hẹp theo `canonical_unit_id` hiện tại.
- Selection ưu tiên item `phase=quiz` trong `item_phase_map`.
- Ghi `interactions` với `session_type=quiz`.
- Cập nhật mastery qua cùng path canonical (`update_kp_mastery_from_item`).

### 8.3 Runtime Module Test

`src/services/module_test_service.py` xử lý module test xuyên section:

- Scope rộng theo nhóm unit thuộc module.
- Selection ưu tiên item `phase=module_test`.
- Snapshot mastery state làm baseline để planner so sánh trước/sau module.

### 8.4 Tương thích Placement (legacy)

`src/services/placement_assessment_service.py` wrap canonical assessment cho legacy placement API. Resolve product learning unit, filter unit không có canonical question, start deep placement, map canonical question về topic unit id. `placement_lite_service.py` là biến thể nhẹ cho onboarding quick screen.

### 8.5 Cập nhật Mastery

Service assessment gọi `update_kp_mastery_from_item()` khi tính năng ghi interaction canonical được bật. Mastery của học viên được persist vào `learner_mastery_kp` với các cột:

- `theta_mu`
- `theta_sigma`
- `mastery_mean_cached`
- `n_items_observed`
- `updated_by`

Planner đọc bằng ước lượng kiểu LCB qua `estimate_mastery_lcb_on_read()` để tránh tin tưởng quá mức khi evidence còn ít.

Pipeline calibration đứng sau: `src/services/item_calibration_service.py` cập nhật `item_calibration` (prior + tham số calibrated `a`, `b`, `c`) từ lịch sử response, có audit qua `calibration_runs` và `item_calibration_history` cho rollback.

### 8.6 Planner Learning Path

Triển khai chính ở `src/services/recommendation_engine.py`.

Luồng planner:

```text
selected_course_ids
  -> các learning unit product liên kết
  -> canonical unit và row unit-KP
  -> snapshot KP mastery
  -> kết quả placement
  -> ưu tiên unit theo schema v2
  -> phân loại action
  -> sắp xếp Phase A/B
  -> persist plan_history và rationale_log
  -> cập nhật planner_session_state
```

Các quyết định planner gồm:

| Action | Ý nghĩa |
|---|---|
| `skip` | Unit đã thành thạo / có thể bỏ qua |
| `quick_review` | Khuyến nghị ôn nhanh |
| `standard_learn` | Học bình thường |
| `deep_practice` | Cần luyện thêm |
| `remediate` | Cần học bù lại |

Planner cân nhắc các yếu tố:

- quyết định placement
- mastery LCB
- segment hidden/reference/logistics
- KP gateway quan trọng
- quiz có sẵn hay không
- điểm salience
- interleaving giữa các khóa
- chính sách khoá Phase A/B
- unit đã waive và progress record

### 8.7 Hệ thống Replan

Replan không chỉ là agent action card mà là một subsystem độc lập với router + 7 service file.

| Endpoint | Service hỗ trợ | Mục đích |
|---|---|---|
| `POST /api/replan/analyze` | `replan_service.py`, `replan_llm_extractor.py`, `replan_keyword_planner.py` | Parse knowledge claim free-text → topic + scope candidate |
| `POST /api/replan/assessment/start` | `replan_service.py`, `replan_question_scope.py`, `replan_unit_recommender.py`, `replan_unit_discovery.py` | Scoped assessment dựa trên claim, reuse `assessment_service` |

Phụ thuộc: `replan_prerequisite_suggestions.py` gợi ý prerequisite ưu tiên dựa trên KP mastery thấp. Kết quả replan có thể trigger planner re-run qua action commit.

### 8.8 Service Review

`src/services/review_service.py` chọn item ôn tập từ canonical bank theo tín hiệu:

- Weak: `mastery_mean_cached < 0.6`
- Stale: `updated_at > 7 days`
- Fallback theo count khi không đủ item.

Output là pool ôn tập tái dùng cùng UI quiz, không tạo session_type riêng.

## 9. Kiến trúc Frontend

### 9.1 Routing Next.js

Frontend dùng App Router. Các nhóm route chính:

- public landing: `frontend/app/page.tsx`
- auth: `login`, `register`, `forgot-password`, `reset-password`
- protected dashboard/profile/history
- catalog khóa học và chi tiết khóa
- màn hình learning unit
- onboarding nhiều bước (goal/deadline → giờ/tuần → trình độ → chọn khóa → sẵn sàng placement)
- assessment và kết quả
- quiz/module test
- learning path
- AI agent
- admin dashboard

### 9.2 Lớp API Client

`frontend/lib/api.ts` định nghĩa Axios instance dùng chung.

Hành vi chính:

- Browser dùng rewrite proxy của Next.js cho `/api/*`.
- Server-side dùng `API_INTERNAL_URL` mặc định trỏ tới backend container.
- Access token Bearer attach từ cookie.
- Response 401 trigger luồng refresh token (đã dedupe).
- Refresh fail → xoá token và redirect login.
- Client domain có kiểu wrap call assessment, course, content, quiz, module test, history, auth và learning session.

`frontend/features/agent/api.ts` thêm streaming dạng fetch cho `/api/agent/chat/stream`, gồm retry refresh token và parse NDJSON theo dòng.

### 9.3 Quản lý State

Store Zustand đảm nhiệm:

| Store | Trách nhiệm |
|---|---|
| `authStore` | Trạng thái user, login/register/logout, lịch refresh token |
| `onboardingStore` | State onboarding nhiều bước |
| `courseCatalogStore` | Cache catalog khóa học |
| `learning-path/store` | Profile planner, danh sách path item, summary và state UI đang chọn |

Auth chỉ persist object user vào localStorage. Token sống trong cookie qua `js-cookie`.

### 9.4 UI học

Màn hình học gồm:

- `LearningPageScreen`
- `LearningUnitShell`
- sheet mobile cho tutor/lesson/key-ideas
- tutor inline trong context
- hook cập nhật progress

Màn hình lưu metadata learning unit đang active vào session storage để agent và route context resolve được tham chiếu deictic kiểu "bài này" hoặc "video gần nhất".

### 9.5 UI Learning Path

`LearningPathShell` load path từ planner và hỗ trợ:

- xem graph qua `RoadmapCanvas` (dynamic import)
- fallback timeline cho mobile
- `PlannerHeader`
- banner thay đổi profile
- drawer unit
- luồng status/update

Phần trình bày graph/timeline tách khỏi logic planner; nguồn sự thật vẫn là `plan_history` và progress record ở backend.

### 9.6 UI Agent

`AgentChatPage` là interface copilot đầy đủ:

- sidebar conversation kèm create/rename/delete
- turn assistant streaming có activity status / thought summary
- chọn model
- toggle tool mode giữa course vs web/papers
- citation / source card
- panel chi tiết source
- card prerequisite path
- action card cho assessment/replan/path switch
- retry cho lỗi agent thoáng qua
- drawer source và history cho mobile

Frontend consume citation và action dưới dạng dữ liệu có cấu trúc. Text trả lời của assistant không cần chứa link thô vì source/action card render navigation riêng.

## 10. Kiến trúc bảo mật

### 10.1 Xác thực

Luồng auth:

```text
register/login
  -> backend phát access + refresh token
  -> frontend lưu access/refresh vào cookie
  -> Axios attach Bearer access token
  -> 401 trigger refresh
  -> logout revoke/denylist token và clear state client
```

Auth backend dùng:

- JWT access/refresh tokens (`python-jose`).
- bcrypt password hashing (`passlib`).
- Token denylist: `src/services/token_denylist.py` set Redis key `revoked:{jti}` với TTL = thời gian sống còn lại của token. Logout/refresh đẩy access token cũ vào denylist. `src/services/token_guard.py` wrap kiểm tra denylist trong auth dependency.
- Rate limit: `src/middleware/rate_limit.py` Redis fixed-window counter cho `/api/auth/login` và `/api/auth/password-reset/request`, limit từ settings.
- Password reset tokens và email service (xem 10.5).

### 10.2 Truy cập dữ liệu & Scope

Agent không chấp nhận user id tuỳ ý từ frontend cho learner context. User id được lấy từ dependency đã xác thực, scope khóa/path cho phép được truyền qua `AgentContextResolver`.

Endpoint course/agent validate:

- ownership conversation
- scope canonical unit candidate
- danh sách course id cho phép
- ownership pending action
- ràng buộc theo path hiện tại

### 10.3 Bảo mật Asset

`src/api/app.py` phục vụ `/data/{asset_path}` ở mode local và bảo vệ video/slide/transcript khóa học bằng xác thực signed URL cho các prefix đã biết. Mode asset production hỗ trợ signed URL S3 + CloudFront qua settings và service asset delivery/signing.

### 10.4 An toàn AI

Các biện pháp kiểm soát:

- sanitize PII input/output
- guardrail router trước câu trả lời tutor/agent
- prompt scope chặt
- kháng prompt injection
- validate schema output cho router
- yêu cầu citation có grounding
- fallback từ chối/làm rõ
- xác nhận action trước khi mutate workflow

### 10.5 Reset Mật khẩu & Email

- `src/models/password_reset.py` — table `PasswordResetToken` với `token_hash`, `expires_at`, `used_at`, `requested_ip`.
- `src/services/password_reset_service.py` — sinh + hash token, validate, mark used (one-shot).
- `src/services/email_service.py` — SMTP (Gmail app password), HTML template, URL gen tới frontend reset page.
- Flow: request → email link → frontend `reset-password` page → backend verify token + đổi password + mark used. Token rate-limit qua `/api/auth/password-reset/request`.

## 11. Observability

### 11.1 Langfuse

`src/core/observability.py` khởi tạo Langfuse khi có key. Hỗ trợ:

- callback handler LangChain
- root span và observation lồng nhau
- propagate metadata user/session/tag
- tạo feedback score cho câu trả lời tutor đã được rate
- no-op khi chưa cấu hình

Call tutor và assessment summary attach metadata: feature, route, user id, session id, lecture id, context binding, assessment session id.

### 11.2 Prometheus

Instrumentation Prometheus được đăng ký trong `src/api/app.py` qua `setup_prometheus(app)`. Histogram chuyên cho tutor:

- thời gian tới sự kiện status đầu tiên
- thời gian tới chunk câu trả lời đầu tiên
- tổng thời gian stream tutor

Label gồm loại route và có image context hay không.

### 11.3 Logs

Backend sử dụng:

- JSON access log qua `AccessLogMiddleware`
- log tutor dạng text và JSONL trong `logs/`
- app logger warning/error
- dashboard observability cho admin

Repo cũng có hook log prompt/session cho AI coding agent ở `.codex`, `.claude`, `.cursor`, `.github/hooks`, v.v. Các file này ghi `.ai-log/session.jsonl` (đã gitignore).

### 11.4 Admin Observability API

`src/routers/admin.py` expose 13 endpoint dành cho admin (gated bởi dependency `require_admin`, role enum trong user model).

| Endpoint | Mục đích |
|---|---|
| `GET /api/admin/stats/overview` | Tổng quan user / session / QA |
| `GET /api/admin/model/current`, `/model/health` | Trạng thái LLM model registry |
| `GET /api/admin/users` | Danh sách user (paginate) |
| `GET /api/admin/signups/timeseries` | Đăng ký mới theo thời gian |
| `GET /api/admin/llm/recent`, `/llm/stats` | Tail `logs/qa_history.jsonl`, thống kê LLM call |
| `GET /api/admin/logs/events`, `/logs/summary` | Tail access log JSON |
| `GET /api/admin/feedback/stats`, `/feedback/recent-negative` | Rating Q&A, feedback âm |
| `GET /api/admin/system/health` | CPU / RAM / Disk / DB / Redis liveness |
| `GET /api/admin/traffic/summary` | Query Prometheus rate cho traffic summary |

Tách rời với observability stack ngoài app (xem 12.5).

## 12. Kiến trúc triển khai

### 12.1 Docker Compose Local

`docker-compose.yml` định nghĩa:

- `db`: PostgreSQL 16 + pgvector
- `redis`: Redis 7 có password và policy memory LRU
- `backend`: FastAPI + uv, chạy Alembic upgrade, hot reload
- `frontend`: Next.js dev server (polling cho Windows)

Frontend dev proxy `/api/*` và `/data/*` về backend.

### 12.2 Container Image

Dockerfile backend:

- Python 3.12 slim
- copy uv từ image uv chính thức
- `uv sync --frozen --no-install-project --no-dev`
- copy app vào `/app`
- `PYTHONPATH=/app`
- start uvicorn ở `${PORT:-8000}`

Dockerfile frontend:

- Node 20 Alpine
- stage dependency với `npm ci`
- stage build với output Next standalone
- runner tối giản, chạy bằng non-root user
- healthcheck tới `/api/health`
- start `node server.js`

### 12.3 Path Production trên AWS ECS

`deploy-ecs/` document một bộ deploy AWS managed đầy đủ:

- cluster ECS Fargate
- service frontend và backend tách riêng
- ALB public route hostname app và API
- repository ECR
- RDS PostgreSQL
- ElastiCache Redis/Valkey
- S3 bucket private
- CloudFront cho asset
- Secrets Manager
- Route 53 + ACM
- CloudWatch
- AWS Budgets
- module Terraform cho network/security/database/asset/ECS/observability

Quy tắc production quan trọng (theo doc deploy): backend không được proxy byte video. Browser phải nhận asset/video qua CloudFront.

### 12.4 CI/CD

Repo có workflow GitHub Actions đang chạy và gói review ECS ở `cicd/`.

Thiết kế CI/CD hiện tại:

- Terraform giữ hạ tầng ổn định.
- GitHub Actions chịu trách nhiệm release app sau khi service tồn tại.
- Image dùng tag SHA immutable.
- Task definition ECS render từ template.
- Migration chạy như one-off ECS task, không phải startup của service long-running.
- ALB smoke check gate cho deployment.

### 12.5 Topology Migration Alembic

Repo có 41 migration tại `alembic/versions/` với nhiều multi-head merge — biểu hiện của development song song theo nhánh chức năng. CI cần `alembic check` (head count = 1) trước khi merge PR.

| Period | Nhánh chính | Output |
|---|---|---|
| 04-11 → 04-14 | Initial schema + rating | `initial_schema`, `add_rating_to_qa_history` |
| 04-15 → 04-17 | Checkpoint state, mastery history | `add_checkpoint_state`, `add_mastery_history` |
| 04-18 | Schema v1 + course platform + pgvector + qa_context | 4 head + merge `course_platform_and_mastery`, `schema_qa_heads` |
| 04-19 | Knowledge graph init + drift fix | `kg_init`, `kg_schema_drift_fix`, `merge_schema_v1_and_pgvector`, `merge_final_heads` |
| 04-23 | Canonical content + legacy archive/drop + numeric difficulty | `canonical_content_tables`, `archive_legacy_runtime_tables`, `drop_legacy_runtime_tables` |
| 04-25 → 04-28 | Placement + experience level + CAT fields + audit | `placement_asmnt`, `experience_level`, `merge_schema_v2_and_cat_fields` |
| 04-29 → 05-01 | Calibration + agent conversations + agent graph runtime | `create_calibration_tables`, `agent_conversations`, `agent_graph_runtime` |
| 05-02 → 05-05 | User role + Langfuse trace + password reset | `add_user_role`, `add_langfuse_trace_fields`, `merge_agent_admin_heads`, `merge_runtime_lf_heads`, `add_password_reset_tokens` |
| 05-12 | Localized content | `localized_content` |

Multi-head merge tiêu biểu: `merge_schema_v1_and_pgvector`, `merge_course_platform_and_mastery_heads`, `merge_final_heads`, `merge_schema_v2_and_cat_fields`, `merge_runtime_lf_heads`, `merge_agent_admin_heads`.

### 12.6 Stack Observability của Admin Dashboard

`admin-dashboard/` chứa stack quan sát ngoài app, tách rời với app stack chính, định nghĩa trong `docker-compose.observability.yml`:

| Component | Vai trò |
|---|---|
| Grafana | Dashboard, alert |
| Loki | Log aggregation |
| Promtail | Log shipper từ container app sang Loki |
| Prometheus | Metric scrape từ `/metrics` của FastAPI |
| Scripts | Bootstrap dashboard, datasource |

Trên prod ECS, vai trò này thay bằng CloudWatch Logs + CloudWatch Metrics + Grafana cloud (theo `deploy-ecs/` docs).

## 13. Testing và Chất lượng

Repo có độ phủ test rộng:

- 195 test backend ở `tests/`
- 94 test frontend ở `frontend/tests/`
- backend: test unit, integration, contract, repository, service và pipeline
- frontend: test unit, route và E2E
- check head Alembic
- test agent graph/router/eval
- test dataset/build cho guardrail router
- test placement/IRT/calibration
- test parity/import canonical runtime
- test auth/security/rate-limit

Các lệnh validation thường dùng (theo doc repo):

```bash
uv run python -m src.scripts.pipeline.import_canonical_artifacts_to_db --validate-only
uv run python -m src.scripts.pipeline.check_canonical_runtime_parity
uv run pytest tests/ -q
npm --prefix frontend run type-check
npm --prefix frontend run test
```

## 14. Các luồng runtime chính

### 14.1 Luồng học viên mới

```text
Register/Login
  -> Onboarding nhiều bước (goal/deadline -> giờ/tuần -> trình độ -> chọn khóa)
  -> Persist GoalPreference
  -> Placement assessment khởi động từ canonical question bank
  -> Ghi interaction và cập nhật KP mastery
  -> Quyết định placement skip/review/relearn
  -> Sinh learning path từ canonical unit và mastery
  -> Học viên mở unit
  -> Cập nhật progress/session state
  -> Quiz/module test tiếp tục cập nhật mastery
  -> Planner có thể chạy lại / replan
```

### 14.2 Luồng học khóa

```text
Catalog khóa học
  -> Overview khóa
  -> Quyết định start khóa
  -> Route learning unit
  -> LearningUnitShell hiển thị text/video/asset
  -> Cập nhật progress qua learning-session
  -> Tutor inline trả lời trong context unit/lecture
  -> Quiz có sẵn khi canonical item bank đủ item phù hợp
```

### 14.3 Luồng câu hỏi Agent

```text
Message của user trên Agent UI
  -> frontend gửi stream NDJSON kèm route context
  -> backend xác thực user
  -> resolve allowed/current course
  -> load conversation và memory
  -> sanitize PII
  -> chuẩn hoá ngôn ngữ
  -> guardrail router
  -> structured intent router
  -> slot resolver
  -> policy guard
  -> thực thi tool hoặc dispatch action
  -> quan sát evidence
  -> compose response cuối
  -> persist citation/action
  -> stream chunk/done về frontend
```

### 14.4 Luồng Replan/Action

```text
Agent phát hiện request_replan/request_path_switch/assess_knowledge
  -> trả về action proposal
  -> persist pending action kèm idempotency key
  -> frontend render action card
  -> user approve/reject/edit
  -> /api/agent/actions/continue resume graph
  -> backend validate ownership và status
  -> service commit action áp mutation hoặc trả lỗi
```

## 15. Điểm mạnh Engineering

1. Tách rạch ròi giữa product shell và canonical learning runtime.
2. Import artifact idempotent, validate count theo manifest.
3. Pipeline AI modular: guardrail, route, slot, policy, tool, observe, respond.
4. Prompt tách theo trách nhiệm, không phải khối monolith.
5. Action agent có thể resume và được persist, giảm rủi ro mutation ngoài ý muốn.
6. Frontend consume citation/action dạng dữ liệu có cấu trúc, không parse link từ text.
7. Langfuse và Prometheus tích hợp nhưng LLM call không phụ thuộc vào availability của observability.
8. Test phủ service, repository, contract API, script pipeline và route behavior frontend.
9. Thiết kế deploy ECS tách rời hạ tầng, release app, migration task và smoke check.
10. Hệ thống giữ bảng audit cho planner, calibration, ingest, edge graph bị prune và pending action.

## 16. Hạn chế hiện tại & Rủi ro kỹ thuật

| Khu vực | Hạn chế / Rủi ro | Ghi chú |
|---|---|---|
| Calibration | Hạ tầng IRT/CAT đã có nhưng độ chín của calibration với response thật phụ thuộc khối lượng dữ liệu production | `item_calibration` đã có prior và field calibrated |
| Phạm vi nội dung | Runtime hiện xoay quanh asset kiểu CS230/CS224n/CS231n | Mở rộng domain cần sinh canonical artifact |
| Path tutor legacy | Lecture tutor vẫn dùng path legacy `/api/lectures/ask` song song `/api/agent` | Được giữ qua compatibility mapping và context binding |
| Streaming async | Tutor dùng LangGraph stream sync + async DB helper qua engine NullPool riêng | Vòng tránh lỗi event loop reuse nhưng phức tạp hơn |
| External research | Agent có tool mode external (DuckDuckGo/Semantic Scholar/arXiv) — production-grade nhưng phụ thuộc public endpoint, cần monitor rate limit |
| Availability model | Nhiều feature degrade/fallback khi thiếu credential model hoặc endpoint local | Frontend có check availability |
| Asset delivery | Mode `/data` local ở dev và CloudFront ở prod phải đồng bộ | Prod không proxy video qua backend |
| Drift prompt | Prompt modular nhưng vẫn phức tạp; thay đổi cần eval-test | Doc/test golden eval hiện có hỗ trợ |

## 17. Đề xuất bước Engineering tiếp theo

1. Thêm changelog có version cho từng module prompt YAML và liên kết với golden eval.
2. Mở rộng eval agent tự động cho query deictic/current-lesson tiếng Việt.
3. Đưa validation canonical artifact vào CI trước khi deploy.
4. Thêm panel dashboard cho sức khỏe calibration assessment và phân bố exposure item.
5. Thống nhất tutor legacy và routing context của agent để toàn bộ tutor dùng chung contract citation/action.
6. Thêm dashboard SLO production cho first-token latency, tỉ lệ stream hoàn tất, tỉ lệ guardrail refuse và tỉ lệ trả lời không có source.
7. Document chính xác chuỗi DVC pull/materialize cho môi trường production mới.
8. Thêm load test cho endpoint streaming và rate limit dựa trên Redis.

## 18. Bản đồ tham chiếu cấp File

| Khu vực | File quan trọng |
|---|---|
| App bootstrap | `src/api/app.py`, `main.py`, `src/config.py`, `src/database.py` |
| Auth/security | `src/routers/auth.py`, `src/services/auth_service.py`, `src/services/token_denylist.py`, `src/middleware/rate_limit.py` |
| Course platform | `src/routers/courses.py`, `src/services/course_catalog_service.py`, `src/services/learning_unit_service.py`, `src/models/course.py` |
| Canonical content | `src/models/canonical.py`, `src/repositories/canonical_content_repo.py`, `src/scripts/pipeline/import_canonical_artifacts_to_db.py` |
| Assessment | `src/routers/assessment.py`, `src/services/assessment_service.py`, `src/services/canonical_question_selector.py`, `src/services/canonical_mastery_service.py` |
| Planner | `src/routers/learning_path.py`, `src/services/recommendation_engine.py`, `src/services/canonical_planner_service.py` |
| Agent | `src/routers/agent.py`, `src/services/agent_graph_service.py`, `src/services/agent_tool_nodes.py`, `src/prompts/agent/agentic_rag.yaml` |
| Tutor | `src/services/llm_service.py`, `src/services/router.py`, `src/services/sandbox.py`, `src/services/lecture_scope_service.py` |
| Guardrails | `src/services/guardrail_router.py`, `src/services/guardrails/*`, `src/prompts/agent/guardrail_router.yaml` |
| Observability | `src/core/observability.py`, `src/middleware/prometheus.py`, `src/middleware/request_logger.py` |
| Frontend API | `frontend/lib/api.ts`, `frontend/features/agent/api.ts` |
| Frontend agent | `frontend/features/agent/components/AgentChatPage.tsx` |
| Frontend learning path | `frontend/features/learning-path/*` |
| Frontend learning UI | `frontend/components/learn/*`, `frontend/app/(protected)/courses/[courseSlug]/learn/[unitSlug]/page.tsx` |
| Deployment | `docker-compose.yml`, `Dockerfile`, `frontend/Dockerfile`, `deploy-ecs/*`, `cicd/*` |
| Tests | `tests/`, `frontend/tests/` |
| Admin & ops | `src/routers/admin.py`, `admin-dashboard/`, `docker-compose.observability.yml` |
| Replan / Review | `src/routers/replan.py`, `src/routers/review.py`, `src/services/replan_*.py`, `src/services/review_service.py` |
| Quiz / Module Test | `src/routers/quiz.py`, `src/routers/module_test.py`, `src/services/quiz_service.py`, `src/services/module_test_service.py` |
| Onboarding & Email | `src/routers/onboarding.py`, `src/services/onboarding_service.py`, `src/services/email_service.py`, `src/services/password_reset_service.py`, `src/models/password_reset.py` |
| Mô hình lỗi | `src/exceptions.py`, `src/exception_handlers.py` |
| Migration | `alembic/versions/` (41 file, multi-head merge) |
| Prompt offline | `prompts/1_question_bank.txt`, `prompts/2_item_calibration.txt`, `prompts/3_quality_assurance.txt`, `prompts/4_item_phase_map.txt`, `prompts/lecture_extraction_prompt.txt` |
| Diagram kiến trúc | `architecture/01-system-overview.svg`, `architecture/02-agentic-rag-pipeline.svg`, `architecture/06-onboarding-assesment.svg`, `architecture/07-ai-tutor.svg`, `architecture/08-data-flywheel.svg`, `architecture/ux.md` |

---

## 19. Coverage Audit

Báo cáo này phản ánh tình trạng codebase tại commit hiện tại sau khi audit theo function area. Bảng dưới ghi nhận coverage để đối chiếu khi codebase thay đổi.

| Function area | Coverage | Section |
|---|---|---|
| Backend runtime + mô hình lỗi | ✅ | §4 |
| Kiến trúc dữ liệu (model) | ✅ | §5 |
| Pipeline offline P1→P5 + DVC | ✅ | §6 |
| Pipeline AI (tutor, agent, guardrail) + 37 agent service | ✅ | §7 |
| Assessment / Quiz / Module Test / Placement / Replan / Review / Planner | ✅ | §8 |
| Frontend (App Router, state, agent UI, learning UI) | ✅ | §9 |
| Bảo mật (JWT, denylist, rate limit, password reset, asset signing) | ✅ | §10 |
| Observability (Langfuse, Prometheus, admin API, ops stack) | ✅ | §11 |
| Triển khai (Docker, ECS, CI/CD, topology Alembic, admin-dashboard) | ✅ | §12 |
| Testing | ✅ | §13 |
| Luồng runtime | ✅ | §14 |
| Điểm mạnh / Rủi ro / Bước tiếp theo | ✅ | §15–17 |

Nguyên tắc maintain: mỗi PR thêm router/service/migration cần cập nhật section tương ứng + `§18 Bản đồ tham chiếu`. Nếu cấu trúc thay đổi lớn (ví dụ tách Replan thành micro-service riêng, hoặc gộp legacy lecture tutor vào `/api/agent`), refactor section thay vì thêm phụ lục.
