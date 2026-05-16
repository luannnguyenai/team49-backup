# Weekly Journal

Ghi lại hành trình xây dựng sản phẩm mỗi tuần — những gì đã làm, học được gì, AI giúp như thế nào.

---

## Tuần 1 — 06/04/2026

**Thành viên:** Nguyễn Duy Minh Hoàng, Nguyễn Đôn Đức, Nguyễn Lê Minh Luân

### Đã làm
- **Project scaffolding + Gemini LLM integration** (Rin): Khởi tạo cấu trúc project, tích hợp Gemini API, chuyển đổi backend sang **Real-time Streaming** bằng `StreamingResponse` (Server-Sent Events). Thêm architecture docs (`docs/architecture-flow.png`).
- **Visual Context (Multi-modal)** (Rin): Triển khai lấy frame trực tiếp qua Canvas HTML5 gửi cho Gemini API. Docker containerization (`Dockerfile`, `docker-compose.yml`) hoàn chỉnh.
- **Markdown + LaTeX/KaTeX** (Rin): Tích hợp `marked.js` và `KaTeX` vào giao diện chat thời gian thực. Chuẩn hóa timestamp sang `HH:MM:SS`.
- **Hệ thống log song song** (Rin): Ghi `app.db` (SQLite) + file `logs/qa_history.log` (JSON). Thêm `sanitize_title` để chuẩn hóa tiêu đề bài giảng trong dropdown.
- **Antigravity hooks & crawl pipeline** (Đức): Setup log hooks cho Antigravity tool (`setup hooks`, `fix: add log hooks for antigravity`), xây dựng crawler data script, fix crawl pipeline.
- **Login UI** (Đức): Tạo giao diện đăng nhập frontend (`feat: ui login`).
- **Backend adaptive learning integration** (Luân): Tích hợp các tính năng adaptive learning (quiz, learning paths, module tests) vào backend (`feat: Integrated adaptive learning features`). Xây dựng infrastructure management scripts.

### Khó nhất tuần này
- **Streaming & The Thinking Component**: Quản lý state của luồng stream khi `gemini-3-flash-preview` trả về các chunks. Giải quyết vấn đề block luồng khi gặp lỗi (Timeout/API error) từ phía server mà UI không bị treo cứng.
- **CORS vs Multi-modal**: Ý định dùng YouTube Player IFrame bị chính sách CORS của trình duyệt cản trở quyết liệt, không cho phép thẻ `<canvas>` trích xuất dữ liệu ảnh pixel để gửi cho LLM. Do đây là khả năng cốt lõi của tính năng "Gia sư đọc slide", mọi hướng đi phụ thuộc nền tảng thứ ba đành bị loại bỏ.

### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Antigravity (Gemini 3.1 Pro) | Lên cấu trúc logic Streaming Generator, sửa bug ghép Yield Chunk, thiết kế Javascript bắt sự kiện SSE ở Frontend | Xây dựng thành công tính năng AI Chat streaming kết hợp LaTeX toán học cực kỳ ổn định ngay trong 1 session code |

### Học được
- Gemini stream thought dễ conflict lỗi.
- Khi xây dựng hệ thống GenAI có cơ chế "Thị giác máy tính / Phân tích nội dung tĩnh", việc giữ file Media thẳng trên Local Data File/S3 có CORS tĩnh mang lại uy quyền tuyệt đối cho việc lập trình Frontend AI mà không e ngại "Security Policy" đánh chặn oan ức từ các nền tảng video (như YouTube).

### Nếu làm lại, sẽ làm khác
- Thiết lập hệ thống log ghi file `logs/*.log` song song với SQLite DB ngay từ đầu. Stream trả về từng phần nên nếu đứt ở phân đoạn nào, file vật lý sẽ phơi bày rõ ràng nhất thay vì việc Debug Console Browser khó khăn.

---

## Tuần 2 — 08/04/2026

**Thành viên:** Nguyễn Duy Minh Hoàng, Nguyễn Đôn Đức, Nguyễn Lê Minh Luân

### Đã làm
- **Di cư dữ liệu CS231N** (Rin): Chuyển đổi từ CS224N sang Stanford CS231N (Spring 2025) — update ingestion service cho JSON ToC, batch ingestion script, fix lỗi ToC và Transcript không nhất quán.
- **Chuẩn hóa mốc thời gian** (Rin): Toàn bộ hệ thống (Context & AI Response) sử dụng định dạng `HH:MM:SS`. Thêm `sanitize_title` tự động làm sạch tiêu đề bài giảng.
- **Dockerization** (Rin): Hoàn thiện Dockerfile (tối ưu bằng `uv`) và `docker-compose.yml` — chạy FastAPI Backend song song chỉ với 1 lệnh. Fix volume mapping cho 4.5GB video và SQLite DB.
- **Prompt Engineering** (Rin): Lưu bộ Prompt "expert analyzer" vào `prompts/` cho việc trích xuất nội dung bài giảng chất lượng cao.
- **Activity logging hook** (Rin): Thêm activity logging hook (`log_hook.py`) để track Antigravity tool events.
- **Crawl data & Docker fixes** (Đức): Fix script crawl data, fix Antigravity hook relative paths, fix docker compatibility (linux/windows), thêm Docker init script nhanh.
- **Backend Auth + AI Tutor page** (Luân): Thêm auth endpoints (login/register/refresh/`/users/me`), seed endpoint, frontend AI Tutor page với video player + chat. Fix proxy rewrite `/data` cho video serving.

### Khó nhất tuần này
- **Data Adaptation**: Xử lý sự khác biệt giữa các nguồn dữ liệu trích xuất (có những bài giảng ToC bị trống hoặc format không chuẩn). Đã giải quyết bằng cách thêm `try-except` trong script ingestion và tạo bộ lọc `sanitize_title`.
- **Docker Volume Mapping**: Cấu hình volume cho 4.5GB video và Database SQLite để đảm bảo dữ liệu không bị mất khi container khởi động lại nhưng cũng không làm phình dung lượng Docker Image.

### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Antigravity (Gemini 3.1 Pro) | Refactor toàn bộ Ingestion service, xử lý logic merge branch, lập kế hoạch Docker hóa và chuẩn hóa Prompt | Hệ thống chạy ổn định trên container, nạp dữ liệu từ 1-9 mượt mà, fix triệt để lỗi crash giao diện |

### Học được
- Việc chuẩn hóa định dạng thời gian ngay từ khâu context giúp AI giảm thiểu sai số (hallucination) khi trích dẫn mốc thời gian.
- Dockerizing giúp loại bỏ hoàn toàn vấn đề "chạy trên máy tôi được nhưng máy bạn thì không" khi làm việc nhóm.

### Nếu làm lại, sẽ làm khác
- Thiết lập một cấu trúc thư mục Google Drive dùng chung ngay từ đầu để đồng bộ video bài giảng, tránh việc mỗi thành viên phải tự tìm kiếm và tải riêng lẻ.

---

## Tuần 3 — 11/04/2026

