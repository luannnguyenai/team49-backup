# Course-First Refactor Architecture

## Mục đích của file này

File này mô tả ngắn gọn nhưng rõ ràng kiến trúc mà đợt refactor hiện tại đang bám theo, để khi review code hoặc UI bạn có thể trả lời nhanh 3 câu hỏi:

1. Hệ thống đang lấy gì làm trung tâm?
2. Frontend, backend, database, legacy layer đang nối với nhau như thế nào?
3. Vì sao `:8000` và `:3000` đang cho hai trải nghiệm khác nhau?

## Kiến trúc đang theo

Refactor hiện tại đang theo kiến trúc:

- `course-first product architecture`
- `server-authoritative data architecture`
- `headless core + presentation adapters` ở frontend
- `strangler migration` cho phần legacy tutor/lecture cũ

Nói ngắn gọn:

- sản phẩm lấy `course` làm entry point chuẩn
- backend là nguồn dữ liệu runtime chuẩn
- frontend tách logic khỏi lớp trình bày để có thể đổi giao diện mà không đổi flow
- các phần legacy chưa bị xóa hẳn, mà đang được bọc lại và di chuyển dần vào flow mới

## 1. Product architecture: course-first

Flow chuẩn sau refactor là:

`Home -> Course Overview -> Start learning -> auth/onboarding/skill test -> Learning Unit -> AI Tutor in-context`

Điểm quan trọng:

- không còn coi `/tutor` là entry point chính
- không còn tư duy “vào thẳng một page rời”
- user phải đi qua context của một `course`
- `AI Tutor` nằm bên trong trang học thật, không phải một sản phẩm tách rời

## 2. Frontend architecture: headless core + presentation adapters

Frontend hiện tại không nên hiểu là “một bộ page UI thuần”. Nó được chia làm 3 lớp:

### A. Core behavior

Đây là phần không nên rollback khi đổi giao diện:

- route flow
- auth gating
- onboarding / assessment gating
- recommendation logic
- start-learning decision flow
- learning-unit loading

Các file kiểu này gồm:

- `frontend/lib/api.ts`
- `frontend/lib/auth-redirect.ts`
- `frontend/lib/course-gate.ts`
- `frontend/stores/courseCatalogStore.ts`
- `frontend/features/course-platform/presenters.ts`

### B. Route orchestration

Các page route chỉ lấy data, gọi decision API, rồi truyền xuống UI:

- `frontend/app/page.tsx`
- `frontend/app/courses/[courseSlug]/page.tsx`
- `frontend/app/courses/[courseSlug]/start/page.tsx`
- `frontend/app/(protected)/courses/[courseSlug]/learn/[unitSlug]/page.tsx`

### C. Presentation layer

Đây là nơi vừa rồi mình re-skin để kéo visual từ `main` về:

- `frontend/components/layout/TopNav.tsx`
- `frontend/components/course/CourseCatalog.tsx`
- `frontend/components/course/CourseOverview.tsx`
- `frontend/components/learn/LearningUnitShell.tsx`

Ý nghĩa của cách chia này:

- muốn đổi UI thì sửa lớp trình bày
- không phải phá start flow hay tutor flow
- `main` được dùng làm `presentation donor`, còn branch refactor là `behavior donor`

## 2.1. Chức năng từng page phía frontend

### `frontend/app/page.tsx`

Chức năng:

- render public home
- load course catalog
- nếu user đã đăng nhập và đã có recommendation thì cho chuyển `Recommended / All`
- là entry point chính của sản phẩm phía UI

Không nên làm ở đây:

- tự quyết định logic gate
- tự đọc raw file trong `data/`
- tự tính recommendation

### `frontend/app/courses/[courseSlug]/page.tsx`

Chức năng:

- render `Course Overview`
- gọi overview API
- hiển thị trạng thái course
- bấm `Start learning` để gọi decision endpoint

Trạng thái hiện tại:

- `CS231n` có thể start
- `CS224n` bị khóa ở `coming_soon`

### `frontend/app/courses/[courseSlug]/start/page.tsx`

Chức năng:

- là route chuyển tiếp logic
- không phải page nội dung chính
- dùng để giữ `course context` khi hệ thống phải redirect qua login / onboarding / assessment

Ý nghĩa:

- user bấm start ở overview
- backend trả decision
- user vẫn quay lại đúng course flow ban đầu

### `frontend/app/(protected)/courses/[courseSlug]/learn/[unitSlug]/page.tsx`

Chức năng:

- render learning unit chuẩn
- load learning-unit payload
- là page học thật của user

Không nên biến nó thành:

- standalone tutor page
- page chỉ hiển thị video không có context course

