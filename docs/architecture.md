# Kiến trúc hệ thống - AI Adaptive Learning Platform

## 1. Tổng quan hệ thống (System Overview)

```mermaid
flowchart TB
    subgraph Client["Client Layer"]
        User["Learner / Admin"]
        FE["Next.js 14 App Router<br/>React 18 · TypeScript 5<br/>Zustand · Tailwind CSS"]
    end

    subgraph Backend["Backend Layer"]
        API["FastAPI Routers<br/>Python 3.12 · Pydantic v2"]
        SVC["Service Layer"]
        subgraph Services["Core Services"]
            CS["content_service"]
            QS["quiz_service<br/>assessment_service<br/>module_test_service"]
            MS["canonical_mastery_service"]
            RE["recommendation_engine"]
            HS["history_service"]
            LS["llm_service"]
        end
    end

    subgraph Data["Data Layer"]
        PG["PostgreSQL 16"]
        RD["Redis 7"]
    end

    subgraph AI["AI Agent Layer"]
        SR["Smart Router<br/>BLOCKED / SIMPLE / COMPLEX"]
        GR["Guardrail Router<br/>safety · topic · action"]
        RA["LangGraph ReAct Agent<br/>Tool-calling"]
        FM["Fast Model"]
        PS["Python Sandbox Tool"]
        PII["PII Sanitizer"]
    end

    subgraph External["External Services"]
        LLM["LLM Providers<br/>Gemini · OpenAI · Anthropic"]
        LF["Langfuse Tracing"]
        OBS["Prometheus · Grafana · Loki"]
    end

    subgraph Deploy["Deployment"]
        ECS["AWS ECS / Fargate"]
        TF["Terraform"]
        GHA["GitHub Actions<br/>EC2 Runner"]
    end

    User -->|HTTPS| FE
    FE -->|Axios REST| API
    API --> SVC
    SVC --> Services
    CS & QS & MS & RE & HS --> PG
    CS & QS & RE --> RD
    LS --> SR
    SR -->|BLOCKED| SR
    SR -->|SIMPLE| FM
    SR -->|COMPLEX| RA
    RA --> PS
    FM & RA --> LLM
    LS --> GR
    LS --> PII
    LS --> LF
    API --> OBS
    Deploy -.->|infra| Backend
```

## 2. Luồng dữ liệu (Data Flow)

```
User → Frontend → Backend/API → Service Layer → Database + Redis
                                      ↕
                               AI Agent / LLM
```

**Luồng chi tiết:**

1. **User** truy cập hệ thống qua trình duyệt web.
2. **Next.js Frontend** render giao dien, gửi request qua Axios tới FastAPI backend.
3. **FastAPI Routers** nhận request, validate bằng Pydantic v2, chuyển tới service layer tương ứng.
4. **Service Layer** xử lý business logic:
   - `content_service` → truy vấn nội dung khóa học (course sections, learning units).
   - `quiz_service` / `assessment_service` → chọn câu hỏi từ Question Bank theo canonical design.
   - `canonical_mastery_service` → cập nhật mastery score (2PL-lite residual with IRT priors) theo Knowledge Point.
   - `recommendation_engine` → sinh learning plan, ghi audit log.
   - `history_service` → ghi nhận interaction history.
5. **llm_service** nhận yêu cầu AI tutor:
   - PII Sanitizer lọc thông tin nhạy cảm trên input/output.
   - Guardrail Router phân loại safety, topic, action (13,513 training samples).
   - Smart Router phân loại intent → BLOCKED (từ chối) / SIMPLE (fast model) / COMPLEX (ReAct Agent).
   - ReAct Agent sử dụng tool-calling (Python Sandbox) để giải bài tập phức tạp.
   - Langfuse tracing ghi nhận toàn bộ AI flow.
6. **PostgreSQL** lưu trữ dữ liệu chính, **Redis** cache session và dữ liệu hot.
7. **Observability stack** (Prometheus, Grafana, Loki) thu thập metrics và logs.

## 3. Kiến trúc AI Agent

