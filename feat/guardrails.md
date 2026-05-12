# Feature: Guardrails

## Architecture liên quan
- [System Architecture](./architecture.md)
- Mục nên xem: `2. Kiến trúc ứng dụng`, `9. Agent Tutor architecture`, `10. Guardrails architecture`

## 1. Mục tiêu
Guardrails bảo vệ các bề mặt AI của hệ thống để model không vượt phạm vi, không tiết lộ prompt nội bộ, không mutate state trái phép, và không đưa ra grounded answer khi không có bằng chứng.

## 2. User/problem this solves
Trong một learning platform có chatbot và agent, rủi ro không nằm ở "model trả lời sai" đơn thuần mà còn ở:
- prompt injection;
- scope leakage sang course không được phép;
- hallucinated citations;
- user xác nhận nhầm action state-changing;
- lộ thông tin nhạy cảm qua logs hay output.

## 3. System scope
Main surfaces:
- `/agent`
- Lecture AI Tutor
- `/replan`

Core files:
- `src/services/agent_policy_service.py`
- `src/services/agent_structured_router.py`
- `src/services/agentic_rag_pipeline.py`
- `src/services/agent_response_composer.py`
- `src/services/llm_service.py`
- `src/services/replan_*`
- `src/prompts/agent/agentic_rag.yaml`

## 4. Architecture & flow
Guardrails không nằm ở một middleware duy nhất mà là multi-layer defense:

```text
input
  -> routing guard
  -> scope/policy guard
  -> evidence guard
  -> pending-action confirmation
  -> safe fallback / error mapping
  -> output contract enforcement
```

Lecture tutor có thêm tutor-specific prompt guardrails. Replan có input guardrails riêng cho knowledge claim.

## 5. Key components
- `StructuredAgentRouter`: structured output thay cho free-form intent text.
- `AgentPolicyService`: chặn content ngoài allowed course scope.
- `AgenticRAGPipeline`: enforce no-evidence-no-grounded-answer.
- `AgentResponseComposer`: hạ confidence khi không đủ citation.
- `PendingAction` flow: bước xác nhận trước khi commit assessment/replan/path action.
- Tutor prompt guardrails trong `_build_tutor_system_instruction(...)`.
- Replan guardrails trong `replan_keyword_planner` và `replan_service`.

## 6. Data model / contracts
Agent response contract cho phép guardrail metadata được expose có kiểm soát:
- `confidence`
- `warning`
- `fallback.errorCode`
- `citations`
- `actions`

Pending action mang:
- `action_id`
- `type`
- `status`
- `payload`
- `idempotency_key`
- `expires_at`

PII runtime adapter đã có file trong `src/services/guardrails/*`, nhưng cần phân biệt rõ mức độ wired-thực-tế theo branch/runtime.

## 7. Technical decisions
- Guardrails chia thành nhiều lớp, không đặt kỳ vọng vào một prompt duy nhất.
- State-changing actions không commit trực tiếp từ LLM output.
- Evidence là contract backend-level, không chỉ là UI decoration.
- Error mapping trả về safe fallback thay vì leak exception.

## 8. Risks / trade-offs
- Guardrails mạnh hơn thì UX có thể "không mềm" bằng chatbot mở.
- Structured router và policy rules cần được test chặt, nếu không sẽ có false positive.
- PII handling dễ trở thành khoảng mờ nếu docs, registry, và runtime implementation không đồng bộ.
- Team dễ nhầm giữa "prompt guardrail" và "enforced runtime guardrail"; report nên chỉ rõ sự khác nhau này.

## 9. Testing / validation
Files hữu ích:
- `tests/services/test_llm_service_prompt.py`
- `tests/services/test_llm_service_guardrails.py`
- `tests/services/test_agent_structured_router.py`
- `tests/services/test_agent_evidence_quality.py`
- `tests/services/test_agent_action_service.py`
- `tests/services/test_replan_service.py`

Cần xác nhận:
- no evidence -> không trả grounded;
- out-of-scope -> bị block;
- pending action hết hạn -> không được approve;
- tutor không reveal hidden instructions.

## 10. Demo-worthy points
- Đây là một feature kỹ thuật rất tốt cho technical report vì nó cho thấy maturity của AI system.
- Có thể present nó như "safety architecture" thay vì chỉ là prompt engineering.
- Rất hợp để trích riêng thành một section về risk management và production readiness.
