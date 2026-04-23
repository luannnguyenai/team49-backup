# Worklog

Ghi lại các quyết định kỹ thuật, phân công, và brainstorming của nhóm.

---

## Các Quyết Định Kỹ Thuật (ADR)

### [ADR-6] Ưu tiên Database-First Evolution cho phase production hardening — 23/04/2026

**Bối cảnh:** Sau khi canonical ingestion artifacts đã sạch và demo đã đủ chạy, nút thắt lớn nhất không còn nằm ở prompt/pipeline nữa mà nằm ở sự lệch giữa runtime schema cũ (`topic/module`) và target schema mới (`kp/unit + planner audit`). Nếu tiếp tục nối service trực tiếp lên runtime cũ thì càng về sau càng khó migrate.

**Quyết định:** Khóa một hướng đi rõ ràng:

1. Xem canonical JSONL là ingestion contract sạch.
2. Xem course-first tables là business shell của sản phẩm.
3. Thêm learner/planner stub tables làm landing zone production:
   - `learner_mastery_kp`
   - `goal_preferences`
   - `waived_units`
   - `plan_history`
   - `rationale_log`
   - `planner_session_state`
4. Chưa wire logic service ngay trong lượt này; phần đó sẽ được làm có kiểm soát ở phase integration sau.

**Hệ quả:** Database direction rõ ràng hơn cho production. Người làm integration phía sau không phải đoán source-of-truth nữa, và việc nâng cấp database có thể tiến hành độc lập với việc refactor service/router/frontend.

### [ADR-7] Runtime cutover chỉ nối những write-path có grain an toàn — 23/04/2026

**Bối cảnh:** Sau khi thêm các sidecar tables mới, nhu cầu kế tiếp là bắt đầu cutover runtime. Tuy nhiên runtime hiện vẫn ở grain `topic/module`, trong khi một phần schema mới (`learner_mastery_kp`, `waived_units`) đòi hỏi grain `kp/unit`.

**Quyết định:** Chỉ nối các write-path nào có thể ghi **đúng grain** hoặc ít nhất **compatibility snapshot minh bạch**:

- nối `update_onboarding()` -> `goal_preferences`
- nối `generate_learning_path()` -> `plan_history`, `rationale_log`, `planner_session_state`
- **không** nối:
  - `mastery_scores` -> `learner_mastery_kp`
  - `learning_paths.status=skipped` -> `waived_units`

cho đến khi có bridge authoritative từ runtime cũ sang canonical `kp_id` / `learning_unit_id`.

**Hệ quả:** Runtime bắt đầu để lại audit trail hữu ích cho production migration mà không fabricate dữ liệu mới sai grain. Đổi lại, cutover chưa hoàn thành hết; hai flow mastery/waive vẫn phải chờ phase canonical-DB integration kế tiếp.

### [ADR-8] Materialize canonical content artifacts thành bảng DB riêng — 23/04/2026

**Bối cảnh:** Canonical JSONL đã sạch nhưng vẫn là file artifact. Nếu planner/assessor production tiếp tục đọc file, hệ sẽ khó transaction, khó query, khó enforce FK và khó nối runtime với `kp_id` / `unit_id` thật.

**Quyết định:** Tạo ORM + Alembic riêng cho canonical content layer:

- `concepts_kp`
- `units`
- `unit_kp_map`
- `question_bank`
- `item_calibration`
- `item_phase_map`
- `item_kp_map`
- `prerequisite_edges`
- `pruned_edges`

Importer đọc `data/final_artifacts/cs224n_cs231n_v1/canonical/*.jsonl`, validate counts với manifest, và upsert idempotent bằng natural keys.

**Hệ quả:** Production DB giờ có landing zone thật cho content graph và Q-matrix. Các flow `learner_mastery_kp` / `waived_units` vẫn chưa nên nối cho đến khi runtime có bridge đúng từ item/unit/KP canonical.

### [ADR-9] Khóa integration handoff trước khi service/router cutover — 23/04/2026

**Bối cảnh:** Sau khi có bảng mới, migration và importer, rủi ro lớn nhất chuyển sang phía integration: người nối backend có thể vô tình đọc/ghi lẫn giữa bảng compatibility cũ và bảng authoritative mới.

