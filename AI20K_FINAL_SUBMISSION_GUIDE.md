# AI20K Build Phase — Tổng hợp yêu cầu nộp dự án cuối kỳ

> Tài liệu này tổng hợp lại toàn bộ yêu cầu trong slide thông báo của BTC, đồng thời bổ sung convention viết report/README và checklist file cần chuẩn bị trước khi nộp.

---

## 1. Thời gian nộp bài

| Hạng mục | Thông tin |
|---|---|
| Mở nộp bài | **11/05** |
| Hạn chót | **23:59 ngày 17/05** |
| Khuyến nghị | Nộp sớm để tránh lỗi kỹ thuật và tránh bị trừ điểm |

**Lưu ý quan trọng:** hệ thống sẽ đóng vào **23:59 ngày 17/05**, vì vậy team nên hoàn thiện và kiểm tra toàn bộ link trước deadline ít nhất vài giờ.

---

## 2. Hai kênh nộp bài bắt buộc

Dự án được đánh giá song song qua **GitHub Repository** và **Form nộp bài**.

| Kênh nộp | Vai trò | Nội dung chính |
|---|---|---|
| **GitHub Repository** | Đánh giá kỹ thuật | Source code, cấu trúc mã nguồn, kiến trúc hệ thống, tiến độ phát triển |
| **Form nộp bài** | Tổng hợp sản phẩm | Live URL, video demo, pitch deck và các link tài liệu |

**Kết luận:** GitHub và Form đều quan trọng. Không nên chỉ chuẩn bị một bên.

---

## 3. Yêu cầu đối với GitHub Repository

Repository cần rõ ràng để BTC có thể chấm kỹ thuật nhanh hơn.

### 3.1. Các hạng mục bắt buộc trong repository

| STT | Hạng mục | Yêu cầu |
|---|---|---|
| 1 | **Source Code** | Có đầy đủ frontend, backend, database, agent/AI logic, API, file cấu hình và tài nguyên chạy dự án |
| 2 | **README.md** | Đặt tại thư mục gốc; mô tả dự án, mục tiêu, tính năng, công nghệ, cách cài đặt, cách chạy và cách sử dụng |
| 3 | **Architecture** | Có sơ đồ mô tả User, Frontend, Backend/API, Database, AI Agent/LLM, External Services và luồng dữ liệu chính |
| 4 | **AI Logs** | Có prompt mẫu, chat logs, cấu hình webhook theo hướng dẫn của BTC nếu có |

### 3.2. Repo nên thể hiện được điều gì?

Người chấm cần nhìn vào repo và hiểu nhanh:

- Dự án giải quyết vấn đề gì.
- Sản phẩm chạy như thế nào.
- Thành phần kỹ thuật gồm những gì.
- AI Agent/LLM nằm ở đâu trong hệ thống.
- Dữ liệu đi qua các thành phần nào.
- Team đã test, đánh giá và cải thiện sản phẩm ra sao.
- Ai phụ trách phần nào và tiến độ hoàn thành như thế nào.

---

## 4. README.md cần có những nội dung nào?

README là tài liệu quan trọng nhất trong repo. README càng rõ thì người chấm càng ít mất thời gian kiểm tra.

### 4.1. Checklist nội dung README.md

- [ ] Tên dự án
- [ ] Mô tả ngắn gọn
- [ ] Mục tiêu / vấn đề cần giải quyết
- [ ] Tính năng chính
- [ ] Công nghệ sử dụng
- [ ] Hướng dẫn cài đặt
- [ ] Hướng dẫn chạy dự án
- [ ] Hướng dẫn sử dụng sản phẩm
- [ ] Link Live URL
- [ ] Link video demo
- [ ] Link pitch deck
- [ ] Link architecture diagram
- [ ] Link AI logs
- [ ] Link journal / worklog / evidence nếu để ngoài repo
- [ ] Thông tin team và phân công thành viên
- [ ] Các giới hạn hiện tại và hướng phát triển tiếp theo

### 4.2. Cấu trúc README.md khuyến nghị

