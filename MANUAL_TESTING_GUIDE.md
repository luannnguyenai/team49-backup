# Manual Testing Guide - Onboarding & Assessment Flow

This guide shows how to manually test the onboarding and assessment flow using curl or Postman.

## Prerequisites

1. Start the API server
   ```bash
   cd /Users/binluan/A20-App-049
   uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
   ```

2. Ensure database is set up
   ```bash
   # Run migrations
   alembic upgrade head
   ```

3. Get a test user token (or create one)
   ```bash
   # Register a test user or use existing auth token
   ```

## Test Flow

### Step 1: Set Learning Goals

**Endpoint:** `POST /api/users/me/onboarding/goals`

**Request:**
```bash
curl -X POST http://localhost:8000/api/users/me/onboarding/goals \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "goal_ids": ["nlp"]
  }'
```

**Expected Response (200):**
```json
{
  "goal_ids": ["nlp"],
  "course_ids": ["cs224n"]
}
```

**Validations:**
- ✓ goal_ids contains valid goal (from VALID_GOAL_IDS)
- ✓ course_ids are correctly mapped
- ✓ UserOnboardingProgress is created in DB

---

### Step 2: Get Available Topics

**Endpoint:** `GET /api/onboarding/topics`

**Request:**
```bash
curl -X GET "http://localhost:8000/api/onboarding/topics?goal=nlp&goal=computer_vision" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response (200):**
```json
{
  "courses": [
    {
      "id": "cs224n",
      "title": "NLP with Deep Learning",
      "sections": [
        {
          "id": "section_1",
          "title": "Fundamentals",
          "units": [
            {
              "id": "unit_uuid",
              "title": "Word Embeddings",
              "canonical_unit_id": "word_embeddings_canonical"
            }
          ]
        }
      ]
    }
  ]
}
```

**Validations:**
- ✓ Response has hierarchical structure (courses → sections → units)
- ✓ Units have canonical_unit_id for placement assessment
- ✓ Topics are filtered by requested goals

---

### Step 3: Mark Known Topics

**Endpoint:** `POST /api/users/me/onboarding/known-topics`

**Request:**
```bash
curl -X POST http://localhost:8000/api/users/me/onboarding/known-topics \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "topic_unit_ids": ["unit_uuid_1", "unit_uuid_2"]
  }'
```

**Expected Response (200):**
```json
{
  "marked_as_known": ["unit_uuid_1", "unit_uuid_2"],
  "total_topics": 15
}
```

**Validations:**
- ✓ topic_unit_ids are valid UUIDs
- ✓ Topics are marked in UserOnboardingProgress
- ✓ Empty list is acceptable (user knows no topics)

---

### Step 4: Set Experience Level

**Endpoint:** `POST /api/users/me/onboarding/experience-level`

**Request:**
```bash
curl -X POST http://localhost:8000/api/users/me/onboarding/experience-level \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "level": "intermediate"
  }'
```

**Expected Response (200):**
```json
{
  "level": "intermediate"
}
```

**Valid Levels:** `"beginner"`, `"intermediate"`, `"advanced"`

**Validations:**
- ✓ level is one of the valid options
- ✓ UserOnboardingProgress is updated with experience_level

---

### Step 5: Start Placement Assessment

**Endpoint:** `POST /api/placement-assessment/start`

**Request:**
```bash
curl -X POST http://localhost:8000/api/placement-assessment/start \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "topic_unit_ids": ["unit_uuid_1", "unit_uuid_2"]
  }'