**Quyết định:** Tạo handoff contract riêng ở `docs/PRODUCTION_DB_INTEGRATION_HANDOFF.md`, mô tả rõ:

- bảng nào authoritative
- bảng nào compatibility-only
- write contract cho `goal_preferences`, `learner_mastery_kp`, `waived_units`, `plan_history`, `rationale_log`, `planner_session_state`
- read contract cho planner/assessor/progress
- thứ tự migrate/import/cutover
- các điều không được làm như fabricate `kp_id` từ `topic_id`

**Hệ quả:** Phase tiếp theo có thể tập trung vào service/repository/router integration mà không phải tranh luận lại source-of-truth. UI vẫn không bị đụng trong lượt DB hardening này.

### [ADR-10] Runtime canonical cutover dùng feature flags, không xóa legacy data — 23/04/2026

**Bối cảnh:** Sau khi canonical content và learner/planner tables đã vào DB, bước kế tiếp là cho runtime bắt đầu đọc/ghi theo canonical data thay vì chỉ giữ schema foundation.

**Quyết định:** Triển khai cutover theo hướng additive:

- thêm bridge columns:
  - `courses.canonical_course_id`
  - `learning_units.canonical_unit_id`
  - `sessions.canonical_phase`
  - `interactions.canonical_item_id`
- thêm canonical question selector đọc `question_bank` + `item_phase_map`
- thêm canonical assessment submit ghi `interactions.canonical_item_id` và update `learner_mastery_kp`
- thêm canonical planner branch đọc `learning_units` + `unit_kp_map` + `learner_mastery_kp`
- thêm parity checker trước khi freeze legacy tables

Tất cả runtime branch mới đều nằm sau feature flags. Không drop/truncate bảng cũ trong lượt này.

**Hệ quả:** Backend có đường đi production sang canonical data nhưng vẫn rollback được bằng flag. Thành viên khác cần chạy migration/import/backfill/parity trước khi bật read flags ở môi trường thật.

### [ADR-1] Chuyển đổi sang Real-time Streaming Response — 06/04/2026

**Bối cảnh:** AI xử lý thông tin với số lượng token lớn (Transcript dài 10 phút + 1 ảnh Frame Capture). API response theo dạng tĩnh truyền thống (Chờ AI xong mới trả toàn bộ một cục JSON) tạo ra thời gian chờ quá tải, dẫn đến UX bị ngắt quãng, không mang lại cảm giác "Trò chuyện tương tác thời gian thực".

**Các lựa chọn đã xem xét:**
- **In-memory cache**: Không giải quyết được đặc điểm trễ bẩm sinh của quá trình Inference AI.
- **WebSockets**: Overhead backend server khá cao, cần thiết kế lại cơ chế Backend Socket và Frontend Event quá lằng nhằng.
- **Server-Sent Events (SSE) với StreamingResponse**: Tích hợp luồng Python Generator native từ thư viện FastAPI, cực kỳ nhẹ bén rễ với chuẩn HTTP và tiện lợi bắt bằng hàm `fetch` cơ bản ở JS.

**Quyết định:** Khai tử toàn bộ API tĩnh. Sử dụng **FastAPI StreamingResponse (SSE)** gửi chunk dữ liệu liên tục về giao diện. Xây dựng UX "Gõ máy chữ" có kèm Animation trạng thái suy nghĩ (*🧠 Thinking...*).

**Hệ quả:** Giao diện AI phản hồi trực quan siêu nhanh ngay từ Token đầu tiên. Đổi lại, code Frontend phải gánh vác việc tự merge mảng bytes liên tục, sử dụng `TextDecoder` thủ công ròng rã và tự ghép luồng chữ chạy qua Markdown/Mã CSS LaTeX thay vì Backend làm hộ gói gọn 1 lần.

---

### [ADR-2] Giữ Local Video Player thay vì dùng YouTube Embed cho tính năng Visual Context — 06/04/2026