```mermaid
flowchart LR
    Input["User Message"]
    PII_IN["PII Sanitizer<br/>(input)"]
    GR["Guardrail Router<br/>safety_label<br/>topic_label<br/>action"]
    SR["Smart Router"]

    subgraph Paths["Processing Paths"]
        BLOCKED["BLOCKED<br/>→ Reject"]
        SIMPLE["SIMPLE<br/>→ Fast Model"]
        COMPLEX["COMPLEX<br/>→ ReAct Agent"]
    end

    RA["LangGraph ReAct Agent"]
    TOOLS["Tools:<br/>Python Sandbox<br/>Lecture Context Retrieval"]
    LLM["LLM Provider<br/>Gemini / OpenAI / Anthropic"]
    PII_OUT["PII Sanitizer<br/>(output)"]
    TRACE["Langfuse Tracing"]
    Output["Response"]

    Input --> PII_IN --> GR --> SR
    SR --> BLOCKED
    SR --> SIMPLE --> LLM
    SR --> COMPLEX --> RA
    RA <--> TOOLS
    RA <--> LLM
    SIMPLE --> PII_OUT
    RA --> PII_OUT
    PII_OUT --> Output
    GR -.-> TRACE
    SR -.-> TRACE
    RA -.-> TRACE
```

**Nguyên tắc AI Tutor:**
- Chỉ trả lời dựa trên lecture context (lecture-grounded).
- Không tiết lộ system instructions.
- Mọi flow được trace qua Langfuse.

## 4. Database Schema Overview

### Product Shell
| Table | Mô tả |
|---|---|
| `courses` | Thông tin khóa học |
| `course_sections` | Phân chia section trong khóa học |
| `learning_units` | Đơn vị học tập |
| `course_assets` | Tài liệu đính kèm |

### Canonical Content
| Table | Mô tả |
|---|---|
| `concepts_kp` | Knowledge Points - trục năng lực |
| `units` | Canonical units tái sử dụng |
| `unit_kp_map` | Mapping unit ↔ KP |
| `question_bank` | Ngân hàng câu hỏi (runtime asset) |
| `item_calibration` | Thông số IRT của câu hỏi |
| `prerequisite_edges` | Quan hệ tiên quyết giữa KP |

### Learner State
| Table | Mô tả |
|---|---|
| `learner_mastery_kp` | Mastery score theo KP (2PL-lite) |
| `learning_progress_records` | Tiến trình học tập |
| `completed_units` | Đơn vị đã hoàn thành |
| `waived_units` | Đơn vị được miễn |

### Planner Audit
| Table | Mô tả |
|---|---|
| `plan_history` | Lịch sử learning plan |
| `rationale_log` | Lý do quyết định của planner |
| `planner_session_state` | Trạng thái session planner |

### Tutor Store
| Table | Mô tả |
|---|---|
| `lectures` | Bài giảng |
| `chapters` | Chương |
| `transcript_lines` | Nội dung transcript |
| `qa_history` | Lịch sử hỏi đáp AI tutor |

**Thiết kế canonical-first:** Units được tái sử dụng across paths, assessments, quiz, player, agent. Knowledge Point là trục năng lực chung. Data pipeline: raw artifacts → JSONL → import → PostgreSQL.

## 5. Deployment Architecture

```
┌─────────────────────────────────────────────┐
│  AWS Cloud                                  │
│  ┌──────────────┐   ┌──────────────┐        │
│  │ ECS/Fargate  │   │ ECS/Fargate  │        │
│  │  Frontend    │   │  Backend     │        │
│  │  (Next.js)   │   │  (FastAPI)   │        │
│  └──────┬───────┘   └──────┬───────┘        │
│         │                  │                │
│  ┌──────┴──────────────────┴───────┐        │
│  │     PostgreSQL 16 · Redis 7     │        │
│  └─────────────────────────────────┘        │
│                                             │
│  ┌─────────────────────────────────┐        │
│  │  Observability                  │        │
│  │  Prometheus · Grafana · Loki    │        │
│  │  Langfuse                       │        │
│  └─────────────────────────────────┘        │
└─────────────────────────────────────────────┘

CI/CD: GitHub Actions (EC2 Runner) → Docker Build → ECS Deploy
IaC:   Terraform quản lý toàn bộ infrastructure
Local: Docker Compose cho development environment
```

**Chi tiết:**
- **Local dev:** Docker Compose chạy toàn bộ stack (frontend, backend, PostgreSQL, Redis).
- **Production:** AWS ECS/Fargate, auto-scaling, managed containers.
- **Infrastructure as Code:** Terraform quản lý VPC, ECS clusters, RDS, ElastiCache.
- **CI/CD:** GitHub Actions trên EC2 self-hosted runner, build Docker images, deploy lên ECS.
- **Observability:** Prometheus thu thập metrics, Grafana dashboard, Loki aggregates logs, Langfuse trace AI flows.

## 6. Tài liệu tham khảo

- [System Architecture Diagram](./page_architecture_overview.png) - Sơ đồ tổng quan hệ thống
- [AWS ECS Deployment Architecture](./aws-ecs-current-architecture-presentable.drawio) - Kiến trúc deployment trên AWS ECS
