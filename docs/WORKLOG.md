# Worklog

Ghi lại các quyết định kỹ thuật, phân công, và brainstorming của nhóm.

---

## Các Quyết Định Kỹ Thuật (ADR)

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