**Bối cảnh:** Mong muốn cao trong việc tiết kiệm dung lượng lưu trữ file của toàn server. Các file Local `.mp4` bài giảng thường ở dung lượng siêu khổng lồ (Nửa GB đến cả vài GB mỗi video). Nhúng (Embed) video YouTube thẳng lên giao diện là idea hoàn hảo lúc đó.

**Các lựa chọn đã xem xét:**
- **Local HTML5 `<video>`**: Tốn disk space trầm trọng. Nhưng thiết kế chuẩn cho phép gọi Javascript API `<canvas>` API chép ảnh nét căng từ hệ thống pixel trên Player để gửi lên Gemini phân tích. Mọi thứ xử lý cục bộ 100%.
- **YouTube Embed IFrame Client-side**: Nhẹ server. Nhưng chính Browser (Chrome/Edge/Safari) tuân thủ chặt chuẩn bảo mật CORS sẽ chặn quyền sử dụng `<canvas>` lấy dữ liệu điểm ảnh hình nêm từ bên trong lõi IFrame gốc thứ 3 lạ hoắc. Trở tay không kịp. Mất trắng tính năng nhận diện thị giác máy tính.
- **YouTube Embed + Server Side `yt-dlp`**: Hiển thị youtube client-side ảo, backend tự động cào ngầm link stream bằng tool `yt-dlp` dán qua `ffmpeg` chép lại 1 mảnh JPEG tĩnh rồi đẩy gộp chung prompt. Cách này quá nặng nề vì đè băng thông backend (tự tải tự phát video để chụp ảnh), sinh ra latency (độ trễ) tận 3-5 giây mới ra lệnh API đầu tiên.

**Quyết định:** Tính năng "Tiền đạo" quan trọng hàng đầu của "Gia sư AI" là nhìn rõ mồn một các Slide toán học/mã code mà học viên đang xem. Trải nghiệm bắt buộc là siêu mượt và không độ trễ. Lựa chọn nghiến răng **Giữ nguyên sử dụng Local HTML5 `<video>` nguyên gốc**, loại thẳng tay các ý tưởng ngông cạn của YouTube.

---

### [ADR-3] Dockerize Project for Distribution & Persistence — 08/04/2026

**Bối cảnh:** Dự án đang ngày một lớn mạnh với nhiều thành phần (FastAPI, Streamlit, SQLite). Việc chia sẻ dự án cho các thành viên khác gặp khó khăn do yêu cầu cài đặt `uv`, cấu hình môi trường Python 3.12 và quản lý 4.5GB dữ liệu video. Ngoài ra, việc duy trì trạng thái Database và Logs cần sự ổn định cao.

**Các lựa chọn đã xem xét:**
- **Manual Setup Guide**: Như đã làm ở README. Ưu điểm là nhẹ nhàng cho máy chủ, nhưng nhược điểm là mệt mỏi cho người mới bắt đầu (cần cài đặt nhiều công cụ).
- **Docker & Docker Compose**: Tạo ra một cấu trúc đóng gói sẵn. 
    - **Thách thức:** Xử lý 4.5GB video. Nếu copy vào image sẽ làm image quá nặng.
    - **Giải pháp:** Sử dụng **Google Drive** để lưu trữ và chia sẻ video, sau đó mount vào container qua cơ chế **Host Volume**.

**Quyết định:** Triển khai **Dockerization** toàn diện kết hợp lưu trữ file nặng trên **Google Drive**.
1. Sử dụng `Dockerfile` đa giai đoạn, cài đặt `uv` để tăng tốc build image.
2. Sử dụng `docker-compose.yml` để chạy song song API và Streamlit.
3. Sử dụng **Host Volumes** cho `data/`, `logs/`, và `app.db`. Người dùng tải thư mục `data/` từ Google Drive về máy trước khi chạy Docker.

**Hệ quả:** Bất kỳ ai cũng có thể chạy dự án chỉ bằng 1 lệnh `docker compose up -d` sau khi đã tải dữ liệu. Dữ liệu video khổng lồ vẫn nằm ở ngoài container nên việc cập nhật code cực kỳ nhanh chóng và không làm phình Image.

---

### [ADR-4] Chuyển đổi kiến trúc sang LangGraph ReAct Agent & Python Sandbox — 11/04/2026