```md
# Tên dự án

## Quick Links
- Live URL:
- Demo Video:
- Pitch Deck:
- Architecture Diagram:
- AI Logs:
- Worklog:
- Evaluation Evidence:

## 1. Giới thiệu dự án
Mô tả ngắn gọn sản phẩm, người dùng mục tiêu và bối cảnh sử dụng.

## 2. Vấn đề cần giải quyết
Nêu rõ pain point, nhu cầu thực tế và lý do sản phẩm cần tồn tại.

## 3. Giải pháp
Mô tả sản phẩm giải quyết vấn đề như thế nào.

## 4. Tính năng chính
- Tính năng 1
- Tính năng 2
- Tính năng 3

## 5. Kiến trúc hệ thống
Chèn ảnh kiến trúc hoặc Mermaid diagram.

## 6. Công nghệ sử dụng
| Thành phần | Công nghệ |
|---|---|
| Frontend | ... |
| Backend/API | ... |
| Database | ... |
| AI Agent/LLM | ... |
| Deployment | ... |

## 7. Cài đặt và chạy local
```bash
git clone ...
cd ...
cp .env.example .env
...
```

## 8. Biến môi trường
Không commit file `.env`. Chỉ commit `.env.example`.

## 9. Cách sử dụng sản phẩm
Mô tả luồng sử dụng chính bằng từng bước.

## 10. Demo và kết quả
Thêm screenshot, link demo, kết quả test, metrics chính.

## 11. Evaluation
Mô tả test cases, metrics, kết quả, failure cases và nhận xét.

## 12. Team & phân công công việc
| Thành viên | Vai trò | Công việc |
|---|---|---|

## 13. Hạn chế và hướng phát triển
Nêu rõ những phần chưa hoàn thiện và kế hoạch cải thiện.
```

---

## 5. Architecture cần trình bày như thế nào?

Slide yêu cầu architecture thể hiện được các thành phần chính:

```text
User
  ↓
Frontend
  ↓
Backend/API
  ↓
Database
  ↓
AI Agent / LLM
  ↓
External Services
```

Ngoài sơ đồ thành phần, cần mô tả thêm **luồng dữ liệu**:

1. User thao tác trên giao diện.
2. Frontend gửi request đến Backend/API.
3. Backend xử lý logic nghiệp vụ.
4. Backend đọc/ghi dữ liệu vào Database.
5. Khi cần AI, Backend gọi AI Agent/LLM.
6. AI Agent/LLM có thể gọi External Services nếu hệ thống có tích hợp.
7. Kết quả được trả về Backend rồi hiển thị lại cho User.

### 5.1. File architecture nên nộp

Nên có ít nhất một trong các dạng sau:

- `docs/architecture.md`
- `docs/architecture.png`
- `docs/architecture.drawio`
- `docs/architecture.mermaid`
- Link Figma / Excalidraw / Draw.io public

### 5.2. Nội dung architecture nên có

- [ ] Sơ đồ tổng quan hệ thống
- [ ] Luồng dữ liệu chính
- [ ] Vị trí của AI Agent/LLM trong hệ thống
- [ ] Database schema hoặc mô tả bảng chính nếu có database
- [ ] API chính nếu có backend
- [ ] External services nếu có dùng
- [ ] Deployment diagram nếu có deploy nhiều service

---

## 6. Nhật ký, worklog và minh chứng

BTC nhấn mạnh: **không chỉ nộp code, hãy nộp cả quá trình**.

### 6.1. Weekly Journal

Mục tiêu: ghi lại tiến độ theo từng tuần.

Nên có các thông tin:

- Mục tiêu tuần
- Việc đã làm
- Kết quả đạt được
- Khó khăn gặp phải
- Cách team giải quyết
- Việc cần làm tiếp theo

File gợi ý:

```text
docs/journal/week-01.md
docs/journal/week-02.md
docs/journal/week-03.md
```

Mẫu nội dung:

```md
# Weekly Journal — Week 01

## Mục tiêu tuần
...

## Kết quả đã đạt được
...

## Khó khăn
...

## Cách giải quyết
...

## Kế hoạch tuần sau
...
```

---

### 6.2. Worklog

Mục tiêu: thể hiện ai làm gì, làm khi nào, trạng thái ra sao.

Nên trình bày dạng bảng:

