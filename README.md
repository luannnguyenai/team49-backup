# 🎓 AI Tutor: Real-time Multi-modal Learning Platform

Hệ thống hỗ trợ học tập cá nhân hóa sử dụng AI để giải đáp thắc mắc của học viên trực tiếp dựa trên ngữ cảnh bài giảng đa phương thức (Video Frame + Transcript + ToC). Đã được nâng cấp để mang lại trải nghiệm thời gian thực tuyệt đối.

## 🚀 Tính năng nổi bật (High-Tech Features)

- **⚡ Real-time Streaming Response**: Trải nghiệm UI theo thời gian thực. AI suy nghĩ đến đâu, chữ hiện ra ngay đến đó (gõ máy chữ), tích hợp animation *“🧠 Thinking...”* cho cảm giác chân thực, thay vì phải chờ đợi xoay vòng tròn.
- **📸 Multi-modal Visual Context**: Tự động chụp ảnh màn hình từ Video Player tĩnh của bạn tại thời điểm hỏi. Giúp phân tích chính xác slide bài giảng, code hay bản vẽ bảng trắng mà không cần gửi video lớn lên Cloud.
- **📐 Markdown & LaTeX Rendering**: Hỗ trợ hiển thị Markdown chuẩn xác. Tích hợp thư viện KaTeX để hiển thị toàn bộ các công thức toán học/deep learning phức tạp nhất cực kỳ đẹp mắt.
- **🗂️ 10-min Context Window & RAG-Free**: Tự động trích xuất +/- 5 phút Transcript kết hợp cùng ToC tổng quát (Global Context) giúp AI trả lời cực sát ngữ cảnh mà không cần setup Vector Database nặng nề.
- **📝 Dual-layer Track & Logs**: 
  - Lưu vào **Database (SQLite - `app.db`)** để dễ dàng kết nối phân tích App.
  - Ghi log siêu tốc ra file **`logs/qa_history.log`** dưới định dạng chuẩn JSON để kỹ sư dễ theo dõi trực tiếp, bắt lỗi mà không cần query Database.
- **🛡️ Robust Error Handling**: Cơ chế theo dõi dòng stream thông minh, nếu AI / API báo lỗi quá hạn mức hoặc ngắt quãng, giao diện sẽ bắt tức thì và báo lỗi đỏ mà không bao giờ bị kẹt (hang).

## ⚙️ Cơ chế hoạt động (How it works)

Khi bạn bấm nút **"Hỏi Gia sư"** (hoặc nhấn phím `Enter`):
1. **Frontend** lấy mốc thời gian hiện tại (`currentTime`) và tự động trích xuất 1 ảnh (Frame) từ thẻ `<video>` HTML5 thông qua thẻ `<canvas>`.
2. Trình duyệt gửi request (kèm Frame, Timestamp và nội dung câu hỏi) xuống FastApi Backend.
3. **Backend RAG** đối chiếu mốc Timestamp vào DB SQLite, trích xuất:
   - Hệ thống Mục lục chung (ToC summary).
   - Đoạn hội thoại xung quanh lúc bạn xem (+/- 5 phút).
4. **Gemini Engine** (`gemini-3-flash-preview`) kích hoạt streaming. Frontend đọc trực tiếp stream raw text qua kỹ thuật `ReadableStream`.
5. Sau khi stream xong xuôi, Frontend tự động kích hoạt `marked.js` và `KaTeX` phủ cấu trúc định dạng lên đoạn text tĩnh để cho ra câu trả lời gọn mượt & khoa học.
6. Khi hoàn tất, sự kiện được lưu song song vào `app.db` và ghi JSON chuẩn xác vào ổ cứng `logs/`.

## 📂 Cấu trúc dự án

```text
├── data/               # Chứa Local Video (.mp4), ToC (.txt) và Transcript (.txt)
├── logs/               # Nơi lưu vết Log câu hỏi & câu trả lời theo phiên (QA History)
├── src/
│   ├── api/            # FastAPI Backend & Server-sent Events (Streaming)
│   │   └── static/     # Giao diện Web UI (UI Styling, Markdown, LaTeX)
│   ├── models/         # SQLAlchemy Models (SQLite)
│   ├── services/       # Core Logic: Ingestion, Streaming LLM (Gemini)
│   └── config.py       # Cấu hình API Key & Model
├── app.db              # Database SQLite lưu mục lục, transcript, lịch sử (Bảo mật)
├── test_stream.py      # Script chạy debug độc lập cho luồng Stream Gemini
└── pyproject.toml      # Quản lý dependency tự động bằng uv
```

## 🛠️ Cài đặt & Khởi chạy

### 1. Yêu cầu hệ thống
- Tải và cài đặt [uv](https://github.com/astral-sh/uv).
- Python 3.10+. Khuyên dùng Linux / macOS.

### 2. Thiết lập môi trường
```bash
# Khởi tạo môi trường ảo và cài đặt thư viện nhanh qua UV
uv venv .venv
source .venv/bin/activate.fish  # Hoặc .bash tùy shell
uv sync
```

### 3. Cấu hình API Key
Tạo file `.env` từ `.env.example` và điền:
```env
GEMINI_API_KEY=AIza...
DEFAULT_MODEL=gemini-3-flash-preview  # Model sử dụng
```

### 4. Nạp dữ liệu (Ingestion)
Đảm bảo đã có mp4/transcript ở `/data`.
```bash
uv run python -m src.services.ingestion
```

### 5. Khởi chạy Server
```bash
uv run python -m src.api.app
```
Truy cập giao diện tại: **`http://localhost:8000`**

---
## 🧪 Trải nghiệm & Phân tích
1. Vào `http://localhost:8000`. Chọn bài giảng NLP có nhiều công thức tự đánh giá.
2. Tại đoạn trình bày công thức Word Vectors, hãy gõ công thức hoặc hỏi logic "Toán học của phần này có ý nghĩa gì?"
3. AI sẽ phân tích hình vẽ công thức trên Slide và phản hồi với chuẩn LaTeX tuyệt đẹp theo quá trình Typing Real-time.
4. Mở thêm 1 cửa sổ terminal: `tail -f logs/qa_history.log` để xem hệ thống đang tự động theo dõi bạn thế nào.
