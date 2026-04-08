# 🎓 AI Tutor: Real-time Multi-modal Learning Platform

Hệ thống hỗ trợ học tập cá nhân hóa sử dụng AI để giải đáp thắc mắc của học viên trực tiếp dựa trên ngữ cảnh bài giảng đa phương thức (Video Frame + Transcript + ToC).

## 🚀 Tính năng nổi bật

- **⚡ Real-time Streaming**: Phản hồi tức thì từng chữ, tích hợp hiệu ứng "🧠 Thinking" chân thực.
- **📸 Multi-modal Context**: Tự động chụp ảnh slide bài giảng tại thời điểm hỏi để AI phân tích trực quan.
- **🕒 HH:MM:SS Precision**: Mọi mốc thời gian trong ngữ cảnh và câu trả lời đều được chuẩn hóa dạng `Giờ:Phút:Giây`.
- **🗂️ Auto-Sanitized ToC**: Hệ thống tự động làm sạch tiêu đề bài giảng (ví dụ: `Lecture 1: Introduction`) giúp danh sách chọn lựa luôn gọn gàng.
- **📐 Math & LaTeX**: Hiển thị công thức toán học/Deep Learning sắc nét qua KaTeX.

## 🐳 Khởi chạy nhanh với Docker (Khuyên dùng)

Dự án đã được Docker hóa hoàn chỉnh, giúp bạn bỏ qua bước cài đặt môi trường phức tạp.

1.  **Thiết lập môi trường**: Tạo file `.env` và điền `GEMINI_API_KEY`.
2.  **Tải dữ liệu bài giảng**: Tải thư mục `data/` (Video, Transcript, ToC) từ Google Drive của nhóm tại đây: [Link Google Drive của bạn] và giải nén vào thư mục gốc của dự án.
3.  **Khởi chạy**:
    ```bash
    docker compose up -d
    ```
3.  **Truy cập**:
    - **Giao diện chính (HTML/JS)**: `http://localhost:8000`
    - **Giao diện Lab (Streamlit)**: `http://localhost:8501`

---

## 🛠️ Cài đặt & Khởi chạy thủ công

### 1. Thiết lập môi trường
```bash
uv venv .venv
source .venv/bin/activate  # Hoặc activate.fish / activate.ps1
uv sync
```

### 2. Cấu hình .env
```env
GEMINI_API_KEY=AIza...
DEFAULT_MODEL=gemini-3-flash-preview
```

### 3. nạp dữ liệu (Ingestion)
Để nạp dữ liệu bài giảng CS231N vào hệ thống:
```bash
PYTHONPATH=. uv run python scripts/ingest_cs231n.py
```

### 4. Khởi chạy Backend
```bash
PYTHONPATH=. uv run python src/api/app.py
```

---

## 📂 Cấu trúc thư mục quan trọng
- `src/`: Mã nguồn chính (API, Models, Services).
- `data/cs231n/`: Chứa Video, Transcript và ToC JSON.
- `prompts/`: Chứa các mẫu prompt tối ưu để trích xuất dữ liệu bài giảng.
- `app.db`: Database SQLite (Tự động khởi tạo khi chạy Docker/API).
- `logs/`: Lịch sử câu hỏi dưới dạng JSON.

## 🧪 Tài liệu bổ sung
- Sử dụng prompt trong `prompts/lecture_extraction_prompt.txt` để trích xuất summary bài giảng mới đạt độ chính xác cao nhất.
