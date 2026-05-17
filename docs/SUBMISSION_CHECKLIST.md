# AI20K Final Submission Checklist

> **Deadline: 23:59 ngày 17/05/2026**  
> Updated: 2026-05-15  
> Status: đang hoàn thiện — còn 2 ngày

---

## TỔNG QUAN TIẾN ĐỘ

| Kênh | Status | Ghi chú |
|---|---|---|
| **GitHub Repository** | ✅ Sẵn sàng | Code, docs, architecture đầy đủ |
| **Form nộp bài** | ✅ Sẵn sàng điền | Live URL, video demo và pitch deck đã có link/file |
| **Live URL** | ✅ Online | https://a20-app-049.io.vn |

---

## 1. GITHUB REPOSITORY

### 1.1 Source Code

| Hạng mục | Status | File/Path |
|---|---|---|
| Frontend (Next.js 14) | ✅ Done | `frontend/` |
| Backend (FastAPI) | ✅ Done | `src/` |
| Database migrations | ✅ Done | `alembic/` |
| AI Agent (LangGraph) | ✅ Done | `src/api/services/llm_service/` |
| Fine-tuned models (Guardrail, Tutor) | ✅ Done | `guardrails/` + DVC tracked |
| Docker Compose (local) | ✅ Done | `docker-compose.yml` |
| Docker Compose (prod) | ✅ Done | `docker-compose.prod.yml` |
| Dockerfile | ✅ Done | `Dockerfile` |
| CI/CD workflows | ✅ Done | `.github/workflows/` |
| Terraform IaC | ✅ Done | `deploy-ecs/` |
| `.env.example` (không commit secret) | ✅ Done | `.env.example` |
| `requirements.txt` / `pyproject.toml` | ✅ Done | gốc project |

### 1.2 README.md

| Hạng mục | Status | Ghi chú |
|---|---|---|
| Tên dự án | ✅ Done | |
| Mô tả ngắn gọn | ✅ Done | |
| Vấn đề cần giải quyết | ✅ Done | Section 2 |
| Tính năng chính | ✅ Done | Section 4 |
| Fine-tuned models | ✅ Done | Section 4.1 |
| Kiến trúc hệ thống | ✅ Done | Section 5 + SVGs |
| Công nghệ sử dụng | ✅ Done | Section 6 |
| Hướng dẫn cài đặt local | ✅ Done | Section 7 |
| Biến môi trường | ✅ Done | Section 8 |
| Cách sử dụng | ✅ Done | Section 9 |
| Demo & kết quả | ✅ Done | Section 10 |
| Evaluation | ✅ Done | Section 11 |
| Team & phân công | ✅ Done | Section 12 |
| Hạn chế & hướng phát triển | ✅ Done | Section 13 |
| **Live URL** | ✅ `https://a20-app-049.io.vn` | |
| **Demo Video** | ✅ YouTube | `https://www.youtube.com/watch?v=9YLKDFpAEio` |
| **Pitch Deck** | ✅ Google Drive | `https://drive.google.com/file/d/1YH_QWxxfRwtMAHUphpxTCodZoHOY0QJ7/view?usp=drive_link` |
| Link architecture | ✅ Done | `ARCHITECTURE.pdf`, `architecture/01-system-overview.svg`, `architecture/02-agentic-rag-pipeline.svg`, `docs/architecture.md` |
| Link AI Logs | ✅ Done | `docs/ai-logs.md` |
| Link evaluation | ✅ Done | `docs/evaluation-report.md` |

### 1.3 Architecture

| Hạng mục | Status | File |
|---|---|---|
| Sơ đồ tổng quan hệ thống | ✅ Done | `architecture/01-system-overview.svg` |
| Architecture PDF nộp bài | ✅ Done | `ARCHITECTURE.pdf` |
| Agentic RAG Pipeline | ✅ Done | `architecture/02-agentic-rag-pipeline.svg` |
| AWS Infrastructure | ✅ Done | `architecture/03-aws-infrastructure.drawio` |
| Request Lifecycle | ✅ Done | `architecture/04-request-lifecycle.drawio` |
| Data Schema | ✅ Done | `architecture/05-data-schema.drawio` |
| UX / Assessment / Data flywheel diagrams | ✅ Done | `architecture/06-onboarding-assesment.svg`, `architecture/07-ai-tutor.svg`, `architecture/08-data-flywheel.svg` |
| Luồng dữ liệu chính | ✅ Done | `docs/architecture.md` |
| Vị trí AI Agent trong hệ thống | ✅ Done | RAG pipeline diagram |
| Deployment diagram | ✅ Done | AWS infra HTML + drawio |

