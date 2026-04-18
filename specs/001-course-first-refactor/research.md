# Research: Course-First Platform Refactor

## Decision 1: Use a canonical course-first content model

- **Decision**: Normalize runtime content around `Course -> Module/Section -> Lesson/Lecture -> Asset` and map legacy lecture data into that structure.
- **Rationale**: The current system mixes `modules/topics` for learning flows with a separate `lectures/chapters/transcript` tutor stack. A canonical model is necessary to support one entry flow and one authoritative content layer.
- **Alternatives considered**:
  - Keep separate `modules/topics` and `lectures` domains and stitch them in the frontend. Rejected because it preserves the existing architectural split.
  - Keep the current assessment-first structure and only add overview pages. Rejected because it does not solve the detached tutor flow or runtime content inconsistency.

## Decision 2: Treat repository data as import sources, not runtime sources

- **Decision**: Repository files under `data/` remain developer/bootstrap inputs only; runtime catalog, overview, progress, and learning-entry data must come from server-managed application storage.
- **Rationale**: Production clients cannot rely on repository-local files, especially when backend hosting and frontend delivery may be separated. This decision also makes future course expansion operationally realistic.
- **Alternatives considered**:
  - Continue reading `data/*.json` directly in the app at runtime. Rejected because it couples runtime behavior to the deployed file layout.
  - Store all metadata in frontend-only static bundles. Rejected because availability, progress, and recommendation behavior require server authority.

## Decision 3: Keep PostgreSQL as the authoritative operational database

- **Decision**: Continue with PostgreSQL as the primary database for catalog, overview metadata, assessment state, recommendations, progress, and tutor history.
- **Rationale**: The project already uses SQLAlchemy, asyncpg, and relational models. PostgreSQL is sufficient for current scope and can support future retrieval work incrementally.
- **Alternatives considered**:
  - Introduce a second operational database. Rejected because it increases migration cost with no immediate benefit.
  - Use files-only storage for course metadata. Rejected because it does not support server-authoritative runtime behavior.

## Decision 4: Use server-managed object storage for binary assets

- **Decision**: Videos, transcripts, slide PDFs, thumbnails, and related bulky assets should be served from server-managed storage endpoints rather than embedded in database rows or client-local files.
- **Rationale**: Binary assets have different delivery and scaling needs than relational metadata. Separating metadata from asset storage keeps the content model stable while allowing hosting flexibility.
- **Alternatives considered**:
  - Keep binary assets in the repository and expose them directly forever. Rejected because it is unsuitable for production hosting and growth.
  - Store asset binaries directly in PostgreSQL. Rejected because it complicates delivery and asset lifecycle management.

## Decision 5: Course availability must be first-class state

- **Decision**: Introduce explicit availability states including `ready`, `coming_soon`, and `metadata_partial`.
- **Rationale**: The product needs to show `CS224n` in the catalog and overview while blocking learning entry. Availability must be data-driven so future courses behave consistently without frontend hardcoding.
- **Alternatives considered**:
  - Special-case `CS224n` only in the UI. Rejected because it does not scale.
  - Hide unfinished courses entirely. Rejected because the approved product direction requires visible coming-soon courses.

## Decision 6: Replace standalone tutor navigation with in-context lecture tutoring

- **Decision**: AI Tutor becomes a panel or sub-surface inside the lecture or lesson page. The legacy `/tutor` route becomes a compatibility redirect rather than a primary product page.
- **Rationale**: The user approved a course-first flow where tutoring is part of the learning experience, not a separate product entry point.
- **Alternatives considered**:
  - Keep `/tutor` as a first-class page. Rejected because it perpetuates the current UX break.
  - Remove tutoring until course refactor is complete. Rejected because tutoring remains a core value proposition for `CS231n`.

## Decision 7: Preserve the existing skill-test gate while changing the entry flow

- **Decision**: Public visitors may browse catalog and overview pages, but starting learning requires auth and completion of the existing onboarding/skill-test flow before recommendation-based catalog views appear.
- **Rationale**: This matches the approved product behavior and minimizes disruption to existing adaptive-learning logic.
- **Alternatives considered**:
  - Force login before viewing catalog. Rejected because the approved flow keeps discovery public.
  - Remove skill-test gating. Rejected because it conflicts with the current product logic and user request.

## Decision 8: Add a three-layer test strategy for the refactor

- **Decision**: Validate the refactor with backend contract/service tests, frontend route/component tests, and end-to-end navigation tests for the public-to-learning flow.
- **Rationale**: This refactor crosses routing, authorization gates, content availability, and data normalization. Single-layer tests are insufficient to protect behavior during staged migration.
- **Alternatives considered**:
  - Backend-only regression coverage. Rejected because most breakage risk is in navigation and user flow.
  - End-to-end testing only. Rejected because failures would be too coarse and slow to debug.
