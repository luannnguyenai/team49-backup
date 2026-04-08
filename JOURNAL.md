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

