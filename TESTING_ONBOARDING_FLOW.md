# Onboarding & Assessment Flow Testing Guide

## Overview

This document describes the complete onboarding flow testing suite for the A20-App-049 project. The tests verify the entire user journey from goal selection through placement assessment completion.

## Onboarding Flow Steps

```
1. Set Learning Goals
   └─> Save user's selected learning goals (e.g., "nlp", "computer_vision")
   └─> Maps goals to courses
   └─> Stores in UserOnboardingProgress

2. Get Available Topics
   └─> Retrieve topic tree for selected goals
   └─> Returns hierarchical structure: Course → Section → Unit

3. Mark Known Topics
   └─> User marks topics they already know
   └─> Skips those topics in placement assessment

4. Set Experience Level
   └─> User specifies their experience level ("beginner", "intermediate", "advanced")
   └─> Stored in UserOnboardingProgress

5. Start Placement Assessment
   └─> For each selected topic unit:
       └─> Query placement items (difficulty: easy, medium, hard)
       └─> Select 5 items using bucket distribution (1 easy, 2 medium, 2 hard)
       └─> Create assessment session

6. Submit Placement Answers
   └─> User answers all questions
   └─> Score: correct_count / total_questions
   └─> Decision per topic:
       └─> score >= 70%  → "skip" (user can skip this topic)
       └─> 50% <= score < 70% → "review" (user can review or relearn)
       └─> score < 50%  → "relearn" (user must relearn the topic)

7. View Placement Results
   └─> User sees placement decisions per topic
   └─> Can override decisions if in "review" state
```

## Test Files

### 1. `tests/test_placement_assessment_router.py`
**Purpose:** Verify router registration and endpoint availability

**Tests:**
- ✓ Router is importable
- ✓ Router has 4 endpoints: `/start`, `/submit`, `/results`, `/topic-decision`
- ✓ Router is registered in the FastAPI app

**Run:**
```bash
python3 -m pytest tests/test_placement_assessment_router.py -v
```

### 2. `tests/test_onboarding_endpoints.py`
**Purpose:** Verify onboarding schema validation and service logic

**Tests:**
- ✓ GoalsRequest schema validation (valid/invalid goals)
- ✓ KnownTopicsRequest schema validation (UUID format)
- ✓ GoalsResponse schema (round-trip serialization)
- ✓ TopicsResponse schema (nested structure)
- ✓ Goal-to-course mapping derivation

**Run:**
```bash
python3 -m pytest tests/test_onboarding_endpoints.py -v
```

### 3. `tests/integration/test_onboarding_flow_e2e.py`
**Purpose:** End-to-end integration tests with real database

**Tests:**
- ✓ `test_onboarding_flow_step1_set_goals` - User sets learning goals
- ✓ `test_onboarding_flow_step2_get_topics` - User retrieves topic tree
- ✓ `test_onboarding_flow_step3_set_known_topics` - User marks known topics
- ✓ `test_onboarding_flow_step4_set_experience_level` - User sets experience
- ✓ `test_onboarding_flow_step5_start_placement_assessment` - Start assessment
- ✓ `test_onboarding_flow_step6_submit_placement_answers` - Submit answers
- ✓ `test_onboarding_flow_complete_journey` - Full journey (all steps)
- ✓ `test_placement_assessment_with_mixed_answers` - Correct & incorrect answers

**Run:**
```bash
python3 -m pytest tests/integration/test_onboarding_flow_e2e.py -v
```

### 4. `tests/services/test_placement_assessment_service.py`
**Purpose:** Service logic tests

**Covers:**
- Item selection logic (bucketing)
- Score calculation
- Decision classification

**Run:**
```bash
python3 -m pytest tests/services/test_placement_assessment_service.py -v
```

### 5. `tests/repositories/test_placement_assessment_repo.py`
**Purpose:** Repository/database tests

**Covers:**
- Query builders
- Data persistence
- Upsert operations

**Run:**
```bash
python3 -m pytest tests/repositories/test_placement_assessment_repo.py -v
```

## Running All Tests

### Option 1: Individual test files
```bash
cd /Users/binluan/A20-App-049

# Test routing
python3 -m pytest tests/test_placement_assessment_router.py -v

# Test schemas & service
python3 -m pytest tests/test_onboarding_endpoints.py -v

# Test E2E flow (requires DB)
python3 -m pytest tests/integration/test_onboarding_flow_e2e.py -v --tb=short
```

### Option 2: Run all with our test runner
```bash
bash /Users/binluan/A20-App-049/test_onboarding_runner.sh
```

### Option 3: Run with pytest directly
```bash
cd /Users/binluan/A20-App-049

# All tests
python3 -m pytest tests/ -v

# Only onboarding-related
python3 -m pytest tests/ -k "onboarding or placement" -v

# With coverage
python3 -m pytest tests/integration/test_onboarding_flow_e2e.py -v --cov=src --cov-report=term-missing
```

## Key Data Models