```md
# Worklog

| Ngày | Thành viên | Công việc | Trạng thái | Ghi chú |
|---|---|---|---|---|
| 12/05 | A | Làm frontend login | Done | ... |
| 12/05 | B | Thiết kế database schema | Doing | ... |
| 13/05 | C | Tích hợp AI Agent | Done | ... |
```

Trạng thái nên thống nhất:

- `Todo`
- `Doing`
- `Done`
- `Blocked`
- `Review`

File gợi ý:

```text
docs/worklog.md
```

---

### 6.3. Evaluation Evidence

Mục tiêu: chứng minh sản phẩm đã được kiểm thử và đánh giá.

Cần trả lời được các câu hỏi:

- [ ] Sản phẩm có đúng mục tiêu không?
- [ ] Agent có xử lý chính xác không?
- [ ] Hệ thống có ổn định không?
- [ ] Đã kiểm thử nhiều tình huống chưa?

Nên có các loại minh chứng:

- Báo cáo đánh giá
- Kết quả test
- Bộ câu hỏi kiểm thử
- Metrics
- Feedback
- Ảnh chụp màn hình
- Log lỗi và cách xử lý
- Failure cases và phân tích nguyên nhân

File gợi ý:

```text
docs/evaluation/evaluation-report.md
docs/evaluation/test-cases.md
docs/evaluation/screenshots/
docs/evaluation/metrics.csv
```

---

## 7. AI Logs cần chuẩn bị gì?

AI Logs cần giúp người chấm hiểu cách team sử dụng, test và kiểm soát AI Agent/LLM.

### 7.1. Nội dung nên có

- Prompt mẫu
- Chat logs
- Input/output mẫu
- Các case thành công
- Các case thất bại
- Cách team cải thiện prompt hoặc logic agent
- Cấu hình webhook theo hướng dẫn của BTC nếu có
- Cấu hình model/provider nếu phù hợp và không chứa secret

### 7.2. Format AI Logs khuyến nghị

```md
# AI Logs

## Case 01: Người dùng hỏi thông tin cơ bản

### User Input
...

### Prompt / System Instruction
...

### Agent Output
...

### Expected Output
...

### Evaluation
- Correctness:
- Relevance:
- Latency:
- Notes:

---

## Case 02: Tình huống lỗi hoặc edge case

...
```

File gợi ý:

```text
docs/ai-logs.md
docs/ai-logs/sample-prompts.md
docs/ai-logs/chat-logs.md
```

**Không nên commit API keys, secrets, token hoặc thông tin nhạy cảm vào log.**

---

## 8. Yêu cầu khi nộp qua Form

Form sẽ được BTC gửi sau. Team cần chuẩn bị sẵn toàn bộ link trước khi form mở.

### 8.1. Các mục cần có trong Form

| STT | Hạng mục | Yêu cầu |
|---|---|---|
| 1 | **Live URL** | Sản phẩm chạy ổn định trên môi trường deploy |
| 2 | **Video Demo** | Video 3–5 phút, thuyết minh bài toán, tính năng chính và luồng xử lý của AI Agent |
| 3 | **Pitch Deck** | 5–10 trang: vấn đề, giải pháp, công nghệ, kết quả |

### 8.2. Convention Live URL

Format gợi ý trong slide:

```text
https://a20-app-xxx.domain
```

Trong đó:

- `xxx` là tên team hoặc mã team.
- Viết thường.
- Không dấu.
- Không khoảng trắng.
- Domain có thể là bất kỳ domain deploy hợp lệ.

Ví dụ hợp lệ:

```text
https://a20-app-049.io.vn
https://a20-app-team01.vercel.app
https://a20-app-abc.onrender.com
```

Ví dụ không nên dùng:

```text
https://A20 App 049.domain
https://a20-app-đội-1.domain
https://localhost:3000
```

---

## 9. Video Demo cần trình bày gì?

Video demo nên dài **3–5 phút**.

### 9.1. Cấu trúc video demo khuyến nghị

