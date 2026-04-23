# Weekly Journal

Ghi lại hành trình xây dựng sản phẩm mỗi tuần — những gì đã làm, học được gì, AI giúp như thế nào.

---

## Tuần 1 — 06/04/2026

**Thành viên:** Nguyễn Duy Minh Hoàng, Nguyễn Đôn Đức, Nguyễn Lê Minh Luân

### Đã làm
- Chuyển đổi kiến trúc backend API tĩnh sang **Real-time Streaming** bằng `StreamingResponse` (Server-Sent Events).
- Triển khai **Visual Context (Multi-modal)** lấy frame trực tiếp qua Canvas HTML5 gửi thẳng cho Gemini API.
- Tích hợp thư viện xử lý **Markdown** (`marked.js`) và **LaTeX/Math** (`KaTeX`) vào giao diện chat thời gian thực.
- Xây dựng hệ thống ghi log song song: lưu `app.db` (SQLite) cho truy xuất dữ liệu & ghi file `logs/qa_history.log` dạng JSON cho developer dễ theo dõi trực tiếp.

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
- **Di cư dữ liệu CS231N**: Chuyển đổi toàn bộ hệ thống từ CS224N (cũ) sang Stanford CS231N (Spring 2025). Khắc phục thành công các lỗi không nhất quán về định dạng ToC và Transcript.
- **Chuẩn hóa mốc thời gian**: Toàn bộ hệ thống (Context & AI Response) hiện đã sử dụng định dạng `HH:MM:SS`, giúp người dùng dễ dàng đối chiếu trực tiếp trên Video Player.
- **Dockerization**: Hoàn thiện Dockerfile (tối ưu bằng `uv`) và `docker-compose.yml`, hỗ trợ chạy song song cả FastAPI Backend và Streamlit Lab UI chỉ với 1 lệnh.
- **Auto-Sanitization**: Xây dựng logic tự động làm sạch tiêu đề bài giảng (`Lecture X: Topic`), giúp giao diện dropdown luôn chuyên nghiệp.
- **Prompt Engineering**: Lưu trữ bộ Prompt "expert analyzer" vào thư mục `prompts/` để phục vụ việc trích xuất nội dung bài giảng chất lượng cao trong tương lai.

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
- **Kiến trúc Agentic (LangGraph):** Chuyển đổi LLM Service từ AI trả lời trơn sang một ReAct Agent thực thụ. Tích hợp Python Sandbox tool giúp AI có khả năng tự sinh code giải quyết các bài toán toán học phức tạp (đạo hàm, tích phân, ma trận) trong khóa CS231N thay vì "đoán" kết quả.
- **Bảo mật Sandbox (Security Hardening):** Cô lập hoàn toàn Python Sandbox với hệ thống. Chặn I/O (File System, Network), bắt lỗi bằng phân tích AST (Static Analysis) trước khi chạy, và giới hạn CPU (12-15s), ngăn chặn Thread-bombing.
- **Bối cảnh đàm thoại (Conversational Memory):** Inject trực tiếp 5 lượt Q&A gần nhất vào hệ thống prompt để duy trì bối cảnh tốt hơn khi chat.
- **Tracking & Logging:** 
  - Chuyển lịch sử QA sang dạng JSONL song song với CSDL để dễ dàng query. 
  - Lưu tiến độ học tập (Learning Progress) theo session ở phía Frontend, tự động seek video quay lại đúng phút đã dừng.
- **Guardrails & Feedback:** 
  - Áp dụng Zero-shot classification prompt để lọc Intents (Jailbreak, Off-topic, Inappropriate) trước khi đưa vào Agent, tránh lãng phí token LLM chính.
  - Tích hợp User Rating (👍/👎) vào trực tiếp giao diện Frontend. Tính năng "Silent Retry" dưới nền được thêm khi gặp lỗi truy xuất.

### Khó nhất tuần này
- **Cân bằng hiệu suất LangGraph:** Việc sử dụng LangGraph kết hợp với ToolNode khiến log trả về frontend phức tạp vì đan xen giữa Token sinh mã và output trả về từ Sub-process sandbox. Khắc phục bằng SSE (Server-Sent Events) debounce sự kiện hiển thị hộp trạng thái `🧠 Thinking...` 
- **Thiết kế Prompt Guardrail fail-open:** Việc bắt sai Intent quá đà làm giảm trải nghiệm. Thiết kế lại Rule set nhẹ nhưng chặn những "Jailbreak" cơ bản theo nguyên lý fail-open khi module lỗi.

### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Antigravity (Claude Opus 4.6 / Gemini 3.1 Pro) | Migrate LangGraph, code Sandbox hardening, thiết kế Guardrails. | Nâng tầm MVP từ một chat-bot đơn thuần trở thành Agent tự giải toán. Tự động hóa được tiến trình lưu dữ liệu bằng API. |

### Học được
- Kiến trúc ReAct (Reasoning and Acting) thay đổi cục diện giải thích code & thuật toán của Tutor. Tuy nhiên độ trễ thời gian trả lời tăng lên cần thông báo trạng thái "Trận đánh Boss Toán học" rõ ràng xuống giao diện để user không có cảm giác App bị sập.

