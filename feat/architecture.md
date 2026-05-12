# System Architecture

## Feature map

- [Onboarding](./onboarding.md)
- [Assessment](./assessment.md)
- [Learning Path Planner](./learning-path-planner.md)
- [Replan](./replan.md)
- [Agent Tutor](./agent-tutor.md)
- [Guardrails](./guardrails.md)
- [Auth Password Reset](./auth-password-reset.md)
- [Admin Observability](./admin-observability.md)
- [Canonical Runtime Cutover](./canonical-runtime-cutover.md)
- [Deployment ECS](./deployment-ecs.md)

## 1. Tổng quan hệ thống

Liên quan:
- [Canonical Runtime Cutover](./canonical-runtime-cutover.md)
- [Deployment ECS](./deployment-ecs.md)
- [Admin Observability](./admin-observability.md)

```mermaid
flowchart LR
    U[Người dùng] --> FE[Next.js Frontend]
    FE --> API[FastAPI Backend]
    API --> SVC[Service Layer]
    SVC --> PG[(PostgreSQL)]
    SVC --> RD[(Redis)]
    SVC --> ASSET[Course Assets / Data]
    SVC --> LLM[LLM Providers]
```

## 2. Kiến trúc ứng dụng

Liên quan:
- [Canonical Runtime Cutover](./canonical-runtime-cutover.md)
- [Agent Tutor](./agent-tutor.md)
- [Guardrails](./guardrails.md)

```mermaid
flowchart TD
    A[Frontend App Router] --> B[API Routers]
    B --> C[Business Services]
    C --> D[Repositories]
    D --> E[(PostgreSQL)]

    C --> F[(Redis)]
    C --> G[Course Assets]
    C --> H[LLM Integrations]
    C --> I[Observability]
```

## 3. Frontend architecture

Liên quan:
- [Onboarding](./onboarding.md)
- [Learning Path Planner](./learning-path-planner.md)
- [Replan](./replan.md)
- [Agent Tutor](./agent-tutor.md)

```mermaid
flowchart TD
    FE[Frontend]
    FE --> APP[app/ routes]
    FE --> COMP[components/]
    FE --> STORE[Zustand stores]
    FE --> LIB[lib/ API clients + mappers]
    FE --> FEATURE[features/ domain modules]

    APP --> STORE
    APP --> LIB
    APP --> COMP
    APP --> FEATURE
```

## 4. Backend architecture

Liên quan:
- [Assessment](./assessment.md)
- [Canonical Runtime Cutover](./canonical-runtime-cutover.md)
- [Admin Observability](./admin-observability.md)

```mermaid
flowchart TD
    API[FastAPI app]
    API --> ROUTER[Routers]
    ROUTER --> SERVICE[Services]
    SERVICE --> REPO[Repositories]
    REPO --> MODEL[SQLAlchemy Models]
    MODEL --> DB[(PostgreSQL)]

    SERVICE --> REDIS[(Redis)]
    SERVICE --> FILES[Data / Assets]
    SERVICE --> EXT[External Providers]
```

## 5. Dòng dữ liệu học tập thích ứng

Liên quan:
- [Onboarding](./onboarding.md)
- [Assessment](./assessment.md)
- [Learning Path Planner](./learning-path-planner.md)
- [Replan](./replan.md)

```mermaid
flowchart LR
    ONB[Onboarding] --> GP[goal_preferences]
    ASM[Assessment] --> INT[interactions]
    ASM --> MKP[learner_mastery_kp]
    GP --> PLAN[Learning Path Planner]
    MKP --> PLAN
    INT --> PLAN
    PLAN --> PH[plan_history]
    PLAN --> RL[rationale_log]
    PLAN --> PSS[planner_session_state]
    PLAN --> LP[Learning Path UI]
```

## 6. Canonical data model

Liên quan:
- [Canonical Runtime Cutover](./canonical-runtime-cutover.md)
- [Assessment](./assessment.md)
- [Learning Path Planner](./learning-path-planner.md)

```mermaid
flowchart TD
    COURSE[courses] --> SECTION[course_sections]
    SECTION --> UNIT[learning_units]

    CKP[concepts_kp] --> UKM[unit_kp_map]
    UNIT --> UKM

    QB[question_bank] --> IPM[item_phase_map]
    QB --> IKM[item_kp_map]
    QB --> IC[item_calibration]

    IKM --> CKP
    UNIT --> QB

    CKP --> PRE[prerequisite_edges]
```

## 7. Onboarding -> Assessment -> Planner flow

Liên quan:
- [Onboarding](./onboarding.md)
- [Assessment](./assessment.md)
- [Learning Path Planner](./learning-path-planner.md)

