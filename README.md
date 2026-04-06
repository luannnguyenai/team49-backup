# 🎓 AI Tutor: Personal Learning Platform

Hệ thống hỗ trợ học tập cá nhân hóa sử dụng AI để giải đáp thắc mắc của học viên trực tiếp dựa trên ngữ cảnh bài giảng (Video + Transcript + ToC). 

## 🚀 Tính năng nổi bật (High-Tech Features)

- **⚡ RAG-Free Table of Contents Routing**: Sử dụng mục lục (ToC) đã tóm tắt để định hướng câu hỏi, đạt tốc độ phản hồi cực nhanh (< 3 giây) mà không cần Vector Database phức tạp.
- **📸 Visual Context (Multi-modal)**: Tự động chụp ảnh frame video tại thời điểm hỏi để AI có thể "nhìn thấy" slide hoặc bảng trắng giảng viên đang giảng.
- **🧠 Gemini 2.0/3 Thinking Mode**: Kích hoạt chế độ suy nghĩ sâu (Thinking High) giúp AI lập luận logic trước khi đưa ra câu trả lời cho các vấn đề phức tạp.
- **🔍 20-min Transcript Window**: Cung cấp ngữ cảnh transcript +/- 10 phút xung quanh thời điểm đang xem để đảm bảo câu trả lời sát thực tế nhất.
- **📊 QA History & Tracking**: Tự động lưu vết mọi câu hỏi, câu trả lời và cả quá trình suy nghĩ (thoughts) của AI vào SQLite để theo dõi tiến độ học tập.
- **💻 Premium Web UI**: Giao diện Dark theme hiện đại, đồng bộ thời gian video theo thời gian thực (Native HTML5/JS).

## 📂 Cấu trúc dự án

```
├── data/               # Chứa Video (.mp4), ToC (.txt) và Transcript (.txt)
├── src/
│   ├── api/            # FastAPI Backend & Static Web UI
│   ├── models/         # SQLAlchemy Models (SQLite)
│   ├── services/       # Core Logic: Ingestion, LLM (Gemini), Parser
│   └── config.py       # Cấu hình API Key & Model
├── app.db              # Database SQLite (chứa ToC, Transcript, History)
└── pyproject.toml      # Quản lý dependency bằng uv
```

## 🛠️ Cài đặt & Khởi chạy

### 1. Yêu cầu hệ thống
- Tải và cài đặt [uv](https://github.com/astral-sh/uv).
- Python 3.10+.

### 2. Thiết lập môi trường
```bash
# Clone dự án
git clone <repo-url>
cd A20-App-049

# Khởi tạo môi trường ảo và cài đặt thư viện
uv venv .venv
source .venv/bin/activate.fish  # Hoặc .bash tùy shell
uv sync
```

### 3. Cấu hình API Key
Tạo file `.env` từ `.env.example` và điền:
```env
GEMINI_API_KEY=AIza...
DEFAULT_MODEL=gemini-2.0-flash-thinking-exp  # Hoặc gemini-3-flash-preview
```

### 4. Nạp dữ liệu (Ingestion)
Chuẩn bị các file Video, ToC và Transcript trong thư mục `data/`, sau đó chạy:
```bash
uv run python -m src.services.ingestion
```

### 5. Khởi chạy ứng dụng
```bash
uv run python -m src.api.app
```
Truy cập giao diện tại: **`http://localhost:8000`**

---
## 🧪 Cách kiểm thử hệ thống
1. Mở trình duyệt tại cổng 8000.
2. Chọn bài giảng NLP.
3. Khi video đang chạy đến phần có Slide, gõ câu hỏi bất kỳ.
4. Quan sát phần **💭 Thoughts** để thấy AI đang "suy luận" và câu trả lời đa phương thức cực kỳ chính xác.