### Nếu làm lại, sẽ làm khác
- Thiết kế Data Schema cho "Session" và "User" ngay từ sớm. Hiện nay tạm thời dùng localStorage UUID bypass Auth để làm MVP nhanh chóng.

---

## Tuần 4 — 18/04/2026

**Thành viên:** Nguyễn Duy Minh Hoàng, Nguyễn Đôn Đức, Nguyễn Lê Minh Luân

### Đã làm
- Hợp nhất nhánh `hybrid/integrate-db-review` vào `main` bằng merge commit, giữ nguyên history thay vì squash.
- Tích hợp nền **PostgreSQL schema v1** vào app course-first: migration head mới, `pgvector` extension, audit table `mastery_history`, và fix engine non-pooled cho sync threadpool tasks.
- Đưa vào **repository layer** cho auth/history/recommendation/assessment và nối flow assessment qua `QuestionSelector` thay vì truy cập data layer rải rác.
- Harden auth/runtime bằng **Redis-backed rate limiting**, **token denylist**, **logout revoke endpoint**, fix startup/CORS/config, và healthcheck/compose migration.
- Hoàn thiện flow **course-first platform** trên hybrid: public catalog, personalized catalog, overview, start gate, learning unit, in-context tutor, dashboard presenters, user skill overview, và compatibility redirects cho route cũ.
- Bổ sung lớp ổn định cho tutor và UI: buffer NDJSON stream chunks, regression test cho stale chapter response khi đổi lecture nhanh, e2e smoke coverage và route tests cho course platform.

### Khó nhất tuần này
- **Hòa giải hai nhánh có trung tâm kiến trúc khác nhau**: một bên course-first, một bên database/repository review. Nếu resolve file theo kiểu "gộp cú pháp" thì rất dễ làm mất contract công khai hoặc kéo lecture stack cũ quay lại.
- **Giữ auth journey không gãy sau khi harden backend**: login, onboarding, assessment, return-to-course, logout revoke và middleware public routes phải khớp nhau ở cả backend lẫn frontend.
- **Ổn định behavior bất đồng bộ của learning experience**: tutor stream NDJSON và race condition lúc đổi bài giảng nhanh đều là lỗi khó thấy nếu không có regression test rõ ràng.

### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| AI coding agents (Codex / Claude / Gemini qua hook logging) | So sánh nhánh, rà conflict, scaffold test hồi quy, và tổng hợp design docs cho hybrid merge | Giữ được history merge, hấp thụ DB hygiene vào `main`, đồng thời không làm mất flow course-first của sản phẩm |

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
- Hoàn thiện chuỗi artifact cho ingestion pipeline nhiều bước: rà soát P2, P3, P4, P5 cho hai khóa **CS224n** và **CS231n**, kiểm tra đủ segment, đủ question bank, calibration bootstrap, prerequisite graph và các file review phụ trợ.
- Tổ chức lại toàn bộ thư mục `data/` theo vai trò rõ ràng:
  - `data/bootstrap/`
  - `data/courses/`
  - `data/working/`
  - `data/final_artifacts/`
- Patch các script/service/test chính để dùng path mới thay vì path cũ kiểu `data/CS231n`, `data/course_bootstrap`, `data/p3_inputs`, `data/p5_inputs`.
- Chuẩn hóa `CS231n/syllabus.json` theo schema mới đang dùng ở `CS224n/syllabus.json`, bổ sung `assets`, `title`, `youtube_title`, `topic`, `year`, `type`, `custom_order` nhưng vẫn giữ các field cũ như `lecture_id`, `lecture_title`, `core_topics`, `scope_keywords`.
- Dọn artifact P2 single-course cũ của CS224n vì nó là run lỗi thời/failed và đã bị supersede bởi bản P2 final cross-course.
- Chỉnh `.gitignore` để chỉ ignore video assets; transcript, slides, JSON artifact nhẹ có thể đưa lên GitHub.

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
- Khóa lại snapshot schema của nhánh `rin/implement`, tách rõ 4 lớp:
  - runtime ORM
  - legacy adapter
  - canonical artifact
  - learner/planner stub persistence
- Bổ sung 6 bảng stub mới cho learner/planner phía DB:
  - `learner_mastery_kp`
  - `goal_preferences`
  - `waived_units`
  - `plan_history`
  - `rationale_log`
  - `planner_session_state`
- Viết tài liệu thiết kế và implementation plan riêng cho hướng **production DB evolution** để người làm integration sau có thể nối code mà không phải suy luận source-of-truth từ runtime cũ.

### Khó nhất tuần này
- Phân biệt rõ đâu là việc **khóa schema đích** và đâu là việc **wire logic runtime**. Nếu làm lẫn hai việc trong cùng một lượt sẽ rất dễ tạo double-write bug hoặc nửa cũ nửa mới.
- Giữ được nhịp production: không chỉ “thêm bảng cho có”, mà phải mô tả rõ authoritative table, compatibility table, migration order và handoff contract cho người làm bước sau.

### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| AI coding agents (Codex) | Rà schema hiện tại, đối chiếu canonical artifacts, thêm stub learner/planner tables, và viết production DB evolution docs | Tạo được landing zone DB cho phase production tiếp theo mà chưa phá runtime cũ |

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