```mermaid
sequenceDiagram
    participant User
    participant FE as Frontend
    participant API as Backend API
    participant DB as PostgreSQL

    User->>FE: Hoàn thành onboarding
    FE->>API: PUT /api/users/me/onboarding
    API->>DB: Ghi goal_preferences

    User->>FE: Bắt đầu assessment
    FE->>API: POST /api/assessment/start
    API->>DB: Đọc canonical question set

    User->>FE: Nộp câu trả lời
    FE->>API: POST /api/assessment/{id}/submit
    API->>DB: Ghi interactions + update learner_mastery_kp

    FE->>API: POST /api/learning-path/generate
    API->>DB: Đọc goals + mastery + graph + progress
    API->>DB: Ghi plan_history + rationale_log + planner_session_state
    API-->>FE: Trả learning path
```

## 8. Replan flow

Liên quan:
- [Replan](./replan.md)
- [Assessment](./assessment.md)
- [Learning Path Planner](./learning-path-planner.md)

```mermaid
flowchart TD
    U[User claim kiến thức đã biết] --> RP[/replan]
    RP --> ANA[POST /api/replan/analyze]
    ANA --> KW[Keyword planner]
    KW --> DISC[Current path unit discovery]
    DISC --> PRE[Prerequisite suggestion]
    PRE --> SCOPE[Scope review]
    SCOPE --> START[POST /api/replan/assessment/start]
    START --> ASM[Assessment engine]
    ASM --> MKP[Update mastery]
    MKP --> PLAN[Planner cập nhật path]
```

## 9. Agent Tutor architecture

Liên quan:
- [Agent Tutor](./agent-tutor.md)
- [Guardrails](./guardrails.md)
- [Admin Observability](./admin-observability.md)

```mermaid
flowchart TD
    USER[User] --> AG[/agent hoặc /lectures/ask]
    AG --> ROUTE[Structured Router]
    ROUTE --> POLICY[Policy Guard]
    POLICY --> RAG[Agentic RAG / Tutor Context]
    RAG --> TOOL[Tool execution]
    TOOL --> COMP[Response Composer]
    COMP --> RESP[Grounded response]

    POLICY --> PA[Pending Action]
    PA --> CONFIRM[User confirm/reject]
    CONFIRM --> COMMIT[Commit service]
```

## 10. Guardrails architecture

Liên quan:
- [Guardrails](./guardrails.md)
- [Agent Tutor](./agent-tutor.md)
- [Replan](./replan.md)

```mermaid
flowchart LR
    IN[Input] --> RG[Routing Guard]
    RG --> SG[Scope Guard]
    SG --> EG[Evidence Guard]
    EG --> CG[Confirmation Guard]
    CG --> OF[Output Filter / Fallback]
```

## 11. Observability architecture

Liên quan:
- [Admin Observability](./admin-observability.md)
- [Agent Tutor](./agent-tutor.md)
- [Deployment ECS](./deployment-ecs.md)

```mermaid
flowchart TD
    API[FastAPI App] --> METRICS[/metrics]
    API --> LOGS[AccessLogMiddleware]
    API --> LF[LangFuse Tracing]

    METRICS --> PROM[Prometheus]
    LOGS --> LOKI[Loki / JSON logs]
    LF --> LANGFUSE[LangFuse Cloud]

    PROM --> GRAF[Grafana]
    LOKI --> GRAF
```

## 12. Deployment architecture

Liên quan:
- [Deployment ECS](./deployment-ecs.md)
- [Admin Observability](./admin-observability.md)
- [Canonical Runtime Cutover](./canonical-runtime-cutover.md)

```mermaid
flowchart TB
    Dev[Developer] --> GH[GitHub]
    GH --> CI[GitHub Actions CI]
    GH --> CD[GitHub Actions Deploy]
    CD --> ECR[Amazon ECR]
    ECR --> ECS[ECS Fargate Services]

    User[Browser] --> ALB[Application Load Balancer]
    ALB --> FE[Frontend Service]
    ALB --> BE[Backend Service]

    BE --> RDS[(RDS PostgreSQL)]
    BE --> CACHE[(ElastiCache Redis)]
    BE --> SECRET[Secrets Manager]
    BE --> EXT[LLM / Email Providers]

    CF[CloudFront] --> S3[(Private S3 Assets)]
    User --> CF
```

## 13. Gợi ý dùng trong technical report

Bạn có thể tách file này thành 3 lớp trình bày:

- **Architecture overview**: mục 1, 2, 12
- **Core product intelligence**: mục 5, 6, 7, 8
- **AI and production safety**: mục 9, 10, 11

Nếu cần rút gọn cho slide hoặc report ngắn, nên giữ lại 4 sơ đồ chính:
- Tổng quan hệ thống
- Canonical data model
- Onboarding -> Assessment -> Planner
- Deployment architecture
