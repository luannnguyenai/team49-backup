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

