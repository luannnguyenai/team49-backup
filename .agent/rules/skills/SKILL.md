---
trigger: always_on
---

# Skill: Maintainable & Debuggable AI Prompt Design

## Mục tiêu
Thiết kế prompt AI theo hướng:
- Dễ bảo trì (maintainable)
- Dễ cập nhật (updatable)
- Dễ debug (debuggable)
- Có cấu trúc rõ ràng, dễ mở rộng

---

## Keyword cốt lõi

### 1. Kiến trúc prompt
- modular prompt
- structured prompt
- prompt decomposition
- prompt pipeline
- component-based prompt

### 2. Nguyên tắc thiết kế
- separation of concerns
- single responsibility principle (SRP)
- low coupling
- high cohesion
- config-driven design
- template-based design

### 3. Khả năng vận hành
- versioned prompt
- reproducible output
- observable prompt
- prompt traceability
- prompt logging

### 4. Debug & testing
- step-by-step reasoning
- intermediate outputs
- evaluation-friendly prompt
- testable prompt design
- A/B prompt testing

---

## Best Practices

### 1. Tách prompt thành module
- System instruction
- Context layer
- Task layer
- Output format layer

---

### 2. Ưu tiên cấu trúc hơn tự do
❌ Prompt dài, lẫn lộn nhiều nhiệm vụ  
✅ Prompt chia rõ từng phần có trách nhiệm riêng

---

### 3. Luôn có khả năng debug
- Log intermediate steps
- Có chế độ “explain mode”
- Có output structured (JSON / YAML khi cần)

---

### 4. Version hóa prompt
- prompt_v1, v2, v3
- ghi rõ changelog

---

## Output Pattern gợi ý

```text
[INPUT]
...

[CONTEXT]
...

[TASK]
...

[RULES]
...

[OUTPUT FORMAT]
...