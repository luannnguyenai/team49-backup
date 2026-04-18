# Feature Specification: Course-First Platform Refactor

**Feature Branch**: `001-course-first-refactor`  
**Created**: 2026-04-18  
**Status**: Draft  
**Input**: User description: "Refactor the platform to a course-first flow with public home/catalog, course overview, in-context lecture tutor, CS231n ready, CS224n coming soon fallback, and production-ready server-side data architecture"

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Discover And Enter A Course (Priority: P1)

As a learner, I can open a public home page, browse the full course catalog, and open a course overview before deciding whether to start learning.

**Why this priority**: The current product has no coherent course-first entry flow. This story establishes the primary discovery journey and removes the need to enter through a disconnected tutor page.

**Independent Test**: Can be fully tested by opening the public home page, confirming both demo courses appear, opening each overview page, and validating that course actions reflect course availability.

**Acceptance Scenarios**:

1. **Given** a visitor opens the public home page, **When** the catalog loads, **Then** the system shows the demo courses `CS231n` and `CS224n` in the course listing.
2. **Given** a visitor opens the `CS231n` overview page, **When** the page renders, **Then** the overview shows course information and a start-learning action.
3. **Given** a visitor opens the `CS224n` overview page, **When** the page renders, **Then** the overview shows course information, labels the course as coming soon, and blocks all learning-entry actions.

---

### User Story 2 - Personalized Catalog After Skill Test (Priority: P2)

As an authenticated learner, I complete the existing skill-test flow and then see recommended courses while still being able to switch to the full course catalog.

**Why this priority**: The user wants recommendations to remain part of the experience, but only after login and skill assessment. This preserves the adaptive-learning value while keeping public discovery available.

**Independent Test**: Can be fully tested by signing in as a new user, completing onboarding and skill test, then verifying that the catalog shows a recommended view and an all-courses view.

**Acceptance Scenarios**:

1. **Given** a signed-in learner has not completed onboarding or skill test, **When** they try to start learning from a course overview, **Then** the system routes them through authentication and the required skill-test flow before granting access to learning actions.
2. **Given** a learner has completed the skill test, **When** they return to the home catalog, **Then** the system shows a recommended-courses view and also provides an all-courses tab that lists the full catalog.
3. **Given** a learner has completed the skill test but has no recommendation output yet, **When** the home catalog renders, **Then** the all-courses view still works without blocking access to ready courses.

---

### User Story 3 - Learn Inside A Unified Lecture Experience (Priority: P3)

As a learner inside a ready course, I move from course overview into the learning experience and use AI Tutor within the lecture page instead of navigating to a separate tutor product.

**Why this priority**: This resolves the largest UX inconsistency in the current codebase, where tutoring exists as a detached page rather than as part of the lesson experience.

**Independent Test**: Can be fully tested by starting a ready course, entering a lecture or lesson, confirming the AI Tutor is available within that page, and verifying the old standalone tutor route no longer acts as the primary entry point.

**Acceptance Scenarios**:

1. **Given** a learner starts a ready course, **When** they enter a lecture or lesson, **Then** the AI Tutor is available within the learning page as part of the same experience.
2. **Given** a learner is already inside a lecture, **When** they ask a tutor question, **Then** the question is associated with the current learning context instead of a detached standalone tutor flow.
3. **Given** a learner opens the legacy standalone tutor entry path, **When** the system handles that request, **Then** it redirects or reroutes them into the course-first learning flow instead of exposing the old disconnected experience.

### Edge Cases