| Thời lượng | Nội dung |
|---|---|
| 0:00–0:30 | Giới thiệu tên dự án, team, vấn đề cần giải quyết |
| 0:30–1:00 | Mô tả người dùng mục tiêu và use case chính |
| 1:00–2:30 | Demo các tính năng chính trên Live URL |
| 2:30–3:30 | Giải thích luồng xử lý của AI Agent |
| 3:30–4:30 | Nêu kết quả, điểm nổi bật, evaluation |
| 4:30–5:00 | Kết luận, hạn chế và hướng phát triển |

### 9.2. Checklist video demo

- [ ] Video truy cập được công khai
- [ ] Âm thanh rõ
- [ ] Thuyết minh ngắn gọn
- [ ] Có demo trực tiếp trên Live URL
- [ ] Có nói rõ bài toán
- [ ] Có nói rõ tính năng chính
- [ ] Có giải thích AI Agent xử lý như thế nào
- [ ] Có nêu kết quả hoặc điểm nổi bật
- [ ] Không để lộ secret/API key/token

---

## 10. Pitch Deck cần có gì?

Pitch deck yêu cầu **5–10 trang**.

### 10.1. Cấu trúc pitch deck khuyến nghị

| Slide | Nội dung |
|---|---|
| 1 | Tên dự án, team, tagline |
| 2 | Vấn đề / pain point |
| 3 | Người dùng mục tiêu / use case |
| 4 | Giải pháp của team |
| 5 | Demo flow / product screenshots |
| 6 | Kiến trúc hệ thống / AI Agent flow |
| 7 | Công nghệ sử dụng |
| 8 | Kết quả, metrics, evaluation |
| 9 | Hạn chế, rủi ro, hướng phát triển |
| 10 | Tổng kết và link quan trọng |

### 10.2. Checklist pitch deck

- [ ] 5–10 trang
- [ ] Có problem
- [ ] Có solution
- [ ] Có công nghệ
- [ ] Có kết quả
- [ ] Có hình ảnh/screenshot sản phẩm
- [ ] Có architecture hoặc AI Agent flow
- [ ] Link slide mở quyền public
- [ ] Không quá nhiều chữ
- [ ] Có câu chuyện rõ ràng từ vấn đề đến giải pháp và kết quả

---

## 11. Quyền truy cập link

Slide nhấn mạnh: **Tất cả link Drive, YouTube, Slide cần mở quyền truy cập công khai.**

### 11.1. Checklist quyền truy cập

- [ ] GitHub repository public hoặc cấp quyền đúng theo yêu cầu BTC
- [ ] Live URL không yêu cầu tài khoản nội bộ
- [ ] Video demo public / unlisted nhưng ai có link đều xem được
- [ ] Pitch deck public / anyone with the link can view
- [ ] Tài liệu Drive public / anyone with the link can view
- [ ] Ảnh, PDF, file evidence mở quyền xem
- [ ] Link trong README click được
- [ ] Link trong Form click được

### 11.2. Cách tự kiểm tra link

Trước khi nộp, mở trình duyệt ở chế độ ẩn danh và kiểm tra:

- Có vào được Live URL không?
- Có xem được video không?
- Có mở được slide không?
- Có mở được tài liệu Drive không?
- Có clone hoặc xem được GitHub repo không?
- Có chạy được hướng dẫn trong README không?

---

## 12. Convention khi viết report / README / tài liệu nộp bài

### 12.1. Convention chung

- Viết rõ ràng, ngắn gọn, có cấu trúc.
- Dùng một ngôn ngữ chính xuyên suốt, ưu tiên tiếng Việt rõ nghĩa hoặc song ngữ Việt–Anh nếu team muốn chuyên nghiệp hơn.
- Mỗi tài liệu nên có mục tiêu cụ thể, không viết lan man.
- Ưu tiên bullet points, bảng, sơ đồ, screenshot.
- Link quan trọng đặt ở phần đầu README.
- Mọi hình ảnh nên có caption hoặc mô tả ngắn.
- Nêu rõ giả định, giới hạn và phần chưa hoàn thiện.
- Không che giấu lỗi; nên ghi rõ lỗi đã gặp và cách xử lý.

### 12.2. Convention đặt tên file

Nên dùng:

```text
lowercase-kebab-case.md
```

Ví dụ tốt:

```text
README.md
docs/architecture.md
docs/worklog.md
docs/ai-logs.md
docs/evaluation-report.md
docs/test-cases.md
docs/journal/week-01.md
```

