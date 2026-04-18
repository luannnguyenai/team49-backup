# Contract: Course Platform API

## Purpose

Define the runtime contract the frontend will consume for the course-first catalog, overview, learning entry, and lecture experience.

## Principles

- The frontend must fetch runtime data from server-managed endpoints.
- Course availability must be data-driven.
- Legacy tutor endpoints are transitional and must not remain the primary flow.

## 1. Public Course Catalog

### `GET /api/courses`

Returns the public course catalog for home page rendering.

**Query parameters**

- `view` = `all` | `recommended`
- `include_unavailable` = `true` | `false`

**Response shape**

```json
{
  "items": [
    {
      "id": "course_cs231n",
      "slug": "cs231n",
      "title": "CS231n: Deep Learning for Computer Vision",
      "short_description": "Deep learning for computer vision.",
      "status": "ready",
      "cover_image_url": "https://cdn.example/courses/cs231n/cover.jpg",
      "hero_badge": "Available now",
      "is_recommended": true
    },
    {
      "id": "course_cs224n",
      "slug": "cs224n",
      "title": "CS224n: Natural Language Processing with Deep Learning",
      "short_description": "Modern NLP systems and language modeling.",
      "status": "coming_soon",
      "cover_image_url": "https://cdn.example/courses/cs224n/cover.jpg",
      "hero_badge": "Coming soon",
      "is_recommended": false
    }
  ]
}
```

**Rules**

- `view=recommended` is only valid for authenticated learners with completed skill-test status.
- If recommendation data is absent, the response returns an empty recommendation list rather than an error.

## 2. Course Overview

### `GET /api/courses/{course_slug}/overview`

Returns the public overview content for a course.

**Response shape**

```json
{
  "course": {
    "id": "course_cs231n",
    "slug": "cs231n",
    "title": "CS231n: Deep Learning for Computer Vision",
    "status": "ready"
  },
  "overview": {
    "headline": "Learn deep learning for vision systems",
    "subheadline": "From linear classifiers to generative models",
    "summary_markdown": "Course summary...",
    "learning_outcomes": [
      "Build intuition for vision architectures",
      "Understand modern vision pipelines"
    ],
    "target_audience": "Learners with Python and math fundamentals",
    "prerequisites_summary": "Basic Python and machine learning familiarity",
    "estimated_duration_text": "18 lectures"
  },
  "entry": {
    "can_start_learning": true,
    "blocked_reason": null,
    "next_route": "/courses/cs231n/start"
  }
}
```

**Rules**

- `coming_soon` courses must return `can_start_learning=false`.
- Placeholder overview content is valid if contract fields are present.

## 3. Start Learning Decision

### `POST /api/courses/{course_slug}/start`

Returns the next action for the learner after the system applies auth, onboarding, skill-test, and availability rules.

**Response shape**

```json
{
  "decision": "redirect",
  "target": "/login?next=/courses/cs231n/start",
  "reason": "auth_required"
}
```

**Allowed reasons**

- `auth_required`
- `skill_test_required`
- `course_unavailable`
- `learning_ready`

**Rules**

- Course context must be preserved across redirects.
- `course_unavailable` must route back to course overview, not to a blank error page.

## 4. Learning Page Data

### `GET /api/courses/{course_slug}/units/{unit_slug}`

Returns the content and tutor context for a ready learning unit.

**Response shape**

```json
{
  "course": {
    "slug": "cs231n",
    "title": "CS231n: Deep Learning for Computer Vision"
  },
  "unit": {
    "id": "unit_lecture_01",
    "slug": "lecture-1-introduction",
    "title": "Lecture 1: Introduction",
    "unit_type": "lecture",
    "status": "ready",
    "entry_mode": "video"
  },
  "content": {
    "body_markdown": "Optional lecture notes",
    "video_url": "https://cdn.example/cs231n/lecture-1.mp4",
    "transcript_available": true,
    "slides_available": true
  },
  "tutor": {
    "enabled": true,
    "mode": "in_context",
    "context_binding_id": "ctx_lecture_01"
  }
}
```

**Rules**

- `tutor.enabled` must be false when the unit is not learnable.
- The frontend must not query a standalone tutor page to render this experience.

## 5. Legacy Tutor Compatibility

### `GET /tutor`

**Behavior**

- The route no longer acts as a primary product surface.
- If a learner has an active learning context, redirect to that unit.
- Otherwise redirect to the course catalog or a default ready course overview.