```

**Expected Response (200):**
```json
{
  "session_id": "session_uuid",
  "total_questions": 10,
  "should_skip_step": false,
  "questions": [
    {
      "item_id": "item_123",
      "canonical_unit_id": "canonical_unit_123",
      "topic_unit_id": "topic_unit_1",
      "stem_text": "What is a word embedding?",
      "option_a": "A vector representation of a word",
      "option_b": "A type of neural network",
      "option_c": "A database of words",
      "option_d": "A language model"
    },
    // ... more questions (5 per topic: 1 easy, 2 medium, 2 hard)
  ],
  "topic_unit_ids": ["unit_uuid_1", "unit_uuid_2"],
  "skipped_topics": []
}
```

**Validations:**
- ✓ Questions are returned (5 per topic with difficulty distribution)
- ✓ Session is created in DB
- ✓ If no placement items: `should_skip_step=true`
- ✓ If all topics skipped: `topic_unit_ids=[]`

**Common Scenarios:**
- If topic has no placement items → topic is in `skipped_topics`
- If all topics have no items → `should_skip_step=true`, frontend skips assessment
- Each question has 4 options (A, B, C, D)

---

### Step 6: Submit Placement Answers

**Endpoint:** `POST /api/placement-assessment/submit`

**Request:**
```bash
curl -X POST http://localhost:8000/api/placement-assessment/submit \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "session_id": "session_uuid",
    "answers": [
      {
        "item_id": "item_123",
        "topic_unit_id": "topic_unit_1",
        "selected_answer": "A"
      },
      {
        "item_id": "item_124",
        "topic_unit_id": "topic_unit_1",
        "selected_answer": "B"
      },
      // ... all questions must have answers
    ]
  }'
```

**Expected Response (200):**
```json
{
  "session_id": "session_uuid",
  "topic_decisions": [
    {
      "topic_unit_id": "topic_unit_1",
      "score_pct": 60.0,
      "decision": "review",
      "user_choice": null
    },
    {
      "topic_unit_id": "topic_unit_2",
      "score_pct": 80.0,
      "decision": "skip",
      "user_choice": null
    }
  ],
  "skipped_count": 1,
  "review_count": 1,
  "relearn_count": 0
}
```

**Decision Logic:**
- score >= 70% → decision = "skip"
- 50% <= score < 70% → decision = "review"
- score < 50% → decision = "relearn"

**Validations:**
- ✓ Answer count must match question count
- ✓ Selected answer must be "A", "B", "C", or "D"
- ✓ Session must exist and belong to user
- ✓ Session must not already be submitted
- ✓ Score is calculated correctly: correct_count / total_questions * 100
- ✓ Decisions are classified correctly per topic

---

### Step 7: Get Placement Results

**Endpoint:** `GET /api/placement-assessment/results`

**Request:**
```bash
curl -X GET http://localhost:8000/api/placement-assessment/results \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response (200):**
```json
{
  "results": [
    {
      "topic_unit_id": "topic_unit_1",
      "score_pct": 60.0,
      "decision": "review",
      "user_choice": null
    },
    {
      "topic_unit_id": "topic_unit_2",
      "score_pct": 80.0,
      "decision": "skip",
      "user_choice": null
    }
  ],
  "has_placement": true
}
```

**Validations:**
- ✓ Returns all placement decisions for user
- ✓ has_placement=false if no placement results exist
- ✓ Only returns "review" decisions if user hasn't chosen yet

---

### Step 8: Override Placement Decision

**Endpoint:** `PATCH /api/placement-assessment/topic-decision`

**Request:**
```bash
curl -X PATCH http://localhost:8000/api/placement-assessment/topic-decision \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "topic_unit_id": "topic_unit_1",
    "user_choice": "skip"
  }'
```

**Expected Response (200):**
```json
{
  "topic_unit_id": "topic_unit_1",
  "score_pct": 60.0,
  "decision": "review",
  "user_choice": "skip"
}
```

**Valid user_choice values:** `"skip"`, `"review"`, `"relearn"`

**Validations:**
- ✓ Only allowed for decisions in "review" state
- ✓ Cannot override "skip" or "relearn" decisions
- ✓ user_choice is stored in database
- ✓ Returns 404 if no reviewable result exists

---

## Test Scenarios

### Scenario 1: Good Student (80%+ on all)
```bash
# All answers correct → decision = "skip"
# Result: User can skip these topics
```

### Scenario 2: Average Student (50-70%)
```bash
# Some correct, some wrong → decision = "review"
# User can choose to skip or relearn
# Using PATCH /api/placement-assessment/topic-decision
```

### Scenario 3: Struggling Student (<50%)
```bash
# Mostly wrong → decision = "relearn"
# User must complete these topics (no override option)
```

### Scenario 4: Mixed Results
```bash
# Topic 1: 90% → skip
# Topic 2: 60% → review (user can override)
# Topic 3: 30% → relearn (must complete)
```

### Scenario 5: No Placement Items
```bash
# Topic has no placement questions
# Response: should_skip_step=true
# Frontend skips this step entirely
```

---

## Error Scenarios

