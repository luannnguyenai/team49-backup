# Data Model: Course-First Platform Refactor

## 1. Course

- **Purpose**: Represents a catalog-visible learning program.
- **Core fields**:
  - `id`
  - `slug`
  - `title`
  - `short_description`
  - `status` (`ready`, `coming_soon`, `metadata_partial`)
  - `visibility` (`public`, `hidden`)
  - `cover_image_url`
  - `hero_badge`
  - `primary_subject`
  - `sort_order`
- **Relationships**:
  - Has one `CourseOverview`
  - Has many `CourseSection`
  - Has many `CourseAsset`
  - Has many `CourseAvailabilityRule`
- **Notes**:
  - `CS231n` is seeded as `ready`
  - `CS224n` is seeded as `coming_soon`

## 2. CourseOverview

- **Purpose**: Public overview content rendered before learning entry.
- **Core fields**:
  - `course_id`
  - `headline`
  - `subheadline`
  - `summary_markdown`
  - `learning_outcomes`
  - `target_audience`
  - `prerequisites_summary`
  - `estimated_duration_text`
  - `structure_snapshot`
  - `cta_label`
- **Relationships**:
  - Belongs to one `Course`
- **Notes**:
  - May initially be populated from mock values
  - Must still live in the authoritative content layer

## 3. CourseSection

- **Purpose**: Ordered structural grouping inside a course, covering module-, unit-, or chapter-level navigation.
- **Core fields**:
  - `id`
  - `course_id`
  - `parent_section_id` (nullable)
  - `title`
  - `kind` (`module`, `unit`, `lesson_group`, `lecture_group`)
  - `sort_order`
  - `is_entry_section`
- **Relationships**:
  - Belongs to one `Course`
  - May have a parent `CourseSection`
  - Has many `LearningUnit`

## 4. LearningUnit

- **Purpose**: The smallest navigable learning page in the unified course-first experience.
- **Core fields**:
  - `id`
  - `course_id`
  - `section_id`
  - `slug`
  - `title`
  - `unit_type` (`lesson`, `lecture`, `reading`, `practice`)
  - `status` (`ready`, `coming_soon`, `metadata_partial`)
  - `sort_order`
  - `content_source_type`
  - `content_body`
  - `estimated_minutes`
  - `entry_mode` (`text`, `video`, `hybrid`)
- **Relationships**:
  - Belongs to one `Course`
  - Belongs to one `CourseSection`
  - Has many `CourseAsset`
  - Has many `TutorContextBinding`
- **State transitions**:
  - `metadata_partial -> ready` when minimum lecture metadata is complete
  - `ready -> coming_soon` is not expected in normal operation and should be treated as administrative rollback only

## 5. CourseAsset

- **Purpose**: Metadata pointer for server-managed course media and supporting files.
- **Core fields**:
  - `id`
  - `course_id`
  - `learning_unit_id` (nullable)
  - `asset_type` (`video`, `transcript`, `slides`, `thumbnail`, `supplement`)
  - `storage_key`
  - `delivery_url`
  - `availability_status`
  - `metadata_json`
- **Relationships**:
  - Belongs to one `Course`
  - Optionally belongs to one `LearningUnit`
- **Notes**:
  - Binary content lives outside the relational DB
  - Relational rows hold linkage and runtime eligibility metadata

## 6. LearnerAssessmentProfile

- **Purpose**: Tracks whether the learner has completed onboarding and skill-test gating.
- **Core fields**:
  - `user_id`
  - `is_onboarded`
  - `skill_test_completed_at`
  - `assessment_session_id`
  - `recommendation_ready`
- **Relationships**:
  - Belongs to one `User`
  - May reference one assessment result set

## 7. CourseRecommendation

- **Purpose**: Captures recommended course ordering or highlighting after the skill test.
- **Core fields**:
  - `id`
  - `user_id`
  - `course_id`
  - `rank`
  - `reason_summary`
  - `generated_at`
- **Relationships**:
  - Belongs to one `User`
  - Belongs to one `Course`

## 8. LearningProgressRecord

- **Purpose**: Stores server-authoritative learner progress within a course-first structure.
- **Core fields**:
  - `id`
  - `user_id`
  - `course_id`
  - `learning_unit_id`
  - `status` (`not_started`, `in_progress`, `completed`, `blocked`)
  - `last_position_seconds` (nullable)
  - `last_opened_at`
  - `completed_at` (nullable)
- **Relationships**:
  - Belongs to one `User`
  - Belongs to one `Course`
  - Belongs to one `LearningUnit`

## 9. TutorContextBinding

- **Purpose**: Connects a tutor interaction surface to the active learning unit.
- **Core fields**:
  - `id`
  - `learning_unit_id`
  - `context_type`
  - `source_ref`
  - `context_window_rule`
  - `is_active`
- **Relationships**:
  - Belongs to one `LearningUnit`
  - Supports many tutor interactions

## 10. LegacyLectureMapping

- **Purpose**: Transitional mapping from legacy lecture records to unified learning units during migration.
- **Core fields**:
  - `legacy_lecture_id`
  - `learning_unit_id`
  - `course_id`
  - `migration_state`
- **Relationships**:
  - Links one legacy lecture source to one canonical `LearningUnit`
- **Notes**:
  - Required for staged migration of `CS231n`
  - Can be removed after the legacy tutor stack is fully absorbed