**Bối cảnh:** Các vấn đề trong khóa CS231N phần lớn đòi hỏi khả năng toán học nâng cao (Ví dụ: tính đạo hàm, vector gradient, tính toán tích cực ma trận Backpropagation). LLLM như Gemini/GPT thường xuyên tính nhẩm sai các bước trung gian dẫn đến kết quả cuối cùng vô dụng đối với việc học kỹ thuật. 

**Các lựa chọn đã xem xét:**
- **Advanced Prompting** (Chain of Thought): Yêu cầu AI "work step-by-step". Nhanh, không tốn resource nhưng AI vẫn sinh ra các ảo giác tính bù trừ (hallucinate math operations).
- **Hard-coded Math Modules**: Tự code function đạo hàm vào DB. Rất cứng nhắc, không bao quát được mọi ngóc ngách câu hỏi tự do của học viên.
- **Agentic AI với Code Interpreter**: Triển khai hệ thống ReAct. Trao cho AI quyền truy cập một môi trường Sandbox thực thi code Python động (với `sympy`, `numpy`) để nó nhận câu hỏi -> sinh code Python giải toán -> Sandbox chạy code và trả kết quả Console -> AI phân tích kết quả -> Trả lời user.

**Quyết định:** Nâng cấp sang kiến trúc truy vấn đa trạm bằng công cụ **LangGraph**. Mọi câu hỏi do user đặt ra giờ được đưa vào một **ReAct Agent**. Nếu Agent nhận thấy có tính toán phức tạp, nó sẽ tự xả mã vào luồng `Execute_Python` tool. 
Tuy nhiên, để chặn sinh viên (hoặc hacker) đánh lừa Agent sinh ra các mã tàn phá server (Ví dụ: `os.system("rm -rf /")`), một cơ chế **Security Sandbox** khắt khe được triển khai xen kẽ:
1. Phân tích tĩnh (Static Analysis) bằng regex AST: Chặn mọi thư viện networking (`socket`, `requests`), filesystem (`open`, `os.remove`), bypass/injection (`eval`, `exec`).
2. Hard limits: Chặn CPU limit ở 12-15s bằng `resource.setrlimit`.
3. Ràng buộc đa luồng chạy bằng biến môi trường phân luồng nội cục bộ OpenBLAS.

**Hệ quả:** Tính năng "Giải Toán Bằng Python" mang lại chất lượng và độ chuẩn xác giáo án cực cao. Nhưng sự đánh đổi nằm ở việc Token tiêu tốn tăng mạnh vì quá trình *Sinh mã Python -> Nhận lỗi -> Sinh lại* tốn tận 2-3 lượt chain. Luồng Stream SSE từ FastAPI cũng phải phức tạp hóa để yield các thông báo chờ đặc biệt kiểu ("👾 Math Boss appeared... Fighting....") xuống cho Frontend nhằm dập tắt sự lo âu của User bởi sự im lặng dài do Latency.

---

### [ADR-5] Smart Router — Dual-Model Routing & Provider Abstraction — 11/04/2026

**Bối cảnh:** Sau khi triển khai LangGraph ReAct Agent (ADR-4), mọi câu hỏi — kể cả "Chào bạn" hay "Bài này nói về gì?" — đều phải đi qua chuỗi xử lý nặng nề: LangGraph graph → model lớn (`gpt-5.4-mini`) → potentially tool calls. Chi phí token cao và latency dài cho những câu hỏi đơn giản. Ngoài ra, `ChatOpenAI` bị hardcode khiến hệ thống không thể chạy trên local model (Ollama).

**Các lựa chọn đã xem xét:**
- **Giữ nguyên single model:** Đơn giản nhưng lãng phí. Câu "Chào bạn" tốn ~2000 tokens thay vì ~150.
- **Rule-based keyword router:** Nhanh nhưng dễ phân loại sai. Regex không thể hiểu ngữ nghĩa "Tính gradient" vs "Giải thích gradient là gì".
- **LLM-based Smart Router:** Dùng model nhẹ (`gpt-5.4-nano`) phân loại BLOCKED/SIMPLE/COMPLEX. SIMPLE được trả lời luôn bởi Nano (skip LangGraph hoàn toàn).