### Error: Invalid Goal
```bash
curl -X POST http://localhost:8000/api/users/me/onboarding/goals \
  -d '{"goal_ids": ["not_a_real_goal"]}'

# Response (422):
# {"detail": [{"msg": "Input should be 'nlp', 'deep_learning', ..."}]}
```

### Error: Session Already Submitted
```bash
# Submit answers twice for same session
curl -X POST http://localhost:8000/api/placement-assessment/submit \
  -d '{"session_id": "...", "answers": [...]}'

# Second request:
# Response (409):
# {"detail": "Placement assessment session already submitted."}
```

### Error: Session Ownership
```bash
# Submit answers for another user's session
# Response (422):
# {"detail": "Session not found or does not belong to this user."}
```

### Error: Invalid UUID
```bash
curl -X POST http://localhost:8000/api/users/me/onboarding/known-topics \
  -d '{"topic_unit_ids": ["not-a-uuid"]}'

# Response (422):
# {"detail": [{"msg": "Input should be a valid UUID..."}]}
```

---

## Quick Test Command

Run a complete flow with a single topic:

```bash
#!/bin/bash
set -e

# Configuration
API="http://localhost:8000"
TOKEN="your_bearer_token"
UNIT_ID="your_unit_uuid"

# Step 1: Set goals
echo "1. Setting goals..."
curl -s -X POST $API/api/users/me/onboarding/goals \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"goal_ids": ["nlp"]}' | jq .

# Step 2: Get topics
echo "2. Getting topics..."
curl -s -X GET "$API/api/onboarding/topics?goal=nlp" \
  -H "Authorization: Bearer $TOKEN" | jq .

# Step 3: Mark known topics
echo "3. Marking known topics..."
curl -s -X POST $API/api/users/me/onboarding/known-topics \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"topic_unit_ids\": [\"$UNIT_ID\"]}" | jq .

# Step 4: Set experience level
echo "4. Setting experience level..."
curl -s -X POST $API/api/users/me/onboarding/experience-level \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"level": "intermediate"}' | jq .

# Step 5: Start placement
echo "5. Starting placement assessment..."
SESSION_RESP=$(curl -s -X POST $API/api/placement-assessment/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"topic_unit_ids\": [\"$UNIT_ID\"]}")
SESSION_ID=$(echo $SESSION_RESP | jq -r '.session_id')
echo $SESSION_RESP | jq .

# Step 6: Submit answers
echo "6. Submitting answers..."
QUESTIONS=$(echo $SESSION_RESP | jq '.questions')
ANSWERS=$(echo $QUESTIONS | jq -c '[.[] | {item_id, topic_unit_id, selected_answer: "A"}]')
curl -s -X POST $API/api/placement-assessment/submit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\", \"answers\": $ANSWERS}" | jq .

# Step 7: Get results
echo "7. Getting placement results..."
curl -s -X GET $API/api/placement-assessment/results \
  -H "Authorization: Bearer $TOKEN" | jq .

echo "✓ Complete flow tested"
```

---

## Debugging Tips

### Check if Questions have Items
```bash
# Check if database has placement items for a unit
sqlite3 app.db << EOF
SELECT COUNT(*) as placement_items 
FROM canonical_items 
WHERE canonical_unit_id = 'unit_id' AND phase = 'placement';
EOF
```

### View User's Assessment Session
```bash
# Check session in database
sqlite3 app.db << EOF
SELECT id, user_id, total_questions, correct_count, completed_at 
FROM sessions 
WHERE user_id = 'user_id' 
ORDER BY created_at DESC LIMIT 5;
EOF
```

### View Placement Results
```bash
# Check placement assessment results
sqlite3 app.db << EOF
SELECT user_id, topic_unit_id, score_pct, decision, user_choice 
FROM placement_assessment_results 
WHERE user_id = 'user_id';
EOF
```

---

## Checklist

- [ ] API server starts without errors
- [ ] Database migrations applied (alembic upgrade head)
- [ ] Can set learning goals
- [ ] Can retrieve topics for goals
- [ ] Can mark topics as known
- [ ] Can set experience level
- [ ] Can start placement assessment (has questions)
- [ ] Can submit answers
- [ ] Scores calculated correctly
- [ ] Decisions classified correctly
- [ ] Can view placement results
- [ ] Can override "review" decisions
- [ ] All error cases handled properly