- What happens when a course has overview metadata but no lecture metadata yet? The course remains visible in the catalog and overview, but the system must block learning entry and display a consistent coming-soon state.
- What happens when a learner deep-links directly to a blocked course lesson or lecture URL? The system must prevent entry and route the user back to the course overview with a clear availability message.
- What happens when recommendation data is unavailable after a completed skill test? The learner must still be able to use the all-courses catalog and start any ready course.
- What happens when a ready course has partial lecture assets, such as missing transcript or slide data? The system must still render the learning page and clearly degrade unavailable sub-features without exposing broken tutor entry points.
- What happens when a visitor starts a course while unauthenticated? The system must preserve the selected course context so the learner can continue from the same course after authentication and required onboarding.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a public home page that lists all courses available in the catalog.
- **FR-002**: The public catalog MUST include the demo courses `CS231n` and `CS224n`.
- **FR-003**: The system MUST provide a dedicated overview page for each course in the catalog.
- **FR-004**: Visitors MUST be able to open course overview pages without being authenticated.
- **FR-005**: The system MUST distinguish course availability states at minimum as `ready`, `coming_soon`, and `metadata_partial`.
- **FR-006**: The system MUST allow learning-entry actions only for courses in a learnable state.
- **FR-007**: The system MUST mark `CS231n` as learnable in the demo experience.
- **FR-008**: The system MUST mark `CS224n` as coming soon in the demo experience until lecture metadata is complete.
- **FR-009**: The system MUST block all learning-entry actions for coming-soon courses while still allowing overview access.
- **FR-010**: The system MUST preserve the selected course context when an unauthenticated visitor attempts to start learning.
- **FR-011**: The system MUST require authentication before a learner can enter any learning, assessment, progress, or tutor interaction flow.
- **FR-012**: The system MUST require the existing onboarding and skill-test flow before granting learning access to a signed-in learner who has not completed that flow.
- **FR-013**: The system MUST show a recommended-courses view only to learners who have completed the skill-test flow.
- **FR-014**: The system MUST also provide an all-courses view to authenticated learners, regardless of recommendation availability.
- **FR-015**: The system MUST allow overview content to be populated from mock or placeholder values until the final overview metadata model is ready.
- **FR-016**: The system MUST expose overview content through the same authoritative content layer that will later serve final production data.
- **FR-017**: The primary learning journey for ready courses MUST follow `home -> course overview -> start learning -> learning page -> in-context AI Tutor`.
- **FR-018**: The AI Tutor MUST be presented within the lecture or lesson learning experience, not as a separate primary product page.
- **FR-019**: Legacy standalone tutor navigation MUST redirect or reroute into the course-first flow instead of remaining a first-class entry point.
- **FR-020**: The system MUST support server-side course, overview, module, lesson, lecture, and availability data as authoritative runtime content.
- **FR-021**: The system MUST treat repository data files as import or bootstrap sources, not as browser-runtime sources of truth in the production architecture.
- **FR-022**: The system MUST support server-managed storage for binary course assets such as videos, transcripts, slides, and thumbnails.
- **FR-023**: The client application MUST consume course and learning data through application endpoints or delivery URLs managed by the server-side platform.
- **FR-024**: The system MUST persist learner progress, skill-test outcomes, recommendation inputs, and tutor interaction history in server-managed storage.
- **FR-025**: The system MUST present a consistent unavailable-state message whenever a learner attempts to enter content that is blocked by availability or missing metadata.
- **FR-026**: The system MUST support adding future courses to the catalog without requiring a new frontend flow for each course.

### Key Entities *(include if feature involves data)*

- **Course**: A catalog item representing a learnable program, including identity, title, summary, cover information, availability state, recommendation eligibility, and entry points.
- **Course Overview**: The public-facing overview content for a course, including hero text, outcomes, structure summary, badges, and placeholder-friendly metadata that can later be filled from production content.
- **Learning Unit**: A normalized instructional node within a course, such as a module, lesson, or lecture, with order, parent-child relationships, and availability status.
- **Course Asset**: A server-managed media or document resource associated with a course or learning unit, such as video, transcript, slides, thumbnails, or supporting files.
- **Learner Assessment Profile**: The learner’s onboarding and skill-test completion state, along with the outcomes used to unlock recommendations and learning entry.
- **Course Recommendation**: A personalized course ordering or highlighting record shown in the recommended-courses view after skill assessment.
- **Learning Progress Record**: A server-managed record of learner progress through course units, including completion state and return-to-learning context.
- **Tutor Interaction Context**: The current learning context and persisted history that ties AI Tutor interactions to the active learning unit instead of to a standalone tutor surface.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In acceptance testing, a visitor can reach either demo course overview from the public home page in no more than 2 navigation actions.
- **SC-002**: In acceptance testing, `CS231n` is startable from its overview and `CS224n` is consistently blocked as coming soon across 100% of tested catalog, overview, and deep-link entry paths.
- **SC-003**: In acceptance testing, a new signed-in learner can complete the required skill-test gate and return to a course catalog with both recommended and all-courses navigation available, without hitting a dead-end screen.
- **SC-004**: In acceptance testing, a learner can move from a ready course overview into a lecture or lesson and access AI Tutor within that learning page without needing to navigate to a standalone tutor page.
- **SC-005**: During runtime validation for the refactored flow, all catalog, overview, learning-entry, and availability states shown to end users are delivered from server-managed application data rather than from browser-local repository files.

## Assumptions

- Existing authentication, onboarding, and skill-test capabilities remain in scope for reuse rather than redesign in this refactor.
- The first release of this refactor only needs to support two visible demo courses: `CS231n` and `CS224n`.
- `CS224n` overview content may exist before full lecture metadata is available, and that is acceptable as long as learning actions remain blocked.
- Overview page content may initially use placeholder or mock values as long as it follows the final server-side content contract.
- Production runtime content is expected to come from server-managed storage and delivery layers, even if repository data files continue to exist as import sources during development.
- Admin tooling or CMS-style authoring for future courses is out of scope for this refactor.
- Mobile responsiveness is required because the current product is web-based, but a separate native-app experience is out of scope.
