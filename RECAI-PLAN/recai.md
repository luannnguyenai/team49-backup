# Research Notes: microsoft/RecAI

Date: 2026-04-23

## Mục tiêu

Tài liệu này ghi lại phần research về repo `microsoft/RecAI` và đối chiếu với codebase hiện tại `A20-App-049`, tập trung vào:

- recommendation
- search / retrieval
- conversational recommendation
- explanation / evaluation
- phần nào nên áp dụng ngay, phần nào chỉ nên học ý tưởng

## Kết luận ngắn

`RecAI` đáng dùng như một **pattern library cho LLM + recommender systems**, nhưng **không nên bê nguyên repo** vào codebase này.

Giá trị lớn nhất của `RecAI` với repo hiện tại là:

1. dùng LLM để **điều phối pipeline recommendation/search**
2. giữ **retrieval/ranking truyền thống** làm phần chọn item thật
3. thêm **explanation** và **evaluation** như first-class capability

Không nên vội áp dụng:

- fine-tuning / RL / teacher-model stack
- research scripts / Gradio-style demo architecture
- unrestricted SQL generation từ prompt

## `RecAI` là gì

Repo gốc:

- https://github.com/microsoft/RecAI

Theo root README, `RecAI` là monorepo nghiên cứu cho bài toán `LLM4Rec`: dùng LLM để làm recommender systems tương tác hơn, giải thích được hơn, kiểm soát được hơn, và đánh giá được tốt hơn.

Các nhánh chính trong repo:

- `InteRecAgent`
- `Knowledge_Plugin`
- `RecLM-emb`
- `RecLM-eval`
- `RecLM-gen`
- `RecLM-uni`
- `RecExplainer`

## Tóm tắt từng phần của `RecAI`

### 1. `InteRecAgent`

Nguồn:

- https://github.com/microsoft/RecAI/tree/main/InteRecAgent
- https://github.com/microsoft/RecAI/blob/main/InteRecAgent/README.md

Ý tưởng chính:

- LLM làm bộ não giao tiếp với user
- recommender tools làm phần thực thi
- pipeline tách thành:
  - query
  - retrieval
  - ranking

Điểm đáng học:

- plan-first orchestration
- tool-oriented recommendation flow
- conversational recommendation nhiều vòng
- memory cho dialogue và user profile

### 2. `Knowledge_Plugin`

Nguồn:

- https://github.com/microsoft/RecAI/tree/main/Knowledge_Plugin
- https://github.com/microsoft/RecAI/blob/main/Knowledge_Plugin/README.md

Ý tưởng chính:

- không fine-tune model
- thay vào đó bơm domain knowledge vào prompt theo cấu trúc

Điểm đáng học:

- inject domain knowledge có chọn lọc
- giữ recommender logic bên ngoài model
- prompt augmentation dựa trên signals thực

### 3. `RecLM-emb`

Nguồn:

- https://github.com/microsoft/RecAI/tree/main/RecLM-emb

Ý tưởng chính:

- embedding model tối ưu cho item retrieval
- phục vụ search query, item similarity, instruction-based retrieval

Điểm đáng học:

- semantic retrieval cho course search
- “similar to this course”
- query types đa dạng: vague query, negative intent, dialogue history

### 4. `RecLM-eval`

Nguồn:

- https://github.com/microsoft/RecAI/tree/main/RecLM-eval
- https://github.com/microsoft/RecAI/blob/main/RecLM-eval/README.md

Ý tưởng chính:

- benchmark recommendation theo nhiều task:
  - retrieval
  - ranking
  - explanation
  - conversation
  - chatbot
  - embedding retrieval/ranking

Điểm đáng học:

- đánh giá search/recommend/chat bằng eval riêng
- không chỉ test API contract mà còn test quality

### 5. `RecLM-gen` và `RecLM-uni`

Nguồn:

- https://github.com/microsoft/RecAI/tree/main/RecLM-gen
- https://github.com/microsoft/RecAI/tree/main/RecLM-uni
- https://aclanthology.org/2024.acl-long.443/

Ý tưởng chính:

- fine-tune LLM để làm recommender
- constrained generation để tránh recommend item ngoài catalog

Điểm đáng học:

- ý tưởng catalog-constrained output

Điểm chưa nên áp dụng sớm:

- SFT / RL / GRPO / teacher-model pipeline
- training infrastructure nặng

### 6. `RecExplainer`

Nguồn:

- https://github.com/microsoft/RecAI/tree/main/RecExplainer

Ý tưởng chính:

- explanation không phải phần phụ
- explanation là một track riêng, có đánh giá riêng

Điểm đáng học:

- chuẩn hóa “why recommended”
- đo chất lượng explanation thay vì chỉ render text

## Tình trạng codebase hiện tại

### Recommendation hiện tại

Các điểm chính:

- recommender backend mới ở [src/services/course_recommendation_engine.py](/D:/VSCODE/VINAI/A20-App-049/src/services/course_recommendation_engine.py:50)
- endpoints ở [src/routers/course_recommendations.py](/D:/VSCODE/VINAI/A20-App-049/src/routers/course_recommendations.py:48)
- catalog decoration ở [src/services/course_catalog_service.py](/D:/VSCODE/VINAI/A20-App-049/src/services/course_catalog_service.py:67)
- frontend auto-generate recommendations ở [frontend/stores/courseCatalogStore.ts](/D:/VSCODE/VINAI/A20-App-049/frontend/stores/courseCatalogStore.ts:65)

Đặc điểm:

- rule-based
- dựa trên bootstrap graph
- persisted recommendation rows + events
- có reason code / reason summary

