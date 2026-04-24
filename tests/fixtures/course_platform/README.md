# Course Platform Test Fixtures

Shared fixture data for backend and frontend course-platform tests.

## Backend Usage

The backend tests in `tests/contract/` use direct imports and `httpx.AsyncClient` with `ASGITransport` to test against the live FastAPI app.

Course data is loaded from `data/bootstrap/` at test time via the bootstrap service — no separate fixture files are needed.

```python
# Example: tests/contract/test_course_catalog_api.py
from httpx import ASGITransport, AsyncClient
from src.api.app import app

class CourseCatalogApiContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        )
```

## Frontend Usage

Frontend tests use `vi.mock` to mock the `courseApi` module and provide fixture data inline or from `frontend/tests/fixtures/coursePlatform.ts`.

```typescript
import { CS231N_ITEM, CS224N_ITEM, LECTURE_1_UNIT } from "@/tests/fixtures/coursePlatform";
```

## Fixture Files

| File | Purpose |
|------|---------|
| `data/bootstrap/courses.json` | Course catalog definitions |
| `data/bootstrap/overviews.json` | Course overview content |
| `data/bootstrap/units.json` | Learning unit mappings |
| `frontend/tests/fixtures/coursePlatform.ts` | Frontend test fixture data |
