# Feature: Agent Tutor

## Architecture liên quan
- [System Architecture](./architecture.md)
- Mục nên xem: `2. Kiến trúc ứng dụng`, `9. Agent Tutor architecture`, `10. Guardrails architecture`, `11. Observability architecture`

## 1. Mục tiêu
Agent Tutor cung cấp chatbot học tập có grounding theo lecture/course context, hỗ trợ hỏi đáp, giải thích, điều hướng học, và đề xuất action như assessment hoặc replan mà không để model tự ý thay đổi runtime state.

## 2. User/problem this solves
Người học cần:
- hỏi đáp ngay trong lúc học video/bài giảng;
- giải thích khái niệm theo context khóa học đang học;
- hỏi "học tiếp gì", "tại sao planner chọn như vậy", "nên replan không";
- có một interface hỏi đáp thay cho việc tự tìm transcript thủ công.

## 3. System scope
Backend:
- `src/routers/agent.py`
- `src/services/agent_graph_service.py`
- `src/services/agentic_rag_pipeline.py`
- `src/services/agent_tool_nodes.py`
- `src/services/agent_response_composer.py`
- `src/services/llm_service.py`
- `src/prompts/agent/agentic_rag.yaml`

Frontend:
- `frontend/app/agent/page.tsx`
- `frontend/features/agent/components/AgentChatPage.tsx`
- `frontend/app/tutor/page.tsx`
- `frontend/components/learn/InContextTutor.tsx`

Tables/runtime state:
- `agent_conversations`
- `agent_graph_runs`
- `agent_pending_actions`
- `qa_history`
- lecture store tables

## 4. Architecture & flow
Repo hiện có hai bề mặt liên quan:
1. lecture AI tutor cho hỏi đáp ngay trong lecture context;
2. path agent cho hỏi đáp/routing/action theo course path.

Luồng agent chính:

```text
Frontend /agent
  -> POST /api/agent/chat
  -> auth + resolve scope
  -> AgentGraphService.chat(...)
  -> route_intent
  -> slot canonicalization
  -> policy guard
  -> agentic_rag / tool dispatch
  -> nếu cần side effect -> pending action
  -> AgentResponseComposer
  -> persist response
```

Luồng lecture tutor:

```text
/api/lectures/ask
  -> verify lecture/context
  -> build tutor prompt + guardrails
  -> stream LangGraph/LangChain response
  -> persist qa_history
  -> optional rating -> LangFuse score
```

## 5. Key components
- `AgentGraphService`: orchestration và thread/run lifecycle.
- `StructuredAgentRouter`: intent + slot extraction theo structured output.
- `AgenticRAGPipeline`: thinking/acting/observing/responding với evidence guard.
- `AgentResponseComposer`: strip hidden stage text, enforce citation contract.
- `llm_service`: lecture-grounded tutor path.
- `agent_pending_action_decision` + commit service: approve/reject action an toàn.

## 6. Data model / contracts
Agent response contract gồm:
- `answer.markdown`
- `answer.confidence`
- `citations`
- `actions`
- `warning`
- `fallback`
- `trace`

Lecture tutor lưu:
- `qa_history`
- `langfuse_trace_id`
- `langfuse_observation_id`

Agent không được tự write planner/mastery/assessment bằng free-form text; mọi side effect phải đi qua typed pending action.

## 7. Technical decisions
- Dùng structured routing thay vì keyword matching làm source of truth.
- Tiếp cận "tool output là authoritative", model không được sửa evidence/citation.
- Side effects đi qua interrupt/resume + idempotency thay vì chat command thuần text.
- Tách lecture tutor và path agent nhưng dùng chung observability và guardrail philosophy.

## 8. Risks / trade-offs
- Hệ thống agent tăng độ phức tạp runtime: thread lock, retry, pending action, checkpoint.
- Chat quality phụ thuộc vào retrieval scope và content hygiene.
- Dễ route sai giữa `request_replan` và `explain_concept` nếu lexical overlap không được kiểm soát.
- Agent dễ gặp issue concurrency và persisted response consistency hơn chatbot stateless.

## 9. Testing / validation
Backend:
- `tests/test_agent_routes.py`
- `tests/services/test_agent_graph_service.py`
- `tests/services/test_agent_graph_router.py`
- `tests/services/test_agent_routing_eval.py`
- `tests/services/test_agentic_rag_pipeline.py`
- `tests/test_lecture_routes.py`

Frontend:
- `frontend/tests/routes/agent/page.test.tsx`
- `frontend/tests/unit/tutor/in-context-tutor.test.tsx`

Ops:
- `docs/agent-ops-runbook.md`

## 10. Demo-worthy points
- Có thể present đây như một "productionized educational agent", không phải chatbot demo.
- Có grounding, policy, pending actions, traceability, và interrupt-safe state.
- Rất mạnh để đưa vào technical report vì nó kết hợp AI engineering, backend reliability, và UX flow.