**Quyết định:**
1. **Dual-Model Architecture:** Thêm `FAST_MODEL` (gpt-5.4-nano) làm router. Câu đơn giản → Nano trả lời luôn. Câu phức tạp → `DEFAULT_MODEL` (gpt-5.4-mini) + LangGraph + Sandbox.
2. **Provider Abstraction:** Thay toàn bộ `ChatOpenAI` bằng `init_chat_model(model, model_provider=MODEL_PROVIDER)` từ LangChain. Chỉ cần set `.env` để chuyển sang Ollama/Anthropic mà không sửa code.
3. **Graceful Degradation:** `bind_tools()` được bọc trong `try/except` — local model không support function calling vẫn chạy được (chỉ thiếu Python Sandbox).

**Hệ quả:** Tiết kiệm ~80% tokens cho câu hỏi đơn giản (450 vs 2000-3000). Hệ thống linh hoạt — đổi 3 dòng `.env` là chạy từ GPT cloud xuống Ollama local trên máy yếu. Trade-off: thêm 1 LLM call (~150 tokens) cho mọi request, nhưng chi phí này nhỏ hơn nhiều so với tiết kiệm được.

---

### [ADR-6] Hợp nhất `course-first` và `db-review` qua nhánh hybrid giữ nguyên history — 18/04/2026

**Bối cảnh:** `main` mạnh về product flow `Course -> Overview -> Start -> Learning Unit`, còn `db-review` mạnh về PostgreSQL, repository layer, Redis auth hardening, và cấu trúc backend sạch hơn. Merge thẳng một nhánh lên nhánh kia có nguy cơ hoặc làm mất UX course-first, hoặc kéo các giả định lecture-first quay lại làm trung tâm.

**Các lựa chọn đã xem xét:**
- **Cherry-pick vài commit từ `db-review`**: Ít xung đột hơn nhưng bỏ lỡ tính nhất quán của repository layer, auth hardening, migration chain, và tạo vòng lặp "port lẻ tẻ" về sau.
- **Merge `db-review` đè lên `main`**: Giữ được DB hygiene nhưng rủi ro cao với public contract mới của course platform, frontend routes, và flow onboarding/assessment/return-to-course.
- **Tạo `hybrid/integrate-db-review` rồi resolve thủ công**: Lấy `course-first` làm baseline sản phẩm, port có chọn lọc internals từ `db-review`, ghi decision log đầy đủ, rồi merge về `main` bằng merge commit.

**Quyết định:** Chọn phương án **hybrid integration branch**. Giữ `course-first platform` làm public contract và kiến trúc sản phẩm chính; hấp thụ có chọn lọc:
- repository layer cho auth/history/recommendation/assessment,
- `QuestionSelector`,
- `DomainError` + exception handlers,
- Redis-backed auth rate limiting + token denylist + logout revoke,
- PostgreSQL schema v1 + `pgvector` extension,
- compose/runtime hardening.

Merge kết quả về `main` bằng merge commit `fe3ea17` để preserve history thay vì squash.

**Hệ quả:** `main` có nền backend mạnh hơn mà không bỏ course-first UX. Đổi lại, nhánh hybrid phát sinh nhiều conflict kiến trúc nên bắt buộc phải có design docs, merge plan, regression tests, và decision logs để giữ toàn bộ team đi cùng một hướng.

---

### [ADR-7] Giữ `course-first` làm contract công khai, cô lập lecture stack thành compatibility layer — 18/04/2026

**Bối cảnh:** Sau refactor, UI và flow chính của sản phẩm đi theo `Course / LearningUnit`. Tuy nhiên tutor và một phần dữ liệu cũ vẫn phụ thuộc lecture-centric stack. Nếu không khóa boundary, model cũ dễ rò ngược ra public API và frontend.