### 1.4 AI Logs

| Hạng mục | Status | File |
|---|---|---|
| Prompt mẫu (System Prompt) | ✅ Done | `docs/ai-logs.md` §2 |
| Chat logs input/output mẫu | ✅ Done | `docs/ai-logs.md` §3 |
| Success cases | ✅ Done | `docs/ai-logs.md` §4 |
| Failure cases | ✅ Done | `docs/ai-logs.md` §5 |
| Quá trình cải tiến prompt | ✅ Done | `docs/ai-logs.md` §6 |
| Guardrail Router logs | ✅ Done | `docs/ai-logs.md` §7 |
| Evaluation summary | ✅ Done | `docs/ai-logs.md` §8 |

### 1.5 Evaluation Evidence

| Hạng mục | Status | File |
|---|---|---|
| Evaluation report | ✅ Done | `docs/evaluation-report.md` |
| Test cases (API contract, service, agent) | ✅ Done | `tests/` |
| Golden eval dataset (50+ cases) | ✅ Done | `tests/fixtures/agent/golden_eval_cases.json` |
| Guardrail dataset (13,513 samples) | ✅ Done | `guardrails/` |
| Agent eval runbook | ✅ Done | `docs/agent-golden-evals.md` |

### 1.6 Nhật ký / Worklog

| Hạng mục | Status | File |
|---|---|---|
| Weekly Journal (tuần 1–4) | ✅ Done | `docs/JOURNAL.md` |
| **Weekly Journal (tuần 5–6 cần bổ sung)** | ⚠️ Thiếu | `docs/JOURNAL.md` |
| Worklog / ADR | ✅ Done | `docs/WORKLOG.md` |
| Changelog | ✅ Done | `CHANGELOG.md` |

---

## 2. FORM NỘP BÀI

| Hạng mục | Status | Ghi chú |
|---|---|---|
| **Live URL** | ✅ Ready | `https://a20-app-049.io.vn` |
| **Video Demo (3–5 phút)** | ✅ Ready | YouTube link đã cập nhật trong README |
| **Pitch Deck (5–10 trang)** | ✅ Ready | Google Drive link đã cập nhật trong README |

---

## 3. QUYỀN TRUY CẬP

| Hạng mục | Status | Action |
|---|---|---|
| GitHub repo public | ✅ Confirm | kiểm tra Settings → Visibility |
| Live URL không yêu cầu auth nội bộ | ✅ Check | test incognito trên `a20-app-049.io.vn` |
| Video demo (public/unlisted) | ✅ Reachable | YouTube link trả HTTP 200 |
| Pitch deck (anyone with link) | ✅ Google Drive | `https://drive.google.com/file/d/1YH_QWxxfRwtMAHUphpxTCodZoHOY0QJ7/view?usp=drive_link` |
| Tất cả link trong README click được | ✅ Verified | README link audit: external HTTP 200, local paths exist |

---

## 4. SELF-TEST TRƯỚC KHI NỘP

Dùng **trình duyệt ẩn danh** để kiểm tra:

- [ ] `https://a20-app-049.io.vn` — load được không?
- [ ] Đăng ký tài khoản mới → onboarding → học thử → quiz → AI Tutor
- [x] Video demo → xem được không?
- [x] Pitch deck → mở được không?
- [ ] GitHub repo → clone + README rõ không?
- [x] Tất cả link trong README hoạt động

---

## 5. ƯU TIÊN CÒN LẠI (theo thứ tự)

| Priority | Việc cần làm | Deadline |
|---|---|---|
| ✅ Done | Video demo 3–5 phút (live demo trên `a20-app-049.io.vn`) | Done |
| ✅ Done | Pitch Deck 5–10 trang | Done |
| ✅ Done | Cập nhật README: thêm link Video + Pitch Deck | Done |
| ✅ Done | Bổ sung Journal tuần 5–10 | Done |
| 🟡 P1 | Verify Live URL: smoke test toàn bộ flow chính | 16/05 |
| 🟢 P2 | Self-test toàn bộ link bằng incognito | 17/05 sáng |
| 🟢 P2 | Nộp Form chính thức | 17/05 trước 23:59 |

