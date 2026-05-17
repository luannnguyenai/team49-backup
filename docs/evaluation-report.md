# Evaluation Report - AI Adaptive Learning Platform

> AI20K Submission | Version 1.0  
> Ngày: 2026-05-15

---

## 1. Mục tiêu đánh giá

Đánh giá độ tin cậy, tính chính xác và tính an toàn của hệ thống AI Adaptive Learning Platform trên các khía cạnh:

- **API Contract**: Đảm bảo các route hoạt động đúng spec (HTTP status, response schema).
- **Business Logic**: Kiểm tra logic nghiệp vụ cốt lõi (mastery scoring, learning path).
- **AI Agent Behavior**: Đánh giá hành vi agent qua golden eval dataset — bao gồm RAG retrieval, context continuity, hallucination prevention, assessment boundary.
- **Safety & Guardrail**: Đánh giá bộ lọc an toàn (guardrail router) với 13,513 samples bao gồm harmful request, jailbreak, prompt injection.
- **Integration/E2E**: Kiểm tra luồng end-to-end từ request đến response.

---

## 2. Phạm vi đánh giá

| Thành phần | Mô tả |
|---|---|
| API Routes | Contract tests cho toàn bộ route chính (FastAPI) |
| Service Layer | Unit tests cho business logic (mastery, learning path, agent routing) |
| AI Agent | Golden eval dataset — 50+ test cases, 10+ categories |
| Guardrail Router | 13,513 samples — train/val/test split, multi-attack-type coverage |
| Mastery Scoring | 2PL-lite residual scoring với IRT priors |
| E2E Flows | Integration tests cho các luồng chính |

---

## 3. Bộ test cases

### 3.1 Tổng quan

| Category | Count | Type | Location |
|---|---|---|---|
| API Contract | 13+ | Route-level HTTP contract | `tests/contract/` |
| Service Logic | 10+ | Business logic unit tests | `tests/services/` |
| Golden Eval | 50+ | Agent behavior scenarios | `tests/fixtures/agent/golden_eval_cases.json` |
| Guardrail Dataset | 13,513 | Safety/topic classification | Guardrail training pipeline |
| Integration/E2E | 5+ | Full flow tests | `tests/integration/` |

### 3.2 Golden Eval Categories (AI Agent)

| Category | Mục đích | Ví dụ kiểm tra |
|---|---|---|
| `rag_initial_retrieval` | Agent tìm và trích dẫn đúng nội dung | Tool call `search_learning_content`, citation có mặt |
| `rag_followup_same_topic` | Giải quyết đại từ, duy trì context | Pronoun resolution trong cùng topic |
| `source_limited_answer` | Trả lời trung thực khi evidence hạn chế | Confidence = `partial`, không hallucinate |
| `contextual_evidence_gap` | Nhận biết thiếu evidence thay vì bịa | Phải có disclaimer, không fabricate |
| `new_topic_after_context` | Chuyển topic sạch, không citation bleed | Không trích dẫn từ topic cũ |
| `thread_memory` | Nhớ chính xác lịch sử hội thoại | Recall thông tin từ các turn trước |
| `scope_current_path_first` | Tìm trong learning path hiện tại trước | Search scope ưu tiên current path |
| `search_refinement` | Thử lại với query tốt hơn khi fail | Retry với refined search query |
| `lexical_trap` | Không bị lừa bởi keyword tương tự | Phân biệt đúng nội dung dù keyword giống |
| `assessment_boundary` | Từ chối hỗ trợ trong assessment | Block response khi context là bài kiểm tra |

Mỗi test case bao gồm:
- **Expected behaviors**: tool calls, search queries, citations, answer content
- **Forbidden behaviors**: must-not rules (ví dụ: `must_not_cite`, `must_not_hallucinate`)
- **Confidence levels**: `grounded`, `partial`, `no_source`

### 3.3 Guardrail Router Dataset

| Metric | Giá trị |
|---|---|
| Tổng samples | 13,513 |
| Train set | 10,756 |
| Validation set | 1,041 |
| Test set | 1,716 |
| Schema violations | 0 |
| Train/test leakage | 0 |

**Nguồn dữ liệu HARMFUL:**

| Source | Số lượng |
|---|---|
| WildGuardMix | 1,500 |
| JailBreakV-28K | 900 |
| MultiJail | 700+ |
| Router-injection | 300 |
| Off-topic | 240 |

**Phân loại attack types:**