### `frontend/app/tutor/page.tsx`

Chức năng hiện tại:

- route compatibility
- không còn là entry point chính

Nó tồn tại để:

- không làm vỡ link cũ
- chuyển user về flow course-first

## 3. Backend architecture: API-first + legacy compatibility

Backend FastAPI hiện tại đóng 2 vai:

### A. Runtime API chuẩn cho flow mới

Các router mới phục vụ course-first platform:

- `src/routers/courses.py`
- `src/routers/auth.py`
- `src/routers/assessment.py`
- `src/routers/content.py`
- `src/routers/history.py`

Các endpoint quan trọng:

- `GET /api/courses`
- `GET /api/courses/{slug}`
- `POST /api/courses/{slug}/start`
- `GET /api/courses/{slug}/units/{unitSlug}`

### B. Legacy lecture/tutor compatibility

Vẫn còn tồn tại để tận dụng data CS231n cũ:

- `GET /api/lectures/{lecture_id}/toc`
- `POST /api/lectures/ask`
- progress routes cũ

Đây là lý do hiện tại hệ thống vẫn là kiến trúc lai:

- `course-first` đã là flow chính
- nhưng tutor context và lecture metadata vẫn còn nối vào legacy lecture layer

## 3.1. Chức năng từng lớp backend

### `src/api/app.py`

Chức năng:

- khởi tạo FastAPI app
- mount static/data assets cần thiết
- include các router
- expose health check
- expose root landing cho backend API

Sau khi sửa:

- `GET /` không còn serve UI legacy
- `GET /` chỉ mô tả đây là backend API surface

### `src/routers/courses.py`

Chức năng:

- public course catalog
- course overview
- start-learning decision
- learning-unit payload

Đây là router quan trọng nhất của flow mới.

### `src/services/course_catalog_service.py`

Chức năng:

- trả catalog cho home
- hỗ trợ `all` và `recommended`
- gắn status `ready` / `coming_soon`

### `src/services/course_entry_service.py`

Chức năng:

- quyết định khi user bấm `Start learning`
- đây là nơi thực thi chuỗi gate:
  - course available?
  - authenticated?
  - onboarded?
  - finished assessment?
  - ready to enter learning unit?

### `src/services/learning_unit_service.py`

Chức năng:

- trả payload cho learning page
- resolve unit sang content, video, tutor binding
- nối unit mới với legacy lecture mapping nếu cần

### `src/services/llm_service.py`

Chức năng:

- phục vụ luồng AI Tutor
- đọc context lecture/transcript/chapter từ layer legacy
- stream câu trả lời cho tutor

### `src/models/store.py`

Chức năng:

- giữ ORM layer legacy cho `Lecture`, `Chapter`, `TranscriptLine`, `QAHistory`
- hiện vẫn cần cho CS231n tutor/lecture stack

Đây là một phần migration layer, chưa phải canonical domain model cuối cùng.

## 3.2. Chức năng các endpoint quan trọng

### `GET /`

Chức năng:

- xác nhận đây là backend API
- chỉ dẫn sang frontend dev server
- cung cấp link nhanh tới health/docs/openapi

### `GET /health`

Chức năng:

- health check của backend

### `GET /api/courses`

Chức năng:

- trả danh sách course cho home
- hỗ trợ public catalog
- có thể trả recommendation nếu user đủ điều kiện

### `GET /api/courses/{slug}`

Chức năng:

- trả dữ liệu overview của course
- trả luôn entry state để biết course có thể start hay đang bị block

### `POST /api/courses/{slug}/start`

Chức năng:

- quyết định redirect target chuẩn khi user bấm start
- giữ course context xuyên suốt auth / onboarding / assessment

### `GET /api/courses/{slug}/units/{unitSlug}`

Chức năng:

- trả payload để render learning page
- gồm:
  - course title
  - unit title
  - content/video
  - tutor enablement
  - context binding

### `GET /api/lectures/{lecture_id}/toc`

Chức năng:

- legacy endpoint trả chapter markers
- learning shell hiện vẫn dùng để hiện chapter rail cho lecture cũ

### `POST /api/lectures/ask`

Chức năng:

- endpoint hỏi đáp cho AI Tutor
- hiện là cầu nối chính giữa learning page mới và lecture stack cũ

## 4. Data architecture: server-authoritative

Kiến trúc dữ liệu đang theo hướng:

- `PostgreSQL` là nguồn dữ liệu có thẩm quyền
- backend là lớp duy nhất frontend đọc runtime data
- `data/` chỉ là nguồn bootstrap / import / static assets

Không nên coi:

- `frontend/data`
- JSON trong repo
- file client-side

là runtime source of truth cho production.

### Phân vai

#### PostgreSQL

Chứa:

- user
- auth / onboarding / assessment state
- recommendation
- progress
- lecture metadata đã ingest
- tutor history / bindings

#### Repository `data/`

Chứa:

- raw assets và bootstrap content
- CS231n videos / transcript / slides / ToC
- bootstrap metadata cho course catalog / overview / units

Vai trò:

- import
- local development support
- transitional compatibility

Không phải:

- runtime source trực tiếp cho frontend

## 5. Domain model đang hướng tới

Refactor hiện tại đang chuẩn hóa quanh trục:

`Course -> Section -> LearningUnit -> Asset`

### Course

Đại diện một khóa học hiển thị ở catalog.

Ví dụ:

- `CS231n`
- `CS224n`

### Section

Nhóm cấu trúc bên trong khóa học.

### LearningUnit

Đơn vị nhỏ nhất mà user thực sự mở để học.

Ví dụ:

- một lecture
- một reading unit
- một lesson

### Asset

Metadata trỏ tới video, transcript, slide, thumbnail, supplement.

## 5.1. Chức năng business của từng thực thể

### Course

Chức năng business:

- đơn vị catalog mà user nhìn thấy đầu tiên
- quyết định trạng thái public của một khóa học

### CourseOverview

Chức năng business:

- content layer cho pre-learning stage
- giúp user hiểu course trước khi bấm start

### Section

Chức năng business:

- nhóm cấu trúc điều hướng bên trong course
- chuẩn bị cho trường hợp sau này có nhiều module/unit phức tạp hơn

### LearningUnit

Chức năng business:

- canonical learning surface
- mọi trải nghiệm học thật đều nên đi qua đây

### Asset

Chức năng business:

- tách metadata của tài nguyên khỏi file binary thật
- để backend kiểm soát runtime eligibility và delivery URL

## 6. Trạng thái migration hiện tại

Hệ thống chưa phải “refactor xong hoàn toàn”. Hiện tại nó đang ở trạng thái migration có kiểm soát:

### Đã chuyển sang flow mới

- public catalog
- course overview
- start-learning gate
- auth/onboarding/assessment redirect chain
- learning page có AI Tutor in-context
- `/tutor` chỉ còn compatibility behavior

### Chưa xóa hẳn legacy

- legacy lecture APIs vẫn còn
- file `src/api/static/index.html` vẫn còn tồn tại
- backend vẫn mount `/static`
- tutor backend vẫn tận dụng lớp lecture cũ

## 7. Vì sao `127.0.0.1:8000` trước đó hiện UI cũ?

Vì trước khi sửa, root route của FastAPI là:

- `GET /` -> `FileResponse("src/api/static/index.html")`

Tức là backend đang serve một static HTML legacy ngay tại root.

Nó không phải frontend mới.

Sau khi sửa:

- `GET /` của backend trả về một API landing JSON
- nói rõ đây là backend API surface
- chỉ người dùng sang frontend dev server ở `http://127.0.0.1:3000`
- legacy static UI vẫn còn nếu cần tra cứu ở `/static/index.html`

## 8. URL nào dùng để review cái gì

### Frontend đúng để review sản phẩm

- `http://127.0.0.1:3000`

Đây là Next.js app, tức là nơi bạn review:

- home
- overview
- learning shell
- top nav
- tutor in-context

### Backend đúng để review API

- `http://127.0.0.1:8000`

Đây là FastAPI backend, dùng để:

- health check
- API runtime
- OpenAPI docs

Các endpoint nên xem:

- `/health`
- `/docs`
- `/openapi.json`

## 9. Kiến trúc hiện tại nên được gọi thế nào cho đúng

Nếu cần mô tả ngắn cho team hoặc cho người review code, câu đúng nhất là:

> Đây là một kiến trúc `course-first`, `server-authoritative`, với frontend theo kiểu `headless core + presentation adapters`, và backend đang ở trạng thái `strangler migration` để hấp thụ dần legacy lecture/tutor stack vào flow mới.

## 10. Quy tắc thực tế khi làm tiếp

Nếu tiếp tục refactor sau này thì nên giữ các nguyên tắc này:

- đổi giao diện: sửa presentation layer trước
- đổi flow: sửa core behavior và API contract
- thêm course mới: thêm vào authoritative content layer, không để frontend đọc file raw trực tiếp
- xóa legacy: chỉ xóa khi lecture/tutor mapping đã đi hết qua canonical learning-unit model
- backend root phải giữ vai trò API surface, không quay lại serve UI legacy ở `/`