---

## 6. CẤU TRÚC FILE NỘP ĐỦ

```
A20-App-049/
├── README.md                         ✅ (đã có Video + Pitch link)
├── AGENTS.md                         ✅
├── ARCHITECTURE.pdf                  ✅
├── CHANGELOG.md                      ✅
├── Dockerfile                        ✅
├── docker-compose.yml                ✅
├── docker-compose.prod.yml           ✅
├── pyproject.toml / requirements.txt ✅
├── .env.example                      ✅ (không commit .env thật)
├── architecture/
│   ├── 01-system-overview.svg        ✅
│   ├── 01-system-overview.drawio     ✅
│   ├── 02-agentic-rag-pipeline.svg   ✅
│   ├── 02-agentic-rag-pipeline.drawio ✅
│   ├── 03-aws-infrastructure.drawio  ✅
│   ├── 04-request-lifecycle.drawio   ✅
│   ├── 05-data-schema.drawio         ✅
│   ├── 06-onboarding-assesment.svg   ✅
│   ├── 07-ai-tutor.svg               ✅
│   └── 08-data-flywheel.svg          ✅
├── docs/
│   ├── architecture.md               ✅
│   ├── ai-logs.md                    ✅
│   ├── evaluation-report.md          ✅
│   ├── JOURNAL.md                    ⚠️ cần thêm tuần 5–6
│   ├── WORKLOG.md                    ✅
│   └── SUBMISSION_CHECKLIST.md       ✅ (file này)
├── src/                              ✅ FastAPI backend
├── frontend/                         ✅ Next.js
├── alembic/                          ✅ DB migrations
├── guardrails/                       ✅ Safety router
├── tests/                            ✅ pytest + golden eval
├── notebooks/                        ✅ training notebooks
├── deploy-ecs/                       ✅ Terraform
└── .github/workflows/                ✅ CI/CD
```

---

## 7. VIDEO DEMO — SCRIPT GỢI Ý

**Thời lượng mục tiêu: 4 phút**

| Thời điểm | Nội dung |
|---|---|
| 0:00–0:20 | Giới thiệu: AI Adaptive Learning Platform, team A20-App-049 |
| 0:20–0:50 | Vấn đề: học sinh tự học không có lộ trình → giải pháp: adaptive loop |
| 0:50–1:30 | Demo: Đăng ký → Onboarding Assessment → nhận Learning Path |
| 1:30–2:30 | Demo: Vào học bài → Video player → Quiz → AI Tutor 24/7 |
| 2:30–3:10 | Demo: AI Tutor giải toán (Python Sandbox) → Guardrail chặn off-topic |
| 3:10–3:40 | Architecture: Pipeline từ User → Guardrail → Smart Router → ReAct Agent |
| 3:40–4:00 | Kết quả: metrics, fine-tuned models, hạn chế và hướng phát triển |

**Điểm nhấn cần thể hiện trong video:**
- AI Tutor xử lý bài toán phức tạp (Python Sandbox tool)
- Guardrail Router chặn jailbreak / off-topic
- Adaptive Learning Path cập nhật theo mastery KP
- System đang chạy production trên AWS ECS Fargate

---

## 8. PITCH DECK — OUTLINE GỢI Ý

**10 trang:**

| Slide | Nội dung |
|---|---|
| 1 | Tên: AI Adaptive Learning Platform · Team A20-App-049 · tagline |
| 2 | Vấn đề: 80% học sinh tự học không có lộ trình · pain points |
| 3 | Người dùng: học sinh cấp 2–ĐH · use case AI Tutor + Adaptive Path |
| 4 | Giải pháp: Adaptive Learning Loop (Assess → Plan → Learn → Update) |
| 5 | Product screenshots: Dashboard, Learning Path, AI Tutor chat |
| 6 | AI Architecture: Guardrail → Smart Router → LangGraph → vLLM |
| 7 | Fine-tuned models: Qwen3.5-0.8B Guardrail + Qwen3.5-4B Tutor |
| 8 | Tech stack: Next.js · FastAPI · PostgreSQL · LangGraph · AWS ECS |
| 9 | Kết quả: valid_json=1.0, harmful_allow=0.0, 50+ golden evals |
| 10 | Hạn chế · Hướng phát triển · Links quan trọng |