| Attack Type | Count |
|---|---|
| `harmful_request` | 1,684 |
| `policy_override` | 851 |
| `jailbreak_template` | 416 |
| `multilingual_jailbreak` | 181 |

**Actions:**
- `ALLOW_LESSON_ANSWER` — Cho phép trả lời liên quan bài học
- `SOFT_REFUSE_REDIRECT` — Từ chối mềm, hướng dẫn lại
- `ASK_CLARIFY` — Yêu cầu làm rõ câu hỏi
- `SAFETY_REFUSE` — Từ chối vì lý do an toàn

---

## 4. Metrics

### 4.1 Mastery Scoring

- Mô hình: **2PL-lite residual scoring** với IRT priors
- Công thức:
  ```
  mastery_lcb = sigmoid((theta_mu - theta_sigma) / sqrt(1 + theta_sigma^2))
  ```
- Staleness: Applied on-read bằng cách inflating uncertainty theo thời gian
- Trạng thái: Phase-1 scoring (chưa validated production IRT/BKT)

### 4.2 Guardrail Router

- Schema validation: **0 violations** trên toàn bộ dataset
- Data integrity: **0 train/test leakage**
- Coverage: 4 attack types, 4+ nguồn dữ liệu harmful

### 4.3 Golden Eval

- 50+ test cases bao phủ 10+ categories
- Mỗi case có expected và forbidden behaviors rõ ràng
- Evaluation: Deterministic dataset check (pattern matching trên tool calls, citations, answer content)

---

## 5. Kết quả chính

| Hạng mục | Kết quả |
|---|---|
| API Contract tests | 13+ tests — kiểm tra HTTP status, response schema |
| Service logic tests | 10+ tests — business logic pass |
| Golden eval coverage | 50+ cases, 10+ behavior categories |
| Guardrail dataset quality | 13,513 samples, 0 schema violations, 0 leakage |
| Guardrail attack coverage | 4 attack types (harmful, policy override, jailbreak, multilingual) |
| Mastery scoring | 2PL-lite implemented, staleness decay hoạt động |
| E2E flows | 5+ integration tests |

---

## 6. Failure Cases và cách xử lý

| # | Vấn đề | Nguyên nhân | Cách fix |
|---|---|---|---|
| 1 | Hallucination khi evidence hạn chế | Agent sinh nội dung không có trong source | Áp dụng `evidence_policy` — bắt buộc confidence level, cấm fabricate |
| 2 | Citation bleed giữa các topic | Chuyển topic nhưng vẫn trích dẫn topic cũ | Thêm topic switching logic — reset citation context khi topic thay đổi |
| 3 | Generic loss bị cite nhầm là YOLO loss | Keyword similarity dẫn đến sai nội dung | Thêm `must_not_cite` rules trong golden eval, cải thiện search relevance |
| 4 | Prompt injection attempts | User cố gắng override system prompt | Deploy guardrail router + system prompt hardening, test với 1,684+ harmful samples |

---

## 7. Nhận xét cuối

### Điểm mạnh

- **Coverage rộng**: Test suite bao phủ từ API contract, business logic, AI agent behavior đến safety guardrail.
- **Golden eval có cấu trúc**: 50+ cases với expected/forbidden behaviors rõ ràng, cho phép regression testing khi thay đổi agent logic.
- **Guardrail dataset lớn**: 13,513 samples từ nhiều nguồn, bao gồm cả multilingual jailbreak — đảm bảo độ phủ attack surface.
- **Failure cases được document và fix**: Mỗi vấn đề phát hiện đều có root cause và giải pháp cụ thể.

### Hạn chế hiện tại

- **Route contract tests**: Có issue request hang với `httpx.ASGITransport` — cần fix để chạy ổn định trong CI.
- **IRT/BKT calibration**: Chưa validated với real interaction data — mastery scoring đang ở phase-1.
- **Golden eval là deterministic check**: Không phải live model evaluation — chưa đo được actual model accuracy/latency.
- **Chưa có quantified metrics**: Accuracy, precision, recall, latency chưa được đo lường chính thức.

### Hướng tiếp theo

1. Fix httpx.ASGITransport hang issue để chạy full contract suite trong CI.
2. Thu thập real interaction data để validate IRT/BKT calibration.
3. Thêm live model evaluation với quantified accuracy/latency metrics.
4. Mở rộng golden eval dataset khi có thêm behavior categories.

---

> **Ghi chú**: Báo cáo này phản ánh trạng thái evaluation tại thời điểm submission. Các metric định lượng sẽ được bổ sung khi có dữ liệu tương tác thực tế.