**Các lựa chọn đã xem xét:**
- **Giữ lecture routes làm trung tâm**: Dễ tận dụng code cũ nhưng đi ngược thiết kế course-first và làm contract sản phẩm tiếp tục mơ hồ.
- **Xóa ngay toàn bộ lecture stack**: Kiến trúc đẹp hơn nhưng rủi ro phá tutor compatibility và retrieval hiện có.
- **Cô lập lecture stack sau adapter/service boundary**: Public vẫn dùng `Course`, `CourseOverview`, `StartDecision`, `LearningUnit`; lecture chỉ còn phục vụ tutor và compatibility routing.

**Quyết định:** Chọn phương án **adapter boundary**:
- `src/routers/courses.py`, `src/schemas/course.py`, `src/services/course_*` và `src/services/learning_unit_service.py` là contract public chuẩn.
- `/api/lectures/*`, legacy lecture id, và mapping canonical-to-legacy chỉ còn là compatibility layer cho tutor/retrieval.
- Bổ sung lecture-aware scope guard để tutor không vượt ngữ cảnh learning unit đang học.

**Hệ quả:** Hướng migration dài hạn rõ ràng hơn, UI không còn bị khóa vào lecture model cũ. Đổi lại, hệ thống phải duy trì thêm mapping/guard ở tầng adapter trong giai đoạn chuyển tiếp.

---

### [ADR-8] Tách `data/` theo vai trò pipeline: `bootstrap / courses / working / final_artifacts` — 22/04/2026

**Bối cảnh:** Sau khi chạy các prompt pipeline P1→P5 cho CS224n và CS231n, thư mục `data/` bắt đầu lẫn nhiều loại artifact khác nhau:
- bootstrap fixture cho app runtime,
- course asset gốc,
- working inputs/output trung gian cho prompt pipeline,
- final cross-course artifacts dùng để ingest,
- experiment outputs cho ModernBERT / SciBERT / GPT review.

Việc để tất cả nằm ngang hàng ở `data/` làm phát sinh 3 rủi ro:
- script và test tiếp tục trỏ vào path cũ hoặc nhầm artifact cũ với artifact final,
- các file P2/P5 cross-course bị đặt sai ngữ nghĩa trong folder của một course đơn lẻ,
- review/debug sau này khó phân biệt cái nào là canonical, cái nào chỉ là working scratch.

**Các lựa chọn đã xem xét:**
- **Giữ nguyên layout cũ và chỉ ghi chú bằng README**: ít thay đổi path nhưng không giải quyết được drift và ambiguity trong runtime/test.
- **Bundle toàn bộ final data thành JSONL export riêng**: rõ ràng cho ingest nhưng thêm một lớp artifact mới, dễ lệch với file source thật của prompt pipeline.
- **Tổ chức lại `data/` theo vai trò lưu trữ**: giữ file source thật, chỉ đổi vị trí để semantic rõ hơn, rồi patch runtime/test/scripts theo layout mới.

**Quyết định:** Chọn layout vai trò:
- `data/bootstrap/` cho fixture seed nhẹ của app,
- `data/courses/CS224n`, `data/courses/CS231n` cho raw + processed per-course assets,
- `data/working/` cho `p2`, `p3_inputs`, `p5` và các artifact trung gian còn phục vụ validation/rerun,
- `data/final_artifacts/cs224n_cs231n_v1/` cho canonical cross-course final outputs (`p2`, `p5`, `gpt54`, visualizations, model experiment logs).

Đồng thời:
- thêm `src/data_paths.py` làm nơi định nghĩa canonical path dùng lại cho scripts/services,
- sửa `.gitignore` để **chỉ ignore video assets** dưới `data/courses/**/videos/*`,
- loại bỏ bản `P2` single-course lỗi thời của CS224n vì đã bị supersede bởi bản cross-course final,
- chuẩn hóa `CS231n/syllabus.json` theo schema của `CS224n/syllabus.json` nhưng vẫn giữ `lecture_id` canonical cũ để không phá compatibility.

**Hệ quả:** 
- Path runtime/test/script rõ vai trò hơn và ít nhầm artifact hơn.
- Các final outputs dùng để ingest/review được gom đúng chỗ, không còn lẫn trong tree của từng course.
- Đổi lại, nhiều file metadata và script mặc định phải được patch lại đồng bộ; việc review path cũ sau refactor trở thành bước bắt buộc.