**Thành viên:** Nguyễn Duy Minh Hoàng, Nguyễn Đôn Đức, Nguyễn Lê Minh Luân

### Đã làm
- **Smart Router & Guardrails** (Rin): Thay thế binary intent guardrail bằng **3-way Smart Router** (SIMPLE / COMPLEX / BLOCK) — phân loại query trước khi vào agent để tối ưu token. Implement intent moderation chặn Jailbreak/Off-topic/Inappropriate.
- **Python Sandbox & Conversational Memory** (Rin): Tích hợp Python Sandbox tool với AST static analysis, giới hạn CPU/Thread. Inject 5 lượt Q&A gần nhất vào prompt (conversational memory). Migrate sang `init_chat_model` provider-agnostic để support multi-model (Claude/Gemini/OpenAI).
- **Video progress tracking + Retry logic** (Rin): Lưu tiến độ học tập theo session trong DB, tự động seek video đúng phút đã dừng. Thêm retry logic khi AI chat API bị lỗi. Chuyển lịch sử QA sang JSONL song song với CSDL.
- **User Rating (👍/👎)** (Rin): Implement feedback system cho phép user đánh giá AI response. Thêm "Silent Retry" dưới nền khi gặp lỗi truy xuất.
- **Auth endpoints + AI Tutor page** (Luân): Tạo auth endpoints đầy đủ (login/register/refresh/`/users/me`), seed endpoint, fix KnowledgeComponent slug, thêm lecture seed script. Xây dựng AI Tutor page (Next.js) với video player + chat interface tích hợp.
- **IRT 2PL assessment** (Luân): Implement logic IRT 2PL để chọn câu hỏi theo năng lực người dùng trong onboarding assessment. Fix onboarding→assessment flow (4 bugs).
- **Docker & tooling fixes** (Đức): Thêm Docker init script để khởi động nhanh hơn, fix hooks, fix Docker compatibility Linux/Windows, thêm Alembic migration cho rating table.

### Khó nhất tuần này
- **Cân bằng hiệu suất LangGraph:** Việc sử dụng LangGraph kết hợp với ToolNode khiến log trả về frontend phức tạp vì đan xen giữa Token sinh mã và output trả về từ Sub-process sandbox. Khắc phục bằng SSE (Server-Sent Events) debounce sự kiện hiển thị hộp trạng thái `🧠 Thinking...` 
- **Thiết kế Prompt Guardrail fail-open:** Việc bắt sai Intent quá đà làm giảm trải nghiệm. Thiết kế lại Rule set nhẹ nhưng chặn những "Jailbreak" cơ bản theo nguyên lý fail-open khi module lỗi.

### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Antigravity (Claude Opus 4.6 / Gemini 3.1 Pro) | Migrate LangGraph, code Sandbox hardening, thiết kế Guardrails. | Nâng tầm MVP từ một chat-bot đơn thuần trở thành Agent tự giải toán. Tự động hóa được tiến trình lưu dữ liệu bằng API. |
| Claude Code (Sonnet) | `/ecc:plan` lên kế hoạch project setup, `/ecc:refactor-clean` rà dead code backend/frontend, debug Docker startup, tạo `start.sh` khởi động một lệnh | Plan refactor rõ ràng, startup script tinh gọn — team chạy được project bằng một lệnh duy nhất |

### Học được
- Kiến trúc ReAct (Reasoning and Acting) thay đổi cục diện giải thích code & thuật toán của Tutor. Tuy nhiên độ trễ thời gian trả lời tăng lên cần thông báo trạng thái "Trận đánh Boss Toán học" rõ ràng xuống giao diện để user không có cảm giác App bị sập.

### Nếu làm lại, sẽ làm khác
- Thiết kế Data Schema cho "Session" và "User" ngay từ sớm. Hiện nay tạm thời dùng localStorage UUID bypass Auth để làm MVP nhanh chóng.

---

## Tuần 4 — 18/04/2026

**Thành viên:** Nguyễn Duy Minh Hoàng, Nguyễn Đôn Đức, Nguyễn Lê Minh Luân

