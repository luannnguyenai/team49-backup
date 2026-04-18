# Hybrid Merge Plan: `001-course-first-refactor` + `db-review`

## Mục tiêu

Tạo một nhánh tích hợp giữ được:

- hướng sản phẩm đúng của `001-course-first-refactor`
- chất lượng backend/database tốt hơn từ `db-review`
- lịch sử commit của cả team khi đưa vào `main`

Tài liệu này không giả định merge thẳng hai nhánh rồi chấp nhận mọi conflict. Mục tiêu là tạo một nhánh integration có kiểm soát, preserve history, và chỉ đưa vào `main` sau khi đã xác nhận rõ phần nào được giữ, phần nào bị loại.

## Kết luận lựa chọn base

### Chọn `001-course-first-refactor` làm base

Lý do:

- nhánh này đã triển khai `course-first product flow`
- đã có canonical course domain: `src/models/course.py`
- đã có API runtime cho catalog/overview/start/learning unit: `src/routers/courses.py`
- frontend đã đi theo flow `Home -> Course -> Overview -> Start -> Learning Unit -> AI Tutor`

### Không dùng `db-review` làm base chính

Lý do:

- `db-review` mạnh ở database/backend hygiene nhưng chưa phải north-star product architecture hiện tại
- app bên đó vẫn còn mental model `LMS + RAG`
- backend root vẫn còn serve static HTML legacy tại `db-review:src/api/app.py`
- chưa có lớp canonical course platform tương đương `src/models/course.py` và `src/routers/courses.py`

## Kết luận lựa chọn chiến lược merge

### Mục tiêu của team

Bạn muốn khi vào `main` vẫn giữ được đóng góp commit của cả bạn và member kia để tính contribution theo từng commit.

### Chiến lược phù hợp

Giữ lịch sử bằng `merge commit`, không squash, và tích hợp qua một nhánh trung gian.

### Không dùng các cách sau nếu muốn giữ credit commit rõ ràng

- `Squash and merge`
- tự port toàn bộ bằng tay rồi chỉ tạo commit mới của một người
- rebase để ép lịch sử thành một chuỗi mới sạch hơn nhưng làm mất cấu trúc đóng góp ban đầu

## Phương án hybrid khuyến nghị

### Pha 1: Tạo integration branch từ `001-course-first-refactor`

```bash
git checkout 001-course-first-refactor
git pull --ff-only origin 001-course-first-refactor
git checkout -b hybrid/integrate-db-review
```

Mục tiêu:

- lấy nhánh hiện tại làm product baseline
- tích hợp `db-review` vào một vùng an toàn, không đụng `main`

### Pha 2: Merge `db-review` với preserve history

```bash
git merge --no-ff db-review
```

Mục tiêu:

- kéo toàn bộ commit history của `db-review` vào integration branch
- tạo merge commit rõ ràng để sau này audit được

Lưu ý:

- bước này gần như chắc chắn sẽ conflict
- không nên resolve theo kiểu "chọn theirs/all theirs" hoặc "chọn ours/all ours" hàng loạt

## Nguyên tắc resolve conflict

### Giữ từ `001-course-first-refactor`

- `src/models/course.py`
- `src/routers/courses.py`
- `src/schemas/course.py`
- `src/services/course_bootstrap_service.py`
- `src/services/course_catalog_service.py`
- `src/services/course_entry_service.py`
- `src/services/learning_unit_service.py`
- toàn bộ route/frontend flow liên quan course catalog, overview, start, learning unit
- tài liệu mô tả course-first architecture

### Lấy ý tưởng hoặc code từ `db-review`

- `DomainError` và exception handler
- `redis_url` và config explicit hơn
- Redis lifecycle trong app startup/shutdown
- CORS config bằng danh sách origin rõ ràng
- repository abstraction cho các phần đang chạm DB thật
- tách service/repository tốt hơn ở auth, assessment, question selection

### Không mang nguyên xi từ `db-review`

- backend root serve static HTML legacy
- mọi thay đổi làm mất hoặc làm yếu course-first flow
- giả định rằng lecture/content/learning/user là toàn bộ product domain

## Mapping khác biệt quan trọng

### `001-course-first-refactor` mạnh ở đâu

- product/system direction
- course-first runtime API
- canonical course model
- frontend integration với catalog/overview/learning/tutor
- backend root `/` không còn là UI legacy

### `db-review` mạnh ở đâu

- backend config rõ hơn
- Redis/client lifecycle
- exception model rõ hơn
- repository layer rõ hơn
- database hygiene và separation of concerns tốt hơn

### Kết luận system design

Hybrid tối ưu nhất là:

- giữ `001-course-first-refactor` làm `behavior and product architecture source`
- dùng `db-review` làm `backend infrastructure and quality pattern source`

## Thứ tự tích hợp an toàn

Sau khi merge `db-review` vào integration branch và resolve conflict tối thiểu để branch build lại được, tiếp tục làm thêm các commit integration theo từng nhóm nhỏ.

### Bước 1: Chuẩn hóa app/config layer

Mục tiêu:

- port `cors_origins`
- port `redis_url`
- port Redis lifecycle
- port exception handler registration

Files ưu tiên xem:

- `src/config.py`
- `src/api/app.py`
- `src/exceptions.py` nếu thêm mới
- `src/exception_handlers.py` nếu thêm mới
- `src/services/redis_client.py` hoặc file tương đương nếu thêm mới