Không nên dùng:

```text
Báo cáo cuối cùng bản mới nhất.md
demo cuối.mp4
file nộp bài FINAL FINAL.pdf
```

### 12.3. Convention thư mục

Cấu trúc repo gợi ý:

```text
.
├── README.md
├── .env.example
├── .gitignore
├── frontend/
├── backend/
├── database/
├── agent/
├── docs/
│   ├── architecture.md
│   ├── architecture.png
│   ├── worklog.md
│   ├── ai-logs.md
│   ├── evaluation-report.md
│   ├── test-cases.md
│   ├── journal/
│   │   ├── week-01.md
│   │   └── week-02.md
│   └── screenshots/
├── scripts/
├── docker-compose.yml
└── deploy/
```

Có thể điều chỉnh theo dự án thực tế, nhưng cần đảm bảo người chấm dễ tìm tài liệu.

### 12.4. Convention viết report evaluation

Evaluation report nên có format:

```md
# Evaluation Report

## 1. Mục tiêu đánh giá
Đánh giá sản phẩm/AI Agent theo các tiêu chí nào?

## 2. Phạm vi đánh giá
Đã test những chức năng nào? Chưa test phần nào?

## 3. Bộ test case
| ID | Tình huống | Input | Expected Output | Actual Output | Kết quả |
|---|---|---|---|---|---|

## 4. Metrics
| Metric | Giá trị | Cách đo |
|---|---|---|

## 5. Kết quả chính
Tóm tắt kết quả tốt nhất và các điểm đã đạt.

## 6. Failure Cases
Các case lỗi, nguyên nhân và hướng xử lý.

## 7. Nhận xét cuối
Sản phẩm có đáp ứng mục tiêu không? Cần cải thiện gì?
```

### 12.5. Convention viết worklog

- Ghi theo ngày hoặc theo sprint.
- Mỗi task có người phụ trách.
- Có trạng thái rõ ràng.
- Có ghi chú nếu bị blocked.
- Không cần quá dài, nhưng phải đủ để thấy quá trình làm việc.

### 12.6. Convention viết AI logs

- Mỗi log nên có input, output, expected behavior và nhận xét.
- Đánh dấu rõ case thành công và case thất bại.
- Không đưa API key, token, user data nhạy cảm vào log.
- Nếu log dài, tách thành nhiều file theo nhóm use case.

### 12.7. Convention screenshot / evidence

- Screenshot nên rõ màn hình, không bị cắt mất nội dung chính.
- Tên file nên có ý nghĩa:

```text
docs/screenshots/login-page.png
docs/screenshots/agent-response-success.png
docs/screenshots/evaluation-case-01.png
```

- Nếu dùng ảnh trong report, nên mô tả ảnh đó chứng minh điều gì.

---

## 13. Checklist file cần nộp / cần có trước deadline

### 13.1. Bắt buộc trong GitHub repo

- [ ] `README.md`
- [ ] Source code frontend
- [ ] Source code backend/API
- [ ] Source code AI Agent/LLM logic
- [ ] Database schema hoặc migration nếu có database
- [ ] File cấu hình cần thiết
- [ ] `.env.example`
- [ ] `.gitignore`
- [ ] Architecture diagram
- [ ] AI logs
- [ ] Worklog
- [ ] Weekly journal
- [ ] Evaluation evidence
- [ ] Hướng dẫn chạy local
- [ ] Hướng dẫn deploy hoặc mô tả môi trường deploy

### 13.2. Cần chuẩn bị để điền Form

- [ ] GitHub repository URL
- [ ] Live URL
- [ ] Video demo URL
- [ ] Pitch deck URL
- [ ] Architecture URL hoặc file trong repo
- [ ] AI logs URL hoặc file trong repo
- [ ] Worklog / journal URL hoặc file trong repo
- [ ] Evaluation evidence URL hoặc file trong repo
- [ ] Thông tin team
- [ ] Mô tả ngắn dự án
- [ ] Danh sách công nghệ sử dụng
- [ ] Ghi chú đặc biệt nếu sản phẩm cần tài khoản demo

### 13.3. Checklist cuối cùng trước khi bấm nộp