### Đã làm
- **Knowledge Graph (KG) full implementation** (Luân): Implement toàn bộ KG layer từ zero — `kg_concepts`, `kg_edges`, `kg_sync_state` (Alembic migration), KG loader/builder/discoverer, bridges YAML integration, recommendation engine và learning path service. Expand question bank thêm 80+ items (CV/3D/Robotics/Ethics). KG integrate vào API và CLI với automation.
- **PostgreSQL schema v1 + repository layer** (Luân): Migration head mới với `pgvector` extension, audit table `mastery_history`. Đưa vào repository layer cho auth/history/recommendation/assessment, nối assessment qua `QuestionSelector`.
- **Redis auth hardening** (Luân): Redis-backed rate limiting, token denylist, logout revoke endpoint, fix startup/CORS/config, healthcheck migration.
- **Frontend UI rebuild (Vietnamese)** (Đức): Rebuild toàn bộ frontend UI — design tokens, Vietnamese copy toàn app, lesson sidebar, tutor hub layout (enrolled courses, recommended courses, resume card). Fix alembic merge heads. Scaffold course-first platform pages (catalog, learning unit, overview).
- **Course-first platform flow** (Đức + Rin): Public/personalized catalog, start gate, learning unit, in-context tutor, dashboard, compatibility redirects. Buffer NDJSON stream chunks, regression test cho stale chapter response, e2e smoke test.
- **CS224n/CS231n data + LLM rate limiter** (Rin): Curate lecture segments cho CS224n và CS231n, add LLM rate limiter service để tránh API quota issues.
- **Hybrid merge coordination** (Rin): Merge `hybrid/integrate-db-review` vào `main` (PR #15), giữ nguyên history, resolve conflicts giữa course-first và DB/repository stacks.

### Khó nhất tuần này
- **Hòa giải hai nhánh có trung tâm kiến trúc khác nhau**: một bên course-first, một bên database/repository review. Nếu resolve file theo kiểu "gộp cú pháp" thì rất dễ làm mất contract công khai hoặc kéo lecture stack cũ quay lại.
- **Giữ auth journey không gãy sau khi harden backend**: login, onboarding, assessment, return-to-course, logout revoke và middleware public routes phải khớp nhau ở cả backend lẫn frontend.
- **Ổn định behavior bất đồng bộ của learning experience**: tutor stream NDJSON và race condition lúc đổi bài giảng nhanh đều là lỗi khó thấy nếu không có regression test rõ ràng.

### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| AI coding agents (Codex / Claude / Gemini qua hook logging) | So sánh nhánh, rà conflict, scaffold test hồi quy, và tổng hợp design docs cho hybrid merge | Giữ được history merge, hấp thụ DB hygiene vào `main`, đồng thời không làm mất flow course-first của sản phẩm |
| Claude Code (Sonnet) | Phân tích dead code frontend (Next.js) và backend (FastAPI), lên plan refactor-clean theo từng module, rà conflict hybrid merge | Xác định vùng dead code có thể xóa an toàn, conflict merge được giải quyết có kiểm soát không mất contract |

### Học được
- Nếu hai nhánh khác nhau về kiến trúc, một **hybrid branch có decision log** an toàn hơn rất nhiều so với cherry-pick rời rạc hoặc merge thẳng rồi sửa hậu quả.
- Repository layer chỉ nên áp vào vùng **thật sự DB-backed**; ép toàn bộ bootstrap/course metadata sang repository quá sớm chỉ làm tăng ceremony mà không tăng giá trị.
- Regression tests cho async UI như tutor stream, chapter fetch, và auth return flow đáng giá hơn nhiều so với chỉ nhìn UI bằng tay.

### Nếu làm lại, sẽ làm khác
- Chốt sớm hơn danh sách **canonical contracts** (`courses/*`, `learning unit`, auth return flow) trước khi bắt đầu merge để giảm số lần phải resolve cùng một mâu thuẫn ở nhiều file.
- Gom test và docs theo domain ngay từ đầu thay vì để phình theo chiều ngang, vì đến lúc merge lớn mới dọn sẽ tốn công rà lại rất nhiều reference cũ.

---

## Tuần 5 — 22/04/2026

**Thành viên:** Nguyễn Duy Minh Hoàng, Nguyễn Đôn Đức, Nguyễn Lê Minh Luân

### Đã làm
- **CS224n/CS231n data pipeline** (Rin): Curate toàn bộ lecture segments cho CS224n và CS231n — rà soát P2-P5 artifacts, kiểm tra segment, question bank, calibration bootstrap, prerequisite graph. Tổ chức lại `data/` theo vai trò rõ ràng (`bootstrap/`, `courses/`, `working/`, `final_artifacts/`).
- **Syllabus schema normalization** (Rin): Chuẩn hóa `CS231n/syllabus.json` theo schema mới của CS224n — thêm `assets`, `title`, `youtube_title`, `topic`, `year`, `type`, `custom_order` (additive, giữ field cũ). Patch script/service/test sang path mới.
- **Onboarding flow UX** (Rin): Thêm experience-level step (beginner skip / experienced continue), flat units trong known-topics step, AI prior profiling step, onboarding assessment depth. Fix onboarding loading hang.
- **IRT/CAT Placement Assessment** (Luân): Implement `IRTAdaptiveStrategy` với 3PL-lite batch CAT, audit logging qua `interactions` và `sessions` (ADD-only), `random_uniform` và `spread_by_prior` strategies. Scaffold `calibration_runs` và `item_calibration_history`. Fix alembic migration (schema_v2 idempotent, merge heads).
- **Planner Roadmap UI** (Rin): Port roadmap-style planner UI — group by course, collapse units under lectures, planner path switcher compact, fix placement decisions → planner actions. Weekly time settings popover. Regenerate planner khi profile changes.
- **Public Landing Page phase 1** (Đức): Tạo public landing page (`feat(frontend): add public landing page phase 1`), scrolling animation, routing authenticated users đến course hub.

### Khó nhất tuần này
- **Phân biệt artifact canonical và artifact tạm**: cùng tên `p2` nhưng có bản single-course failed, bản cross-course final, bản input bundle, bản validation report. Nếu không đặt lại cấu trúc thư mục thì rất dễ ingest nhầm.
- **Đồng bộ path sau reorg**: không chỉ move file, mà còn phải sửa metadata bên trong JSON, manifest, run report, visualization summary, và default path của script/test/runtime.
- **Chuẩn hóa syllabus mà không phá code cũ**: `CS224n` và `CS231n` vốn dùng hai schema khác nhau. Phải thêm field mới theo kiểu additive để code cũ vẫn sống được.

### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| AI coding agents (Codex) | Audit path, patch script/service/test, normalize syllabus schema, dọn canonical artifact tree | Layout `data/` rõ ràng hơn, final artifact cross-course tách khỏi course tree, giảm mạnh ambiguity trước khi ingest |

### Học được
- Với pipeline nhiều bước, **semantic location** của artifact quan trọng không kém nội dung file. Một file đúng nội dung nhưng nằm sai thư mục vẫn gây lỗi tư duy và lỗi vận hành.
- Nếu một schema đang tiến hóa, hướng an toàn nhất là **additive normalization**: thêm field mới và giữ field cũ trong giai đoạn chuyển tiếp.
- `.gitignore` nên phản ánh đúng cost của dữ liệu: ignore binary nặng như video, nhưng track JSON/text artifacts để review, diff và reproduce pipeline.

### Nếu làm lại, sẽ làm khác
- Chốt `data_paths.py` và layout role-based của `data/` sớm hơn ngay từ đầu pipeline, trước khi sinh hàng trăm file P3/P4/P5.
- Gắn luôn `artifact_scope` hoặc `artifact_role` trong metadata của mỗi file (`course_local`, `cross_course_final`, `working_input`) để script validate không phải suy luận từ folder name.

---

## Tuần 5 — 23/04/2026

**Thành viên:** Nguyễn Duy Minh Hoàng, Nguyễn Đôn Đức, Nguyễn Lê Minh Luân

### Đã làm
- **DB schema canonical layer** (Rin): Khóa snapshot schema nhánh `rin/implement` — tách 4 lớp rõ ràng (runtime ORM, legacy adapter, canonical artifact, learner/planner stub). Bổ sung 6 bảng stub cho learner/planner: `learner_mastery_kp`, `goal_preferences`, `waived_units`, `plan_history`, `rationale_log`, `planner_session_state`.
- **Production DB evolution docs** (Rin): Viết `docs/PRODUCTION_DB_INTEGRATION_HANDOFF.md` — khóa authoritative tables, compatibility tables, feature flags, write/read contracts, migration order cho người làm integration sau.
- **Runtime canonical cutover** (Rin + Luân): Onboarding ghi snapshot vào `goal_preferences`, planner ghi audit vào `plan_history`/`rationale_log`/`planner_session_state`. Materialize canonical content layer thành DB (985 questions, 1171 item-KP mappings, 79 prerequisite edges). Assessment đọc `question_bank` theo `item_phase_map.phase`, canonical answer submit ghi `interactions.canonical_item_id`.
- **Drop legacy schema** (Luân): DB migration `20260423_drop_legacy` — drop hẳn `modules/topics/knowledge_components/questions/mastery_scores/mastery_history/learning_paths`. Gỡ `src/kg/*` khỏi runtime. Fix `alembic_version varchar(32)` limit.
- **Abandon/resume state + mastery stale** (Rin): `planner_session_state` lưu `current_unit_id`/`current_stage`/`current_progress`/`last_activity`. Mastery stale dùng read-time sigma inflation, không mutate raw posterior. Quiz abandon giữ `interactions` (evidence không rollback).
- **Synthetic demo users** (Luân): Script deterministic tạo 9 demo accounts + 30 cohort users với distribution rõ (beginner/developing/proficient/advanced). Source-of-truth chuyển sang `scenarios.json` viết tay thay vì procedural generation.
- **Onboarding canonical payload** (Rin): Chuyển form/API sang `known_unit_ids`, `desired_section_ids`, `selected_course_ids` thay vì `topic/module`. Backend ghi `goal_preferences.selected_course_ids`.

### Khó nhất tuần này
- Phân biệt rõ đâu là việc **khóa schema đích** và đâu là việc **wire logic runtime**. Nếu làm lẫn hai việc trong cùng một lượt sẽ rất dễ tạo double-write bug hoặc nửa cũ nửa mới.
- Giữ được nhịp production: không chỉ “thêm bảng cho có”, mà phải mô tả rõ authoritative table, compatibility table, migration order và handoff contract cho người làm bước sau.

### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| AI coding agents (Codex) | Rà schema hiện tại, đối chiếu canonical artifacts, thêm stub learner/planner tables, và viết production DB evolution docs | Tạo được landing zone DB cho phase production tiếp theo mà chưa phá runtime cũ |
| Claude Code (Sonnet) | Setup test accounts cho demo, quyết định `.gitignore` cho data pipeline (ignore binary nặng, track JSON/text artifact), rà canonical artifact path | `.gitignore` phản ánh đúng cost dữ liệu, test account sẵn sàng cho smoke test |

### Học được
- Khi demo đã xong, phần khó nhất không còn là “sinh dữ liệu” mà là **khóa source-of-truth** để production không bị drift giữa nhiều thế hệ schema.
- Một schema migration tốt cần được mô tả như **hệ điều hành chuyển tiếp**: bảng nào authoritative, bảng nào compatibility, bảng nào chỉ dùng audit.

### Nếu làm lại, sẽ làm khác
- Chốt sớm hơn tài liệu “authoritative ownership matrix” ngay khi bắt đầu thêm `course-first` layer, để đỡ phải giải thích lại nhiều lần vì sao không nên tiếp tục phát triển logic mới trên `topics/questions/mastery_scores` cũ.

### Bổ sung cùng ngày

- Đã bắt đầu runtime cutover thực tế ở mức an toàn:
  - onboarding ghi compatibility snapshot vào `goal_preferences`
  - learning path generation ghi topic-grain audit vào `plan_history`, `rationale_log`, `planner_session_state`
- Chủ động **không** nối `learner_mastery_kp` và `waived_units` vào runtime vì hiện chưa có mapping authoritative sang canonical `kp_id` / `learning_unit_id`.
- Bài học rõ nhất: production cutover không phải cứ “có bảng mới là ghi vào”, mà phải kiểm tra grain của dữ liệu ngay tại điểm runtime.
- Đã materialize canonical content layer thành DB schema riêng và thêm importer:
  - validate-only trên bundle thật pass với `985` questions, `1171` item-KP mappings, `79` prerequisite edges
  - đây là bước cần thiết trước khi nối assessor/planner sang KP/unit grain thật
- Đã thêm handoff contract cho production DB integration:
  - `docs/PRODUCTION_DB_INTEGRATION_HANDOFF.md`
  - khóa rõ authoritative tables, compatibility-only tables, feature flags, write/read contracts và migration order
- Đã triển khai runtime canonical cutover sau feature flags:
  - bridge columns cho course/unit/session/interaction
  - assessment có branch đọc `question_bank` theo `item_phase_map.phase`
  - canonical answer submit ghi `interactions.canonical_item_id`
  - KP mastery bootstrap ghi `learner_mastery_kp` qua `item_kp_map`
  - planner có branch unit-grain đọc `learning_units` + `unit_kp_map` + `learner_mastery_kp`
  - parity checker chặn freeze/xóa legacy data khi chưa đủ điều kiện
- Điểm cần nhớ cho nhóm: chưa được xóa data cũ; phải chạy `alembic upgrade head`, import canonical, backfill product links, parity check rồi mới bật flags.
- Bước tiếp theo đã hoàn thành luôn trong ngày:
  - runtime production code không còn reference thực thi tới `modules/topics/knowledge_components/questions/mastery_scores/mastery_history/learning_paths`
  - `src/kg/*` bị gỡ khỏi runtime codebase vì không còn được mount/use
  - DB dev đã lên `20260423_drop_legacy`
  - các bảng legacy ở trên đã bị drop thật, không còn là “compatibility maybe”
- Bài học mạnh nhất:
  - đến một lúc phải **cắt hẳn** chứ không thể giữ fallback vô thời hạn; nếu không, source-of-truth sẽ tiếp tục trôi về schema cũ dù tài liệu đã nói ngược lại.

### Bổ sung 24/04/2026

- Đã chốt nốt phần execution semantics cho canonical runtime:
  - planner path update không còn dừng ở audit-only
  - `learning_progress_records` giữ trạng thái thực thi theo `learning_unit`
  - `waived_units` trở thành audit trail thật cho skip decision
- Một lỗi mechanical đáng nhớ đã lộ ra khi migrate:
  - `alembic_version.version_num` đang giới hạn `varchar(32)`
  - revision id đặt quá dài sẽ fail dù logic migration đúng
  - fix bằng cách rút ngắn revision id và giữ migration idempotent (`IF NOT EXISTS`)
- Điều rút ra:
  - production-hardening không chỉ là đổi schema logic, mà còn phải để ý các giới hạn cơ học như enum migration, revision id length, idempotency khi rerun.

### Bổ sung kiểm thử runtime 24/04/2026

- Sau khi DB/schema đã canonical-only, phần verification đáng làm nhất là build/e2e chứ không chỉ unit test backend.
- `next build` lộ lỗi đúng kiểu production: client page dùng `useSearchParams()` nhưng thiếu `Suspense` boundary. Dev mode có thể che lỗi này, nên production build phải nằm trong checklist bắt buộc.
- Playwright e2e lộ thêm drift copy/label do data canonical đã đổi từ lecture-level title sang segment-level unit title. Fix đúng là update test selector theo canonical data hiện hành, không đổi UI.
- Asset test lộ một bug guard thật: protected prefix cũ thiếu `courses/`, nghĩa là signed URL check có thể không áp dụng lên path runtime mới. Đây là ví dụ tốt cho việc route contract test bắt được lỗi bảo mật nhỏ sau data-layout refactor.
- Trạng thái hiện tại: frontend build pass, backend canonical regression pass, course discovery/gating e2e pass.

### Bổ sung abandon/resume state 24/04/2026

- Đã bịt gap nhỏ nhưng quan trọng của learner runtime: trước đây có progress/status bền vững nhưng thiếu pointer cho phiên đang bỏ dở.
- `planner_session_state` giờ có thể lưu `current_unit_id`, `current_stage`, `current_progress`, `last_activity`.
- Quy tắc quan trọng được khóa lại: quiz abandon không được xoá `interactions`; evidence đã sinh thì vẫn là evidence, chỉ quiz gate có thể bị regenerate nếu quá stale.
- Mastery stale được xử lý bằng read-time sigma inflation, không mutate trực tiếp `learner_mastery_kp`. Cách này giữ raw posterior sạch và để quick-review/placement-lite tạo evidence mới nếu user quay lại sau lâu ngày.

### Bổ sung course-first onboarding 24/04/2026

- Onboarding không còn lấy `topic/module` làm ngôn ngữ payload chính.
- Frontend form và API payload đã chuyển sang `known_unit_ids`, `desired_section_ids`, `selected_course_ids`.
- Backend ghi `goal_preferences.selected_course_ids` từ lựa chọn course rõ ràng, thay vì lưu snapshot legacy và để planner tự đoán scope.
- Giữ alias cũ trong backend chỉ là bridge tạm cho client chưa migrate; không dùng làm contract sản phẩm mới.

### Bổ sung semantic cleanup 24/04/2026

- Sau khi DB đã canonical-only, bước tiếp theo là làm public contract bớt gây hiểu nhầm.
- Đã rename các DTO runtime chính sang learning-unit/section-first: assessment result, module-test group/result/review suggestion, learning-path counts, history question detail.
- Điểm giữ lại có chủ đích: một số alias input như `topic_ids` hoặc `module_id` vẫn tồn tại để không phá client cũ ngay lập tức, nhưng frontend và docs active dùng tên mới.

### Bổ sung docs cleanup 24/04/2026

- README cũ là nguồn drift lớn vì vẫn mô tả seed `modules/topics/questions`, planner topological topic, và IRT/BKT như production reality.
- Đã đổi README thành contract ngắn gọn cho runtime canonical hiện tại và chuyển scoring claim về mức đúng: bootstrap KP-level, chưa phải calibrated IRT/BKT.
- Các plan/spec cũ trong `docs/superpowers` được giữ để audit, nhưng đã có banner historical. Điều này quan trọng vì production work tiếp theo cần một nguồn sự thật duy nhất, không đọc nhầm task chuyển tiếp cũ thành thiết kế active.

### Bổ sung legacy helper cleanup 24/04/2026

- `scripts/seed.py` là bẫy lớn hơn tưởng tượng: dù DB legacy đã drop, entrypoint này vẫn import `Module/Topic/Question` cũ. Nếu giữ, người vận hành có thể chạy đúng command cũ và fail ở production bootstrap.
- Fix đúng không phải xóa command, mà đổi command sang canonical import để `make seed` và `start.sh` vẫn có workflow quen thuộc nhưng không quay về schema cũ.
- Xóa hẳn helper topic/topological dead code giúp giảm rủi ro người mới copy nhầm planner logic cũ.

### Bổ sung mastery scoring 24/04/2026

- Scoring cần rõ semantic trước khi sinh synthetic. Nếu không, synthetic data sẽ chỉ làm đẹp dashboard nhưng không kiểm thử được learner/planner thật.
- Phase-1 hiện dùng 2PL-lite trên prior/calibration fields đã có sẵn, nhưng vẫn không gọi là calibrated IRT. Đây là ranh giới quan trọng cho production honesty.
- Synthetic calibration được tách thành task cuối: trước khi sinh phải chốt latent learner profiles, session cadence, abandon/resume, phase mix và tagging `is_synthetic`.

### Bổ sung learner runtime cases 24/04/2026

- Đã triển khai đủ backend phase 1-5 cho các learner archetype chính trước khi đụng synthetic:
  - skipper: policy gate trước khi ghi `waived_units`
  - abandon video: lưu current unit/stage/progress
  - abandon quiz: lưu answered/remaining item IDs, không rollback evidence
  - review-heavy / long-return: `/api/review/start`
  - placement-lite returner: `/api/placement-lite/start`
- Điểm cố ý chưa làm: sinh synthetic data. Synthetic phải là task thiết kế riêng vì nếu không tag và tách khỏi real evidence, calibration report sẽ bị nhiễu ngay từ đầu.

### Bổ sung synthetic demo users 24/04/2026

- Synthetic demo data được chuyển từ ý tưởng sang script deterministic, nhưng vẫn không gọi là calibration truth.
- Thiết kế quan trọng: 9 demo accounts để login UX tách khỏi 30 cohort users để tạo volume.
- Không khóa state runtime. Demo account được phép thao tác; reset baseline bằng cách chạy lại script import.
- Cohort có phân bố trình độ rõ (`beginner/developing/proficient/advanced`) để planner/mastery/history không nhìn như một nhóm user đồng nhất.
- Sau review, source-of-truth được đổi từ procedural generation sang `scenarios.json` viết tay. Đây là điểm quan trọng: năng lực user phải review được bằng mắt, không ẩn trong Python helper.

---

## Tuần 6 — 29/04/2026

**Thành viên:** Nguyễn Duy Minh Hoàng, Nguyễn Đôn Đức, Nguyễn Lê Minh Luân

### Đã làm
- **LangGraph Agentic RAG redesign** (Rin): Thiết kế lại toàn bộ agent pipeline — structured router → context service → search service (RAG) → answer node. Thêm prerequisite path agent, citation grounding, evidence policy (`grounded / partial / no_source`) và assessment boundary (block agent khi user đang trong bài kiểm tra).
- **Guardrail Router client** (Rin): Xây dựng multilayer guardrail gate tích hợp vào cả tutor flow lẫn agent flow. Thêm language normalization dùng Lingua detector để xử lý tiếng Việt / tiếng Anh.
- **External research mode** (Rin): Tích hợp Semantic Scholar API và web search để agent mở rộng tìm kiếm ra ngoài learning content.
- **Langfuse observability** (Rin): Implement Langfuse tracing — trace ID propagation, span tagging theo route/agent node, eval trigger hook. Thêm `ContinueLearningHero` component và admin dashboard KpiGroup (`feat: implement Langfuse observability`).
- **Replan feature E2E** (Rin): Toàn bộ replan flow từ frontend đến backend — replan route shell, claim guardrails, scope review component, prerequisite suggestion dialog, backend schemas/service/router, LLM keyword extraction, guardrail modes. Fix replan persistence của placement skips.
- **Frontend theme refactor** (Đức): Rebuild hệ thống màu sắc frontend — design tokens, chart-theme, auth pages refactor (LoginForm, RegisterForm, ForgotPasswordForm), bloom badges, AgentChatPage theme, landing page CTA unify. Vietnamese copy cho auth/public pages.
- **Reset password flow** (Đức): Implement complete reset password flow (frontend + backend wiring).
- **vLLM self-hosted serving** (Rin + Đức): Triển khai Qwen3.5-0.8B qua Cloudflare Tunnel như OpenAI-compatible API endpoint cho guardrail router.

### Khó nhất tuần này
- **Citation grounding vs. hallucination tradeoff**: Agent cần trích dẫn đúng source segment mà không sinh nội dung ngoài source. Phải thiết kế evidence policy chi tiết và thêm `must_not_hallucinate` rules vào golden eval để kiểm soát được regression.
- **Guardrail multilayer latency**: Mỗi request đi qua guardrail router trước khi vào agent. Với vLLM local qua Cloudflare Tunnel, latency tăng thêm 3-4s cho mỗi turn. Phải cache route result cho session và chỉ re-route khi topic thay đổi để giảm impact.
- **Terraform IaC từ zero**: Chưa có state file nào, phải provision toàn bộ từ đầu. RDS và ElastiCache ở private subnet nên phải cẩn thận security group rules để backend ECS task có thể reach được.

### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Claude Code (Opus) | Thiết kế LangGraph graph nodes, viết evidence policy rules, scaffold Terraform modules | Agentic RAG pipeline có cấu trúc rõ ràng, citation và no-hallucination constraint được enforce ở node level |
| Claude Code (Sonnet) | Fix Next.js build error (thiếu `Suspense` boundary cho `useSearchParams`), debug Docker compose, fix planner course display không load | Frontend build pass production, planner hiển thị đúng danh sách course |
| Codex | Review Terraform plan output, fix IAM policy scope, viết script reconcile Secrets Manager | Infrastructure provision thành công, secret injection vào ECS task definition hoạt động đúng |
| Codex | Debug planner feature — phân tích `CourseFeature` component, rà course display và enrollment flow bugs | Xác định root cause course không hiện sau onboarding, fix display logic |

### Học được
- **Citation phải là contract, không phải style**: Nếu không định nghĩa rõ "grounded = có exact match với source segment", agent sẽ drift sang paraphrase và bắt đầu fabricate. Golden eval phải có `must_not_cite` cases để giữ boundary.
- **Terraform state là canonical**: Sau khi provision, mọi thay đổi hạ tầng phải đi qua `terraform apply`. Sửa trực tiếp trên Console rồi apply sau sẽ gây conflict state mà rất khó debug.
- **vLLM qua tunnel phù hợp cho prototype, không phải production**: Latency Cloudflare Tunnel dao động nhiều hơn kết nối trực tiếp. Production deployment cần đưa guardrail model vào cùng VPC với app.

### Nếu làm lại, sẽ làm khác
- Thiết kế golden eval test cases song song với agent node design, không chờ pipeline xong mới viết test — lúc đó mất nhiều lần refactor để fit behavior vào test.
- Provision Terraform với remote state (S3 backend) từ đầu thay vì local state, để nhiều người có thể apply mà không conflict.

---

## Tuần 7 — 09/05/2026

**Thành viên:** Nguyễn Duy Minh Hoàng, Nguyễn Đôn Đức, Nguyễn Lê Minh Luân

### Đã làm
- **ECS production deployment** (Đức): Manual bootstrap production — 5 backend task revisions liên tiếp (canonical migration fail → Secrets Manager IAM thiếu → CORS chưa include domain → vLLM endpoint sai format → pgvector image mismatch). Images tag theo commit hash (`frontend:7deedc0`, `backend:7deedc0-units`). Live tại `a20-app-049.io.vn` (09-10/05).
- **CI/CD automation** (Đức): Đưa pipeline vào `.github/workflows/` — `build-push.yml` trên self-hosted EC2 runner (build + push ECR), `deploy-ecs-prod.yml` render task definition từ template rồi deploy ECS Fargate. Fix 4 CI/CD blockers, promote ECS workflows. `reconcile-backend-secret.sh` update Secrets Manager động theo deployment context.
- **Admin observability panel** (Đức): Trang admin với Loki log streaming, Prometheus metrics embed, Grafana dashboard embed, CloudWatch log group integration. Route protected bằng admin role. Update model selector dropdown và health check display (11/05).
- **PII Guardrail module** (Đức): Tạo `pii_guardrail.py`, `guardrails_adapter.py`, `pii_policy.py`, `types.py` — phát hiện và chặn PII (email, phone, CCCD) trong user query trước khi vào agent. Test coverage đầy đủ (11/05).
- **DVC transcript tracking** (Rin): Track course transcript artifacts bằng DVC thay vì đưa binary vào Git (`Track course transcript DVC artifacts`, 08/05).
- **Agent UI activity tracker** (Rin, agent-ui branch): Thêm real-time activity tracker hiển thị agent actions (search, retrieve, cite), model health caching và failover khi endpoint không healthy. (Hoàn thành merge 13/05, được bắt đầu tuần này)

### Khó nhất tuần này
- **5 backend revisions trong một ngày**: Mỗi revision fix một lớp — đầu tiên là migration fail vì revision id quá dài (PostgreSQL varchar(32) limit), sau đó là Secrets Manager IAM permission thiếu, rồi CORS config chưa include production domain, rồi vLLM endpoint URL sai format. Phải deploy → test → identify → fix → redeploy 5 vòng.
- **Self-hosted runner trên EC2**: Docker buildx trên EC2 cần cấu hình đúng IAM role để push lên ECR. Multi-platform build tốn thêm thời gian. Runner phải được giữ alive qua `screen` session hoặc systemd service để không mất kết nối giữa build.
- **Guardrail model vLLM latency**: Với ECS deployment, guardrail router vẫn gọi sang Cloudflare Tunnel. Latency dao động gây timeout cho một số request. Phải implement circuit breaker và fallback route (default ALLOW khi guardrail không trả kết quả kịp).

### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Claude Code (Opus) | Debug ECS deployment failures từ CloudWatch logs, thiết kế CI/CD yaml, viết admin panel query logic | Pipeline CI/CD hoạt động end-to-end từ push → build → deploy mà không cần thao tác thủ công |
| Codex | Phân tích deploy options (full AWS ECS vs. separate services), lên Terraform plan, viết sơ đồ AWS architecture dạng markdown, viết reconcile-backend-secret.sh, fix task definition template | Chọn được strategy deploy đúng, Terraform plan có cơ sở rõ, secret sync tự động |

### Học được
- **ECS production bootstrap cần checklist chặt**: Mỗi revision là một deployment window. Nếu không có checklist (migration → secret → CORS → health check → smoke test), dễ bỏ sót bước và phải rollback.
- **CI/CD trên self-hosted runner tiết kiệm cost nhưng phức tạp hơn**: Phải manage runner lifecycle (restart sau EC2 reboot, log rotation, IAM permission boundary). GitHub-hosted runner đơn giản hơn cho prototyping, self-hosted phù hợp hơn khi cần Docker cache và ECR proximity.
- **Observability phải có từ ngày đầu production**: Không có Loki/CloudWatch, 5 revision debug đó sẽ tốn gấp đôi thời gian vì không biết lỗi xảy ra ở container layer nào.

### Nếu làm lại, sẽ làm khác
- Viết smoke test script chạy ngay sau mỗi ECS deployment thay vì test thủ công qua browser. Với 5 revision, một script `curl` + assertion đơn giản đã tiết kiệm được ít nhất 30 phút.
- Thiết lập Terraform remote state và ECS blue/green deployment từ đầu, không phải force-deploy revision mới lên task definition cũ.

---

## Tuần 8 — 11/05/2026

**Thành viên:** Nguyễn Duy Minh Hoàng, Nguyễn Đôn Đức, Nguyễn Lê Minh Luân

### Đã làm
- Hoàn thiện nhánh `rin/fine-tune` cho hướng **local fine-tuned AI tutoring stack**:
  - **Qwen3.5-0.8B LoRA** làm lesson-scope guardrail router.
  - **Qwen3.5-4B LoRA** làm answer/refusal generator.
  - Router chỉ trả label JSON ngắn, không sinh giải thích dài, phù hợp để đưa vào production pipeline.
- Xây dựng và review bộ dữ liệu router v2 từ 5 nguồn chính:
  - EduVidQA / question bank cho `ON_TOPIC`.
  - CantTalkAboutThis + CLINC150/OOS + cross-pair cho `OFF_TOPIC`.
  - WildGuardMix, JailBreakV-28K, MultiJail cho `HARMFUL` và prompt/router injection.
  - Ambiguous templates và open-QA review labels cho các câu thiếu ngữ cảnh.
- Chuyển route safety chính sang schema gọn hơn:
  - `SAFE`
  - `HARMFUL`
  - `ON_TOPIC / OFF_TOPIC / AMBIGUOUS / N_A`
  - `ALLOW_LESSON_ANSWER / SOFT_REFUSE_REDIRECT / ASK_CLARIFY / SAFETY_REFUSE`
- Thêm data hardening quan trọng cho router:
  - schema override ép model trả `SAFE`.
  - policy override kiểu ignore previous/system/developer.
  - role override.
  - scope override.
  - KP injection ép `selected_kp_ids` giả.
  - hard off-topic với invariant `query_unit_id != context_unit_id` và primary KP không nằm trong candidate KPs.
- Track artifact bằng **DVC** thay vì đưa binary vào Git:
  - router v2 train/validation/test split.
  - Qwen3.5-0.8B router adapter.
  - Qwen3.5-4B answer generator adapter.
- Thêm notebook và script phục vụ reproduce:
  - dataset builders v1/v2.
  - source review / source validation scripts.
  - EduVidQA preparation.
  - local router benchmark script.
  - Colab notebooks cho fine-tune/eval Qwen3.5 router và answer model.

### Kết quả nổi bật
- Router v2 đạt `valid_json_rate = 1.0` trên validation/test.
- Test route chính đạt `route_exact_match = 0.9697`.
- `harmful_false_allow_rate = 0.0`, tức eval hiện tại không ghi nhận harmful prompt nào bị route thành lesson answer.
- `ambiguous_recall = 0.9905`, tốt hơn v1 vì test đã có nhiều case ambiguous thật hơn.
- `hard_offtopic_recall = 0.9408`, cho thấy router đã học boundary unit/KP chứ không chỉ chặn off-topic dễ.
- Local smoke benchmark trên RTX 3050 Laptop GPU chạy được:
  - peak VRAM khoảng `1.5GB`.
  - output schema hợp lệ `8/8` prompt.
  - các case router injection và KP injection được chặn đúng.
  - latency trung bình khoảng `3.4s/query` khi chạy bằng script local.

### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Codex | Review dataset, viết dataset builders/tests, tạo DVC pointers, chuẩn hóa commit theo từng file, và benchmark local adapter | Tạo được baseline fine-tuned router + answer generator có thể tái lập bằng code, DVC artifact và notebook |
| Claude Code (Sonnet) | Hỗ trợ fine-tuning pipeline — rà training script, kiểm tra data schema alignment giữa training prompt và serving prompt | Phát hiện mismatch enum giữa training và inference prompt trước khi deploy |
| Gemini/OpenAI judge notebooks | Chấm chất lượng answer model và so sánh với baseline | Có report eval rõ ràng để chọn adapter 4B final thay vì chỉ nhìn loss |

### Học được
- Với guardrail router, chất lượng data quan trọng hơn prompt. Khi data được sửa đúng boundary, model nhỏ vẫn học route/action rất chắc.
- Gộp `UNSAFE` và `JAILBREAK` thành `HARMFUL` cho route chính giúp production decision ổn định hơn, còn `attack_type` nên giữ làm telemetry phụ.
- Fine-tune artifact không nên commit thẳng vào Git. DVC phù hợp hơn vì giữ được reproducibility mà repo vẫn nhẹ.
- Benchmark local phải dùng đúng prompt/schema lúc train. Khi prompt inference lệch, model vẫn sinh JSON nhưng enum có thể sai hoàn toàn.

### Nếu làm lại, sẽ làm khác
- Thiết kế DVC tracking ngay từ đầu trước khi sinh nhiều output zip/checkpoint.
- Đặt `WORKLOG`, `JOURNAL`, build report và model manifest thành checklist cố định sau mỗi vòng fine-tune.
- Giữ benchmark nhỏ trong notebook lẫn script local để phát hiện sớm mismatch giữa training prompt và serving prompt.

---

## Tuần 9 — 12/05/2026

**Thành viên:** Nguyễn Duy Minh Hoàng, Nguyễn Đôn Đức, Nguyễn Lê Minh Luân

### Đã làm
- **Agent search rerank** (Rin): Thêm rerank theo score cho kết quả tìm kiếm của agent unit search — ưu tiên unit có relevance cao hơn thay vì chỉ trả về theo thứ tự embedding. Fix narrow qualified acronym evidence (chặn tình huống agent cite nhầm do keyword giống nhau). Thêm contextual prerequisite action preservation để agent không mất track khi follow-up question liên quan prerequisite path.
- **Observability stack hoàn thiện** (Đức): Scaffold production observability đầy đủ — Terraform module cho Prometheus/Grafana/Loki stack, backend metrics scrape endpoint, PostgreSQL datasource trong Grafana, fix Cloud Map namespace format, wiring frontend admin embed panel. Toàn bộ stack deployed lên ECS, admin panel live.
- **Agent failover & network fix** (Đức): Debug và fix 4 lần agent downtime liên tiếp do vLLM endpoint không respond — thêm circuit breaker logic, fix router HTTPS endpoint, cập nhật pgvector image version, fix secret injection cho agent route.
- **Landing page redesign** (Luân): Cập nhật toàn bộ landing page theo sản phẩm production thực tế — nội dung mới, button dimensions chuẩn, bỏ social proof section chưa có data thật, thêm Redis error handling cho backend resilience.
- **Auth UX hardening** (Rin): Fix stale error hydration trong auth store (lỗi persisted error từ session cũ hiển thị sai khi load trang mới). Fix login/register stale error. Relax password schema validation cho demo accounts — giảm độ phức tạp để demo thực tế không bị friction với `DemoPass123!`. Thêm test coverage cho toàn bộ auth form edge cases.
- **RoadmapPlanner master-detail** (Rin): Migrate từ flat list sang master-detail layout với sidebar navigation. Unit tests cập nhật theo layout mới.
- **Submission documentation** (Đức): Tạo `docs/ai-logs.md`, `AI20K_FINAL_SUBMISSION_GUIDE.md`, cập nhật README với Quick Links đầy đủ, xóa stale testing docs (`TESTING_DOCUMENTATION_INDEX.md`, `TEST_STATUS_REPORT.md`, `TESTING_ONBOARDING_FLOW.md`), bổ sung team section.
- **CI/CD pipeline** (Đức): Refactor workflow YAML, fix concurrency (cancel previous progress), cập nhật `build-push.yml` + `ci.yml`, clean up stale jobs. Fix Loki log pipeline.

### Kết quả nổi bật
- Agent search quality cải thiện: kết quả rerank đúng hơn, acronym trap được giải quyết, contextual citation không bị mất khi multi-turn.
- Observability live: `admin.a20-app-049.io.vn` hiển thị Grafana dashboard, Loki log stream theo service/level, CloudWatch integration.
- Auth flow ổn định cho demo: stale error không còn xuất hiện, password demo login không cần complex format.
- Repo sạch cho submission: stale docs xóa, README đầy đủ Quick Links, team section điền đúng.

### Khó nhất tuần này
- **Agent downtime 4 lần liên tiếp**: Mỗi fix lộ ra một lớp mới — đầu tiên là HTTPS endpoint URL sai, sau đó là pgvector image mismatch, rồi secret không inject đúng, cuối cùng là Cloud Map namespace sai format. Phải deploy → CloudWatch log → identify → fix → redeploy 4 vòng trong cùng một ngày.
- **Observability Cloud Map format**: Terraform `service_discovery_registry_arn` và Cloud Map namespace phải khớp chính xác format với ECS service discovery. Một ký tự sai trong namespace gây toàn bộ metrics scrape fail silently — không có lỗi rõ ràng, chỉ thấy "no data" trong Grafana.
- **Auth stale error**: Lỗi này chỉ xảy ra khi user đã login session cũ còn cached trong Zustand persist store, sau đó mở tab mới. Không reproduce được qua unit test thông thường — phải viết test mock persist state cụ thể mới bắt được.

### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Claude Code (Opus) | Debug agent downtime từ CloudWatch logs, thiết kế rerank scoring logic, viết auth stale error test cases | Xác định được root cause của từng downtime instance mà không cần SSH trực tiếp vào container |
| Codex | Refactor observability Terraform module, viết Grafana datasource provisioning config | Observability stack deploy thành công lần đầu sau khi fix namespace format |

### Học được
- **Rerank là cần thiết khi search space lớn**: Embedding similarity tốt cho recall nhưng không đủ cho precision khi nhiều unit có title/KP tương tự. Một rerank step đơn giản theo combined score tăng rõ rệt chất lượng citation.
- **Observability silent failure là loại nguy hiểm nhất**: Lỗi "no data" trong Grafana khó hơn lỗi exception. Phải có alert rule ngay từ đầu: nếu metric scrape không có data trong 5 phút thì coi là lỗi, không coi là "không có traffic".
- **Demo account UX là sản phẩm**: Người dùng demo lần đầu mà không login được vì password quá phức tạp là lỗi UX nghiêm trọng như mọi bug khác. Password policy cho production và cho demo account phải được thiết kế riêng.

### Nếu làm lại, sẽ làm khác
- Thiết lập observability stack ngay tuần đầu production, không phải tuần cuối. Toàn bộ 5 revision ECS bootstrap tuần 7 sẽ debug nhanh hơn 50% nếu Grafana/Loki đã live từ lúc đó.
- Chốt demo account policy (email format, password complexity) ngay khi tạo synthetic users, không sửa lại ở tuần submission.

---

## Tuần 10 — 15/05/2026 (Submission Week)

**Thành viên:** Nguyễn Duy Minh Hoàng, Nguyễn Đôn Đức, Nguyễn Lê Minh Luân

### Đã làm
- **Architecture HTML redesign** (Đức): Vẽ lại toàn bộ `architecture/03-aws-infrastructure.html` theo chuẩn AWS draw.io 2026 — icon màu chính xác theo category (Networking: #8C4FFF, Compute: #E7500A, Storage: #3DAA35, Database: #1565C0, Security: #DD344C), zone borders (VPC: orange solid, Subnet: blue dashed, ECS Cluster: orange dashed), SVG inline icons cho từng service. Bỏ Mermaid dark theme — chuyển sang white background chuẩn draw.io.
- **Agent fix** (Đức): Sửa lỗi agent route sau lần downtime cuối — cập nhật vLLM endpoint, fix circuit breaker timeout, verify fallback sang Gemini/OpenAI hoạt động đúng.
- **Loki log pipeline fix** (Đức): Fix pipeline Loki log aggregation cho production — log stream theo service/level hoạt động lại sau cấu hình sai namespace.
- **README & SVG update** (Đức): Cập nhật SVG architecture diagrams trong README, bổ sung link Quick Links table, chuẩn hóa format submission.
- **Submission checklist** (Đức): Tạo `docs/SUBMISSION_CHECKLIST.md` tổng hợp toàn bộ trạng thái submission, còn thiếu Video Demo và Pitch Deck.

### Kết quả nổi bật
- Architecture HTML đạt chuẩn visual AWS draw.io 2026 — đủ icon, màu, zone borders.
- Agent production hoạt động ổn định sau fix — fallback sang LLM provider ngoài hoạt động đúng khi vLLM gặp lỗi.
- Observability (Grafana/Loki) live và ổn định.
- Repo sạch, documentation đầy đủ cho submission.

### Khó nhất tuần này
- **Vẽ lại architecture đúng chuẩn draw.io**: Icon AWS mỗi service category có màu riêng và icon path riêng; làm bằng SVG inline trong HTML phức tạp hơn dùng Mermaid nhưng kết quả đẹp và chuyên nghiệp hơn nhiều.
- **Agent lại downtime lần 5**: Root cause lần này là vLLM endpoint URL thay đổi sau restart server Cloudflare Tunnel; phải update secret + redeploy ECS service.

### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Claude Code (Sonnet) | Phân tích ảnh draw.io reference, thiết kế SVG icon cho mỗi AWS service, vẽ lại HTML architecture theo chuẩn 2026 | Architecture HTML professional, đủ zone borders, màu AWS chuẩn |
| Claude Code (Sonnet) | Tạo SUBMISSION_CHECKLIST.md, tổng hợp trạng thái toàn bộ requirements | Biết chính xác còn thiếu gì trước deadline 17/05 |

### Học được
- **SVG inline diagram trong HTML bền hơn Mermaid cho technical documentation**: Mermaid tốt cho quick iteration nhưng SVG cho phép kiểm soát pixel-level, icon đúng AWS standard, không phụ thuộc JS runtime.
- **Checklist submission nên làm từ tuần 8, không phải tuần 10**: Ngay khi thấy deadline sắp đến, việc đầu tiên là inventory — xem còn thiếu gì, không phải tiếp tục code feature mới.

### Nếu làm lại, sẽ làm khác
- Freeze feature development 2 tuần trước deadline. Dành toàn bộ thời gian còn lại cho documentation, testing, và submission prep.
- Quay video demo từ tuần 9, không phải đợi đến tuần 10.