### Session
- Tracks user assessment session
- Fields: `id`, `user_id`, `session_type`, `canonical_phase`, `total_questions`, `correct_count`, `score_percent`, `completed_at`

### UserOnboardingProgress
- Tracks user's onboarding state
- Fields: `user_id`, `selected_goals`, `marked_topics`, `experience_level`, `last_updated`

### PlacementAssessmentResult
- Stores placement decision per topic
- Fields: `user_id`, `topic_unit_id`, `score_pct`, `decision` ("skip"/"review"/"relearn"), `raw_answers`

### QuestionBankItem
- Canonical questions with difficulty
- Fields: `item_id`, `question`, `choices`, `answer_index`, `difficulty_prior`, `unit_id`, `phase`

## Expected Behavior

### Happy Path
1. User selects goals (e.g., "nlp")
2. System maps to courses (cs224n)
3. User views topics tree
4. User marks known topics (optional)
5. User sets experience level
6. System starts placement assessment with 5 questions per topic
7. User answers all questions
8. System scores: e.g., 3/5 = 60% → "review" decision
9. User can accept or override decision
10. Placement complete ✓

### Edge Cases
1. **No placement items for topic**
   - System skips that topic automatically
   - `should_skip_step=True` returned

2. **User answers all questions correctly**
   - Score = 100% → Decision = "skip"
   - User can skip this topic in curriculum

3. **User answers all questions incorrectly**
   - Score = 0% → Decision = "relearn"
   - User must complete this topic

4. **User has known topics**
   - Placement assessment excludes those topics
   - Those topics are marked as "skip"

5. **Duplicate submission**
   - System rejects if session already completed
   - Error: "Placement assessment session already submitted"

## Assessment Item Selection Logic

### Bucket Distribution
For each topic, selects 5 questions:
- **1 Easy**: difficulty_prior ≤ -0.5
- **2 Medium**: -0.5 < difficulty_prior ≤ 0.5 (None treated as medium)
- **2 Hard**: difficulty_prior > 0.5

### Fallback Rules
If a bucket has fewer items than needed:
1. Fill remaining slots from other buckets (in order)
2. If insufficient items across all buckets, select any available
3. If no items available for topic, skip that topic

## Debugging Failed Tests

### Check database connectivity
```bash
python3 -c "
from src.database import get_async_engine
import asyncio
asyncio.run(get_async_engine().connect())
print('✓ Database connection OK')
"
```

### Check test data availability
```bash
python3 -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.config import Settings
from sqlalchemy import select
from src.models.course import LearningUnit

async def check():
    settings = Settings()
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession)
    async with async_session() as db:
        result = await db.execute(select(LearningUnit).limit(5))
        units = result.scalars().all()
        print(f'Found {len(units)} learning units')
        for u in units:
            print(f'  - {u.id}: {u.title} (canonical: {u.canonical_unit_id})')

asyncio.run(check())
"
```

### View placement items for a unit
```bash
python3 -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.config import Settings
from sqlalchemy import select
from src.models.course import LearningUnit
from src.repositories.canonical_question_repo import CanonicalQuestionRepository

async def check():
    settings = Settings()
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession)
    async with async_session() as db:
        unit = await db.execute(
            select(LearningUnit)
            .where(LearningUnit.canonical_unit_id.isnot(None))
            .limit(1)
        )
        unit = unit.scalar_one_or_none()
        if unit:
            repo = CanonicalQuestionRepository(db)
            items = await repo.get_items_for_placement_bucketed(
                canonical_unit_ids=[unit.canonical_unit_id],
                phase='placement'
            )
            print(f'Found {len(items)} placement items for unit {unit.id}')
            easy = sum(1 for _, d in items if d and d <= -0.5)
            med = sum(1 for _, d in items if d is None or -0.5 < d <= 0.5)
            hard = sum(1 for _, d in items if d and d > 0.5)
            print(f'  Easy: {easy}, Medium: {med}, Hard: {hard}')

asyncio.run(check())
"
```

## Test Status Summary

| Test File | Status | Notes |
|-----------|--------|-------|
| test_placement_assessment_router.py | ✓ Ready | Basic routing tests |
| test_onboarding_endpoints.py | ✓ Ready | Schema validation tests |
| test_onboarding_flow_e2e.py | ✓ Ready | Full integration tests (NEW) |
| services/test_placement_assessment_service.py | ✓ Exists | Service logic tests |
| repositories/test_placement_assessment_repo.py | ✓ Exists | Repository tests |

## Next Steps

1. Run basic routing tests
   ```bash
   python3 -m pytest tests/test_placement_assessment_router.py -v
   ```

2. Run schema validation tests
   ```bash
   python3 -m pytest tests/test_onboarding_endpoints.py -v
   ```

3. Run full E2E integration tests
   ```bash
   python3 -m pytest tests/integration/test_onboarding_flow_e2e.py::test_onboarding_flow_complete_journey -v --tb=short
   ```

4. Run all tests together
   ```bash
   python3 -m pytest tests/ -v --tb=short
   ```