### Bước 2: Port error model và failure semantics

Mục tiêu:

- thay các lỗi ad-hoc bằng domain exception rõ ràng ở backend nơi hợp lý
- không làm thay đổi public behavior của course-first routes ngoài việc trả lỗi sạch hơn

### Bước 3: Port repository pattern chọn lọc

Mục tiêu:

- chỉ áp repository ở các phần đã thật sự đọc/ghi DB có nghiệp vụ rõ
- không cố bọc mọi service bootstrap/data adapter hiện có chỉ để "đồng bộ style"

Ưu tiên:

- auth/user profile
- assessment history
- recommendation/progress khi các phần này đã DB-backed thật

### Bước 4: Port Redis-backed auth hardening

Mục tiêu:

- rate limiting rõ ràng hơn
- denylist/revocation nếu branch `db-review` đã có phần dùng được

Lưu ý:

- không được làm gãy login/onboarding/assessment flow hiện tại
- nếu `db-review` vẫn còn limiter in-memory trong auth router, chỉ lấy phần đã đủ chín

### Bước 5: Rà lại legacy handling

Mục tiêu:

- xác nhận phần nào vẫn đang là adapter phục vụ `CS231n`
- không xóa nhầm lecture/tutor legacy path đang nuôi learning unit

## Cách merge vào `main` để giữ commit history

Sau khi integration branch đã ổn:

```bash
git checkout main
git pull --ff-only origin main
git merge --no-ff hybrid/integrate-db-review
```

Hoặc nếu merge qua GitHub/GitLab:

- tạo PR từ `hybrid/integrate-db-review` vào `main`
- chọn `Create a merge commit`
- không chọn `Squash and merge`
- không chọn `Rebase and merge`

Kết quả:

- commit của bạn từ `001-course-first-refactor` vẫn còn
- commit của member kia từ `db-review` vẫn còn
- commit resolve/integration mới cũng còn

## Cách đọc contribution sau này

### Nếu merge theo kế hoạch này

- lịch sử trên `main` sẽ chứa commit của cả hai nhánh
- merge commit cho biết thời điểm tích hợp
- các commit integration bổ sung sẽ cho thấy ai chịu trách nhiệm hòa trộn hai hướng refactor

### Nếu chỉ cherry-pick hoặc port tay

- có thể dễ kiểm soát code hơn
- nhưng lịch sử team sẽ kém trung thực hơn về mặt contribution

## Rủi ro chính

### Rủi ro 1: Merge xong nhưng kiến trúc bị pha tạp

Dấu hiệu:

- route course-first vẫn còn nhưng app startup/config/error handling bị lẫn style cũ
- code compile được nhưng khó reasoning hơn trước

Giảm thiểu:

- resolve conflict theo nguyên tắc "product từ branch hiện tại, infra pattern từ db-review"

### Rủi ro 2: Lấy quá tay từ `db-review`

Dấu hiệu:

- vô tình khôi phục root static UI legacy
- route course-first bị suy yếu

Giảm thiểu:

- review kỹ `src/api/app.py`, `src/config.py`, `src/routers/auth.py`, `src/models/*`, `src/routers/courses.py`

### Rủi ro 3: Preserve history nhưng integration quá bẩn

Dấu hiệu:

- một merge commit khổng lồ, khó review

Giảm thiểu:

- sau merge `db-review`, tạo thêm commit integration theo từng nhóm nhỏ thay vì dồn hết vào một lần

## Checklist thực thi ngắn

- [ ] Tạo `hybrid/integrate-db-review` từ `001-course-first-refactor`
- [ ] Merge `db-review` bằng `--no-ff`
- [ ] Resolve conflict với nguyên tắc giữ course-first architecture
- [ ] Build/test lại tối thiểu sau merge
- [ ] Port có chọn lọc các phần mạnh của `db-review`
- [ ] Commit riêng cho từng nhóm integration
- [ ] Review lại system design sau integration
- [ ] Merge vào `main` bằng `--no-ff` hoặc `Create a merge commit`

## Bộ lệnh khuyến nghị

### Chuẩn bị branch

```bash
git checkout 001-course-first-refactor
git pull --ff-only origin 001-course-first-refactor
git checkout -b hybrid/integrate-db-review
```

### Merge preserve history

```bash
git merge --no-ff db-review
```

### Xem nhanh vùng nguy hiểm sau merge

```bash
git diff --name-only --diff-filter=U
```

```bash
git diff --stat 001-course-first-refactor...HEAD
```

```bash
git log --oneline --decorate --graph --max-count=40
```

### Chuẩn bị đưa vào `main`

```bash
git checkout main
git pull --ff-only origin main
git merge --no-ff hybrid/integrate-db-review
```

## Recommendation cuối

Nếu mục tiêu ưu tiên là:

- đúng kiến trúc sản phẩm
- giữ contribution commit của cả team
- vẫn nâng chất lượng backend một cách thực dụng

thì phương án tốt nhất là:

1. lấy `001-course-first-refactor` làm base
2. merge `db-review` vào integration branch để preserve history
3. resolve theo nguyên tắc `course-first core thắng, db-review infra được hấp thụ có chọn lọc`
4. merge integration branch vào `main` bằng merge commit, không squash
