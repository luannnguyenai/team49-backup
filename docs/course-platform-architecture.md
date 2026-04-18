# Course Platform Architecture

> Server-authoritative data architecture for the course-first learning platform refactor.

## Overview

The course platform follows a **server-authoritative** data model where PostgreSQL is the single source of truth for all application data. Bootstrap files (`data/course_bootstrap/`) are used for import/seeding only — they are never read at runtime by the frontend.

```
┌─────────────────────────────────────┐
│           Next.js Frontend          │
│  (App Router, Zustand, Axios)       │
│                                     │
│  /                  → CourseCatalog │
│  /courses/:slug     → Overview      │
│  /courses/:slug/    → LearningUnit  │
│    learn/:unitSlug    Shell + Tutor │
└──────────────┬──────────────────────┘
               │ HTTP / JSON
               ▼
┌─────────────────────────────────────┐
│         FastAPI Backend             │
│  (SQLAlchemy, Pydantic, LangGraph) │
│                                     │
│  /api/courses       → Catalog       │
│  /api/courses/:slug → Overview      │
│  /api/courses/:slug/start → Entry   │
│  /api/courses/:slug/               │
│    units/:unitSlug  → LearningUnit  │
│  /api/lectures/ask  → Tutor Q&A    │
└──────────────┬──────────────────────┘
               │ SQL
               ▼
┌─────────────────────────────────────┐
│           PostgreSQL                │
│  (Users, Sessions, Lectures, etc.) │
└─────────────────────────────────────┘
```

## Data Flow Layers

### 1. Bootstrap Layer (Import Only)

**Location:** `data/course_bootstrap/`

| File | Purpose |
|------|---------|
| `courses.json` | Course catalog definitions (CS231n, CS224n) |
| `overviews.json` | Course overview content (headlines, outcomes) |
| `units.json` | Learning unit mappings (18 CS231n lectures) |

These files are read by `src/services/course_bootstrap_service.py` and `src/services/learning_unit_service.py` to seed or serve course metadata. They are **not** directly consumed by the frontend.

### 2. Legacy Lecture Layer

**Location:** `data/CS231n/` + `src/models/store.py`

| Component | Purpose |
|-----------|---------|
| `data/CS231n/videos/` | Raw video files (MP4) |
| `data/CS231n/transcripts/` | Transcript data |
| `data/CS231n/slides/` | Slide assets |
| `data/CS231n/ToC_Summary/` | Table of contents |
| `Lecture` model | Legacy DB model for ingested lectures |
| `Chapter` model | Chapter markers with timestamps |
| `TranscriptLine` model | Searchable transcript segments |
| `QAHistory` model | Tutor Q&A history |

The `units.json` bootstrap data maps `legacy_lecture_id` fields to connect the new course-first unit system with existing lecture records.

### 3. Course Platform Layer (New)

**Location:** `src/schemas/course.py` + `src/routers/courses.py`

| Schema | API | Purpose |
|--------|-----|---------|
| `CourseCatalogResponse` | `GET /api/courses` | Public catalog listing |
| `CourseOverviewResponse` | `GET /api/courses/{slug}` | Course detail + entry decision |
| `StartLearningDecisionResponse` | `POST /api/courses/{slug}/start` | Auth/onboarding/skill-test gate |
| `LearningUnitResponse` | `GET /api/courses/{slug}/units/{unitSlug}` | Unit content + tutor context |

## Import Boundaries

### Frontend → Backend

The frontend **never** reads from `data/` directly. All data flows through API endpoints:

```
Frontend                    Backend
─────────                   ───────
courseApi.catalog()      →  GET /api/courses
courseApi.overview(slug) →  GET /api/courses/{slug}
courseApi.start(slug)    →  POST /api/courses/{slug}/start
courseApi.learningUnit() →  GET /api/courses/{slug}/units/{unitSlug}
```

### Backend Service Boundaries

```
courses.py (router)
  ├─ course_catalog_service.py    → reads bootstrap courses + overviews
  ├─ course_entry_service.py      → 4-gate decision chain
  └─ learning_unit_service.py     → reads bootstrap units, resolves video paths

llm_service.py (tutor)
  └─ reads legacy Lecture/Chapter/TranscriptLine from DB via store.py
```

### State Management

| Store | Scope | Persistence |
|-------|-------|-------------|
| `authStore` | User session, tokens | Cookie + localStorage |
| `courseCatalogStore` | Catalog view (all/recommended) | Memory (per-session) |

## Decision Service Pattern

The `course_entry_service.py` implements a **4-gate decision chain** for course access:

```
Gate 1: Course Availability
  └─ Is the course status "ready"?
     ├─ No  → course_unavailable
     └─ Yes ↓

Gate 2: Authentication
  └─ Is the user authenticated?
     ├─ No  → auth_required (redirect /login?next=...)
     └─ Yes ↓

Gate 3: Onboarding
  └─ Has the user completed onboarding?
     ├─ No  → redirect /onboarding
     └─ Yes ↓

Gate 4: Skill Test
  └─ Has the user completed the assessment?
     ├─ No  → skill_test_required (redirect /assessment)
     └─ Yes → learning_ready (redirect /courses/{slug}/learn/{unitSlug})
```

## Legacy Compatibility

### Tutor Migration (US3)

| Old Route | New Behavior |
|-----------|-------------|
| `/tutor` | Shows compatibility banner → links to course catalog |
| `/learn` | Redirects to `/` (course catalog) |
| `/learn/{topicId}` | Redirects to `/courses/cs231n` |

The AI Tutor is now embedded within `LearningUnitShell` as `InContextTutor`, sharing the same `/api/lectures/ask` endpoint but with an optional `context_binding_id` that scopes Q&A to the active unit.

### Lecture-to-Unit Mapping

Each learning unit in `units.json` has a `legacy_lecture_id` field that maps to the original `Lecture.id` in the database. This allows:

1. Loading chapters/transcript via legacy API (`/api/lectures/{id}/toc`)
2. Binding tutor questions to the correct lecture context
3. Preserving existing progress and Q&A history

## File Structure

```
src/
├── routers/courses.py           # Course platform API endpoints
├── schemas/course.py            # Pydantic response schemas
├── services/
│   ├── course_bootstrap_service.py  # Bootstrap data loader
│   ├── course_catalog_service.py    # Catalog + recommendations
│   ├── course_entry_service.py      # Start-learning decision chain
│   └── learning_unit_service.py     # Learning unit payloads
├── models/
│   ├── store.py                     # Legacy lecture ORM models
│   └── ...
│
frontend/
├── app/
│   ├── page.tsx                     # Public catalog home
│   ├── courses/[courseSlug]/
│   │   └── page.tsx                 # Course overview
│   └── (protected)/courses/[courseSlug]/
│       └── learn/[unitSlug]/
│           └── page.tsx             # Canonical learning page
├── components/
│   ├── course/                      # Catalog + overview components
│   └── learn/
│       ├── LearningUnitShell.tsx     # Unified lecture experience
│       └── InContextTutor.tsx        # In-context AI Tutor
├── stores/
│   ├── authStore.ts
│   └── courseCatalogStore.ts
├── lib/
│   ├── api.ts                       # Typed API client
│   └── course-gate.ts               # Client-side gate helpers
└── types/index.ts                   # Shared TypeScript types
```