Điểm mạnh:

- deterministic
- explainable
- testable

Điểm yếu:

- chưa có orchestration layer kiểu conversational recommendation
- chưa có eval quality riêng
- chưa nối trực tiếp với KG runtime

### Search hiện tại

Điểm chính:

- ô search ở [frontend/components/layout/TopNav.tsx](/D:/VSCODE/VINAI/A20-App-049/frontend/components/layout/TopNav.tsx:94) còn `readOnly`
- `GET /api/courses` chưa có `q`, filter, sort chuyên cho search

Kết luận:

- hiện **chưa có course search thật**

### KG hiện tại

Điểm chính:

- KG service ở [src/kg/service.py](/D:/VSCODE/VINAI/A20-App-049/src/kg/service.py:30)
- router ở [src/kg/router.py](/D:/VSCODE/VINAI/A20-App-049/src/kg/router.py:97)

KG đang làm được:

- topic context
- learning path
- next-topic ranking

Nhưng:

- course recommender hiện tại **không dùng KG trực tiếp**

### Tutor hiện tại

Điểm chính:

- tutor runtime ở [src/services/llm_service.py](/D:/VSCODE/VINAI/A20-App-049/src/services/llm_service.py:222)
- tool layer sơ khai ở [src/tools.py](/D:/VSCODE/VINAI/A20-App-049/src/tools.py:9)

Đặc điểm:

- LangGraph
- transcript-window retrieval
- legacy lecture based
- chưa phải recommendation-aware assistant

## Bảng so sánh

| Phần | `RecAI` | Codebase hiện tại | Có thể áp dụng |
|---|---|---|---|
| Recommendation pipeline | Query -> Retrieve -> Rank -> Explain | Rule-based scoring trực tiếp | Tách recommender thành pipeline rõ ràng |
| Conversational recommendation | Có trong `InteRecAgent` | Chưa có | Làm assistant cho course discovery |
| Search / retrieval | Có retrieval-oriented thinking và embedding branch | Chưa có search thật | Làm semantic course search |
| Learner memory | Có dialogue memory + profile memory | Chưa có lớp memory chung | Persist goals, likes, dislikes, weak skills |
| Explanation | `RecExplainer` và explanation eval | Có `reason_summary` nhưng còn mỏng | Nâng cấp “why recommended” |
| Evaluation | `RecLM-eval` khá mạnh | Chủ yếu test behavior/API | Thêm eval cho relevance/quality |
| Catalog constraint | `RecLM-uni` chống out-of-domain output | Chưa có conversational output kiểu này | Nếu build AI recommender, chỉ trả item hợp lệ |
| Fine-tuning recommender | Có `RecLM-gen`, `RecLM-uni` | Chưa cần | Chưa nên làm sớm |

## Những gì nên áp dụng ngay

### P0

1. Làm `course search` thật
2. Refactor recommendation thành pipeline `filter -> retrieve -> rank -> explain`
3. Thêm learner profile memory có cấu trúc
4. Dựng evaluation suite riêng cho recommend/search/explanation

### P1

1. Inject structured knowledge từ course graph + KG + learner state vào prompt/tool context
2. Xây conversational recommendation UI
3. Nâng cấp explanation quality

### P2

1. Thử semantic retrieval / similar-course retrieval
2. Nếu có AI recommender tự do, thêm catalog-constrained output

### P3

1. Chỉ cân nhắc fine-tuning / RL khi đã có:
   - data đủ tốt
   - search baseline tốt
   - evaluation pipeline rõ

## Những gì không nên bê nguyên

- Không copy nguyên architecture của `RecAI`
- Không kéo whole training stack vào FastAPI app hiện tại
- Không cho LLM sinh SQL/query tự do
- Không dựa vào prompt-only memory cho dữ liệu người học thật
- Không dùng explanation chỉ để “cho đẹp UI”; phải đo được chất lượng

## Đề xuất roadmap ngắn cho repo này

### Phase 1: Search

- thêm `q`, filter, sort cho catalog API
- biến ô search hiện tại thành search thật
- thêm test cho search relevance cơ bản

### Phase 2: Recommender pipeline

- tách recommender thành các bước:
  - filter
  - retrieve
  - rank
  - explain
- nối learner state vào pipeline

### Phase 3: Eval

- tạo benchmark nội bộ cho:
  - recommendation relevance
  - search relevance
  - explanation quality
  - conversational recommendation

### Phase 4: AI assistant cho course discovery

- chat assistant để tìm course
- refine query qua nhiều vòng
- trả card recommendation + lý do + filter controls

## Nguồn tham khảo chính

- Root repo: https://github.com/microsoft/RecAI
- Root README: https://github.com/microsoft/RecAI/blob/main/README.md
- InteRecAgent: https://github.com/microsoft/RecAI/tree/main/InteRecAgent
- Knowledge Plugin: https://github.com/microsoft/RecAI/tree/main/Knowledge_Plugin
- RecLM-eval: https://github.com/microsoft/RecAI/tree/main/RecLM-eval
- RecLM-gen: https://github.com/microsoft/RecAI/tree/main/RecLM-gen
- RecLM-uni: https://github.com/microsoft/RecAI/tree/main/RecLM-uni
- ACL paper for `RecLM-gen`: https://aclanthology.org/2024.acl-long.443/

## Final takeaway

Nếu rút gọn toàn bộ research xuống một câu:

> Với codebase này, nên dùng LLM để điều phối và giải thích recommendation/search, còn phần chọn course thật vẫn nên dựa trên retrieval, ranking, graph, và learner state có cấu trúc.