- [ ] Tên Repository và Live URL đúng định dạng
- [ ] Source code đã push bản mới nhất lên GitHub
- [ ] Sản phẩm chạy ổn định tại Live URL
- [ ] README.md có đầy đủ link quan trọng ở phần đầu
- [ ] Tất cả link Drive, YouTube, Slide đã mở công khai
- [ ] Video demo xem được bằng cửa sổ ẩn danh
- [ ] Pitch deck xem được bằng cửa sổ ẩn danh
- [ ] Architecture, AI logs, journal, worklog và evidence đã sẵn sàng
- [ ] Không commit `.env`, API keys, secrets, tokens
- [ ] Hướng dẫn cài đặt/chạy dự án đã được test lại
- [ ] Các screenshot minh chứng đủ rõ
- [ ] Form đã điền đúng link, không dán nhầm link private
- [ ] Nộp trước deadline **23:59 ngày 17/05**

---

## 14. Gợi ý mức độ ưu tiên nếu còn ít thời gian

Nếu team không còn nhiều thời gian, nên ưu tiên theo thứ tự:

1. **Live URL chạy ổn định**
2. **GitHub repo có code mới nhất**
3. **README đầy đủ và link rõ ràng**
4. **Video demo 3–5 phút**
5. **Pitch deck 5–10 trang**
6. **Architecture diagram**
7. **AI logs**
8. **Evaluation evidence**
9. **Worklog và weekly journal**

Trong đó, README nên được xem là trung tâm điều hướng: người chấm có thể mở README và đi đến tất cả tài liệu còn lại.

---

## 15. Mẫu Quick Links đặt ở đầu README

```md
## Quick Links

| Hạng mục | Link |
|---|---|
| Live URL | https://... |
| Demo Video | https://... |
| Pitch Deck | https://... |
| Architecture | ./docs/architecture.md |
| AI Logs | ./docs/ai-logs.md |
| Worklog | ./docs/worklog.md |
| Evaluation Report | ./docs/evaluation-report.md |
```

---

## 16. Mẫu submission summary

Có thể đặt trong README hoặc file `docs/submission-summary.md`.

```md
# Submission Summary

## Project
- Tên dự án:
- Team:
- Live URL:
- GitHub Repository:
- Demo Video:
- Pitch Deck:

## Problem
Dự án giải quyết vấn đề gì?

## Solution
Sản phẩm giải quyết vấn đề bằng cách nào?

## AI Component
AI Agent/LLM được dùng ở đâu? Vai trò là gì?

## Tech Stack
- Frontend:
- Backend:
- Database:
- AI/LLM:
- Deployment:

## Evaluation
Team đã test những gì? Kết quả ra sao?

## Notes
Các tài khoản demo, giới hạn hiện tại hoặc lưu ý cho người chấm.
```

---

## 17. Các lỗi dễ bị mất điểm

- Không mở quyền public cho video/slide/Drive.
- Live URL lỗi hoặc chỉ chạy ở localhost.
- README thiếu hướng dẫn chạy.
- Repo lộn xộn, người chấm không biết bắt đầu từ đâu.
- Không có architecture.
- Không có AI logs hoặc minh chứng test AI Agent.
- Không có evaluation evidence.
- Không push code mới nhất.
- Form điền nhầm link.
- Commit nhầm `.env`, API key, token.
- Video demo quá dài, thiếu trọng tâm hoặc không demo được sản phẩm.
- Pitch deck chỉ nói ý tưởng, không có kết quả hoặc minh chứng.

---

## 18. Kết luận

Yêu cầu nộp bài không chỉ là nộp code. Team cần chứng minh được 4 nhóm nội dung:

1. **Sản phẩm chạy được**: có Live URL ổn định.
2. **Kỹ thuật rõ ràng**: repo có source code, README, architecture.
3. **AI có minh chứng**: có AI logs, test cases, evaluation evidence.
4. **Quá trình làm việc minh bạch**: có journal, worklog và tài liệu hỗ trợ.

Cách nộp tốt nhất là dùng `README.md` làm trung tâm, đặt toàn bộ link quan trọng ở đầu file để BTC có thể kiểm tra nhanh.
