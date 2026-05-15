# Evaluation Report - AI Adaptive Learning Platform

> AI20K Submission | Version 1.0  
> Ngay: 2026-05-15

---

## 1. Muc tieu danh gia

Danh gia do tin cay, tinh chinh xac va tinh an toan cua he thong AI Adaptive Learning Platform tren cac khia canh:

- **API Contract**: Dam bao cac route hoat dong dung spec (HTTP status, response schema).
- **Business Logic**: Kiem tra logic nghiep vu cot loi (mastery scoring, learning path).
- **AI Agent Behavior**: Danh gia hanh vi agent qua golden eval dataset — bao gom RAG retrieval, context continuity, hallucination prevention, assessment boundary.
- **Safety & Guardrail**: Danh gia bo loc an toan (guardrail router) voi 13,513 samples bao gom harmful request, jailbreak, prompt injection.
- **Integration/E2E**: Kiem tra luong end-to-end tu request den response.

---

## 2. Pham vi danh gia

| Thanh phan | Mo ta |
|---|---|
| API Routes | Contract tests cho toan bo route chinh (FastAPI) |
| Service Layer | Unit tests cho business logic (mastery, learning path, agent routing) |
| AI Agent | Golden eval dataset — 50+ test cases, 10+ categories |
| Guardrail Router | 13,513 samples — train/val/test split, multi-attack-type coverage |
| Mastery Scoring | 2PL-lite residual scoring voi IRT priors |
| E2E Flows | Integration tests cho cac luong chinh |

---

## 3. Bo test cases

### 3.1 Tong quan

| Category | Count | Type | Location |
|---|---|---|---|
| API Contract | 13+ | Route-level HTTP contract | `tests/contract/` |
| Service Logic | 10+ | Business logic unit tests | `tests/services/` |
| Golden Eval | 50+ | Agent behavior scenarios | `tests/fixtures/agent/golden_eval_cases.json` |
| Guardrail Dataset | 13,513 | Safety/topic classification | Guardrail training pipeline |
| Integration/E2E | 5+ | Full flow tests | `tests/integration/` |

### 3.2 Golden Eval Categories (AI Agent)

| Category | Muc dich | Vi du kiem tra |
|---|---|---|
| `rag_initial_retrieval` | Agent tim va trich dan dung noi dung | Tool call `search_learning_content`, citation co mat |
| `rag_followup_same_topic` | Giai quyet dai tu, duy tri context | Pronoun resolution trong cung topic |
| `source_limited_answer` | Tra loi trung thuc khi evidence han che | Confidence = `partial`, khong hallucinate |
| `contextual_evidence_gap` | Nhan biet thieu evidence thay vi bia | Phai co disclaimer, khong fabricate |
| `new_topic_after_context` | Chuyen topic sach, khong citation bleed | Khong trich dan tu topic cu |
| `thread_memory` | Nho chinh xac lich su hoi thoai | Recall thong tin tu cac turn truoc |
| `scope_current_path_first` | Tim trong learning path hien tai truoc | Search scope uu tien current path |
| `search_refinement` | Thu lai voi query tot hon khi fail | Retry voi refined search query |
| `lexical_trap` | Khong bi lua boi keyword tuong tu | Phan biet dung noi dung du keyword giong |
| `assessment_boundary` | Tu choi ho tro trong assessment | Block response khi context la bai kiem tra |

Moi test case bao gom:
- **Expected behaviors**: tool calls, search queries, citations, answer content
- **Forbidden behaviors**: must-not rules (vd: `must_not_cite`, `must_not_hallucinate`)
- **Confidence levels**: `grounded`, `partial`, `no_source`

### 3.3 Guardrail Router Dataset

| Metric | Gia tri |
|---|---|
| Tong samples | 13,513 |
| Train set | 10,756 |
| Validation set | 1,041 |
| Test set | 1,716 |
| Schema violations | 0 |
| Train/test leakage | 0 |

**Nguon du lieu HARMFUL:**

| Source | So luong |
|---|---|
| WildGuardMix | 1,500 |
| JailBreakV-28K | 900 |
| MultiJail | 700+ |
| Router-injection | 300 |
| Off-topic | 240 |

**Phan loai attack types:**

| Attack Type | Count |
|---|---|
| `harmful_request` | 1,684 |
| `policy_override` | 851 |
| `jailbreak_template` | 416 |
| `multilingual_jailbreak` | 181 |

**Actions:**
- `ALLOW_LESSON_ANSWER` — Cho phep tra loi lien quan bai hoc
- `SOFT_REFUSE_REDIRECT` — Tu choi mem, huong dan lai
- `ASK_CLARIFY` — Yeu cau lam ro cau hoi
- `SAFETY_REFUSE` — Tu choi vi ly do an toan

---

## 4. Metrics

### 4.1 Mastery Scoring

- Mo hinh: **2PL-lite residual scoring** voi IRT priors
- Cong thuc:
  ```
  mastery_lcb = sigmoid((theta_mu - theta_sigma) / sqrt(1 + theta_sigma^2))
  ```
- Staleness: Applied on-read bang cach inflating uncertainty theo thoi gian
- Trang thai: Phase-1 scoring (chua validated production IRT/BKT)

### 4.2 Guardrail Router

- Schema validation: **0 violations** tren toan bo dataset
- Data integrity: **0 train/test leakage**
- Coverage: 4 attack types, 4+ nguon du lieu harmful

### 4.3 Golden Eval

- 50+ test cases bao phu 10+ categories
- Moi case co expected va forbidden behaviors ro rang
- Evaluation: Deterministic dataset check (pattern matching tren tool calls, citations, answer content)

---

## 5. Ket qua chinh

| Hang muc | Ket qua |
|---|---|
| API Contract tests | 13+ tests — kiem tra HTTP status, response schema |
| Service logic tests | 10+ tests — business logic pass |
| Golden eval coverage | 50+ cases, 10+ behavior categories |
| Guardrail dataset quality | 13,513 samples, 0 schema violations, 0 leakage |
| Guardrail attack coverage | 4 attack types (harmful, policy override, jailbreak, multilingual) |
| Mastery scoring | 2PL-lite implemented, staleness decay hoat dong |
| E2E flows | 5+ integration tests |

---

## 6. Failure Cases va cach xu ly

| # | Van de | Nguyen nhan | Cach fix |
|---|---|---|---|
| 1 | Hallucination khi evidence han che | Agent sinh noi dung khong co trong source | Ap dung `evidence_policy` — bat buoc confidence level, cam fabricate |
| 2 | Citation bleed giua cac topic | Chuyen topic nhung van trich dan topic cu | Them topic switching logic — reset citation context khi topic thay doi |
| 3 | Generic loss bi cite nham la YOLO loss | Keyword similarity dan den sai noi dung | Them `must_not_cite` rules trong golden eval, cai thien search relevance |
| 4 | Prompt injection attempts | User co gang override system prompt | Deploy guardrail router + system prompt hardening, test voi 1,684+ harmful samples |

---

## 7. Nhan xet cuoi

### Diem manh

- **Coverage rong**: Test suite bao phu tu API contract, business logic, AI agent behavior den safety guardrail.
- **Golden eval co cau truc**: 50+ cases voi expected/forbidden behaviors ro rang, cho phep regression testing khi thay doi agent logic.
- **Guardrail dataset lon**: 13,513 samples tu nhieu nguon, bao gom ca multilingual jailbreak — dam bao do phu attack surface.
- **Failure cases duoc document va fix**: Moi van de phat hien deu co root cause va giai phap cu the.

### Han che hien tai

- **Route contract tests**: Co issue request hang voi `httpx.ASGITransport` — can fix de chay on dinh trong CI.
- **IRT/BKT calibration**: Chua validated voi real interaction data — mastery scoring dang o phase-1.
- **Golden eval la deterministic check**: Khong phai live model evaluation — chua do duoc actual model accuracy/latency.
- **Chua co quantified metrics**: Accuracy, precision, recall, latency chua duoc do luong chinh thuc.

### Huong tiep theo

1. Fix httpx.ASGITransport hang issue de chay full contract suite trong CI.
2. Thu thap real interaction data de validate IRT/BKT calibration.
3. Them live model evaluation voi quantified accuracy/latency metrics.
4. Mo rong golden eval dataset khi co them behavior categories.

---

> **Ghi chu**: Bao cao nay phan anh trang thai evaluation tai thoi diem submission. Cac metric dinh luong se duoc bo sung khi co du lieu tuong tac thuc te.
