# Assessment Flow - Visual Guide & Technical Reference

**Last Updated:** 2026-04-27

---

## 🎯 Complete Assessment Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     USER ONBOARDING & ASSESSMENT FLOW                    │
└──────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: GOAL & TOPIC DISCOVERY                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Step 1: Select Learning Goals                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ POST /api/users/me/onboarding/goals                            │   │
│  │ Input:  goal_ids = ["nlp"]                                     │   │
│  │ Output: goal_ids=["nlp"], course_ids=["cs224n"]               │   │
│  │ Database: UserOnboardingProgress created                       │   │
│  │ Test: test_onboarding_flow_step1_set_goals ✅                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                                    ▼                                     │
│  Step 2: Get Available Topics                                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ GET /api/onboarding/topics?goal=nlp                            │   │
│  │ Output: Hierarchical structure:                                 │   │
│  │   courses[]                                                    │   │
│  │   └─ sections[]                                                │   │
│  │      └─ units[]                                                │   │
│  │            ├─ id: uuid                                         │   │
│  │            ├─ title: string                                    │   │
│  │            └─ canonical_unit_id: string                        │   │
│  │ Test: test_onboarding_flow_step2_get_topics ✅                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                                    ▼                                     │
│  Step 3: Mark Topics User Knows (Optional)                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ POST /api/users/me/onboarding/known-topics                    │   │
│  │ Input:  topic_unit_ids = [uuid1, uuid2]                       │   │
│  │ Output: marked_as_known = [uuid1, uuid2]                      │   │
│  │ Effect: Skip assessment for these topics                       │   │
│  │ Test: test_onboarding_flow_step3_set_known_topics ✅          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                                    ▼                                     │
│  Step 4: Set Experience Level                                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ POST /api/users/me/onboarding/experience-level                │   │
│  │ Input:  level = "beginner" | "intermediate" | "advanced"     │   │
│  │ Output: level stored in UserOnboardingProgress                │   │
│  │ Test: test_onboarding_flow_step4_set_experience_level ✅     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: PLACEMENT ASSESSMENT                                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Step 5: Start Assessment (Per Topic)                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ POST /api/placement-assessment/start                          │   │
│  │ Input:  topic_unit_ids = [uuid1, uuid2]                       │   │
│  │                                                                │   │
│  │ Processing:                                                    │   │
│  │   For each topic:                                              │   │
│  │   1. Query canonical items for topic (phase="placement")      │   │
│  │   2. Classify by difficulty:                                  │   │
│  │      - Easy:   difficulty_prior ≤ -0.5      (1 item)         │   │
│  │      - Medium: -0.5 < difficulty ≤ 0.5      (2 items)        │   │
│  │      - Hard:   difficulty_prior > 0.5       (2 items)        │   │
│  │   3. Select 5 items total (1-2-2 distribution)               │   │
│  │                                                                │   │
│  │ Output:                                                        │   │
│  │   {                                                            │   │
│  │     "session_id": "uuid",                                     │   │
│  │     "total_questions": 10,  (5 per topic)                     │   │
│  │     "questions": [                                            │   │
│  │       {                                                        │   │
│  │         "item_id": "item_123",                               │   │
│  │         "stem_text": "What is...",                          │   │
│  │         "option_a": "...",                                   │   │
│  │         "option_b": "...",                                   │   │
│  │         "option_c": "...",                                   │   │
│  │         "option_d": "..."                                    │   │
│  │       }                                                        │   │
│  │     ],                                                         │   │
│  │     "topic_unit_ids": [uuid1, uuid2],                       │   │
│  │     "skipped_topics": [],                                     │   │
│  │     "should_skip_step": false                                │   │
│  │   }                                                            │   │
│  │                                                                │   │
│  │ Database: Session created with total_questions=10             │   │
│  │ Test: test_onboarding_flow_step5_start_placement ✅          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                                    ▼                                     │
│  Step 6: User Answers Questions                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ User selects answers (A/B/C/D) for all 10 questions           │   │
│  │ Frontend stores answers in form/state                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                                    ▼                                     │
│  Step 7: Submit Assessment Answers                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ POST /api/placement-assessment/submit                         │   │
│  │ Input:                                                         │   │
│  │   {                                                            │   │
│  │     "session_id": "uuid",                                     │   │
│  │     "answers": [                                              │   │
│  │       {                                                        │   │
│  │         "item_id": "item_123",                               │   │
│  │         "topic_unit_id": "topic_1",                          │   │
│  │         "selected_answer": "A"                               │   │
│  │       }                                                        │   │
│  │     ]                                                          │   │
│  │   }                                                            │   │
│  │                                                                │   │
│  │ Processing Per Topic:                                          │   │
│  │   1. Count correct answers (match item.answer_index)          │   │
│  │   2. Calculate score: (correct / total) * 100                │   │
│  │   3. Classify decision:                                       │   │
│  │      └─ score ≥ 70%       → "skip"   (user can skip)         │   │
│  │      └─ 50% ≤ score < 70% → "review" (user can choose)      │   │
│  │      └─ score < 50%       → "relearn"(user must relearn)    │   │
│  │                                                                │   │
│  │ Output:                                                        │   │
│  │   {                                                            │   │
│  │     "session_id": "uuid",                                     │   │
│  │     "topic_decisions": [                                      │   │
│  │       {                                                        │   │
│  │         "topic_unit_id": "topic_1",                          │   │
│  │         "score_pct": 60.0,                                    │   │
│  │         "decision": "review",                                 │   │
│  │         "user_choice": null                                   │   │
│  │       }                                                        │   │
│  │     ],                                                         │   │
│  │     "skipped_count": 1,                                        │   │
│  │     "review_count": 1,                                         │   │
│  │     "relearn_count": 0                                         │   │
│  │   }                                                            │   │
│  │                                                                │   │
│  │ Database: Session marked completed, results stored            │   │
│  │ Test: test_onboarding_flow_step6_submit_placement ✅         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: RESULTS & DECISIONS                                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Step 8: View Placement Results                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ GET /api/placement-assessment/results                         │   │
│  │ Output:                                                        │   │
│  │   {                                                            │   │
│  │     "results": [                                              │   │
│  │       {                                                        │   │
│  │         "topic_unit_id": "topic_1",                          │   │
│  │         "score_pct": 60.0,                                    │   │
│  │         "decision": "review",                                 │   │
│  │         "user_choice": null  (null until user decides)       │   │
│  │       }                                                        │   │
│  │     ],                                                         │   │
│  │     "has_placement": true                                      │   │
│  │   }                                                            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                    ┌───────────────┼───────────────┐                    │
│                    │               │               │                    │
│                    ▼               ▼               ▼                    │
│               (SKIP)           (REVIEW)       (RELEARN)                 │
│          Score ≥ 70%       50% ≤ Score       Score < 50%              │
│                           ≤ 70%                                         │
│          ✅ Auto-skip       ⚠️ User choice    ❌ Must relearn          │
│          (No action)       (Can override)    (No choice)               │
│                                  │                                      │
│                                  ▼                                      │
│              Step 9: User Overrides Decision (Optional)                 │
│              ┌─────────────────────────────────────────────┐           │
│              │ PATCH /api/placement-assessment/topic-decision│         │
│              │ Only available for "review" decisions       │           │
│              │ Input:  {                                   │           │
│              │   "topic_unit_id": "topic_1",              │           │
│              │   "user_choice": "skip" | "relearn"        │           │
│              │ }                                            │           │
│              │ Output: TopicDecision{..., user_choice}    │           │
│              └─────────────────────────────────────────────┘           │
│                                    │                                     │
│                                    ▼                                     │
│                          ✅ ASSESSMENT COMPLETE                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🧮 Scoring & Decision Logic Flowchart

```
┌─────────────────────────────────────────────────────────────────┐
│ SCORING CALCULATION                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User submits 5 answers for a topic:                           │
│  ┌──────┬──────┬──────┬──────┬──────┐                          │
│  │Ans 1 │Ans 2 │Ans 3 │Ans 4 │Ans 5 │                          │
│  │  A   │  B   │  C   │  B   │  D   │                          │
│  └──────┴──────┴──────┴──────┴──────┘                          │
│     │      │      │      │      │                               │
│     ▼      ▼      ▼      ▼      ▼                               │
│  (Correct)(Correct)(Wrong)(Correct)(Wrong)                     │
│                                                                 │
│  Correct Count = 3                                              │
│  Total Count   = 5                                              │
│                                                                 │
│  Score = (3 / 5) * 100 = 60%                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│ DECISION CLASSIFICATION                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│        Score = 60%                                              │
│           │                                                     │
│        ┌──┼──┐                                                   │
│        │  │  │                                                   │
│        ▼  ▼  ▼                                                   │
│    ┌─────────────────────────────────────┐                      │
│    │   Is score ≥ 70% ?                  │                      │
│    │   60 ≥ 70 ?  → NO                   │                      │
│    └──────────┬──────────────────────────┘                      │
│               │                                                  │
│               ▼                                                  │
│    ┌─────────────────────────────────────┐                      │
│    │   Is score ≥ 50% AND < 70% ?       │                      │
│    │   50 ≤ 60 < 70 ?  → YES            │                      │
│    └──────────┬──────────────────────────┘                      │
│               │                                                  │
│               ▼                                                  │
│    ┌─────────────────────────────────────┐                      │
│    │   DECISION = "review" ⚠️            │                      │
│    │   User can choose to skip or relearn│                      │
│    └─────────────────────────────────────┘                      │
│                                                                 │
│  Other Paths:                                                   │
│  • Score ≥ 70% → "skip" (auto-approved) ✅                    │
│  • Score < 50%  → "relearn" (no choice) ❌                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Item Selection Logic (Bucketing)

```
┌──────────────────────────────────────────────────────────────────┐
│ ITEM BUCKETING FOR ASSESSMENT                                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Available Items (from database):                               │
│  ┌────────────────────────────────────────────┐                │
│  │ ID │ Question        │ Difficulty │ Bucket │                │
│  ├────────────────────────────────────────────┤                │
│  │ 1  │ What is NLP?    │ -0.8       │ EASY   │                │
│  │ 2  │ RNN tutorial    │ -0.3       │ MEDIUM │                │
│  │ 3  │ LSTM advanced   │ 0.2        │ MEDIUM │                │
│  │ 4  │ Transformers    │ 0.7        │ HARD   │                │
│  │ 5  │ BERT details    │ 1.1        │ HARD   │                │
│  │ 6  │ Embeddings      │ -0.5       │ MEDIUM │                │
│  │ 7  │ Advanced MBERT  │ 1.5        │ HARD   │                │
│  └────────────────────────────────────────────┘                │
│                                                                  │
│  Difficulty Thresholds:                                         │
│  • EASY:   difficulty_prior ≤ -0.5                            │
│  • MEDIUM: -0.5 < difficulty_prior ≤ 0.5 (or NULL)           │
│  • HARD:   difficulty_prior > 0.5                             │
│                                                                  │
│  Bucketing Result:                                              │
│  ┌──────────────────────────────────────────┐                 │
│  │ Easy:   [Item 1]                 (1)     │                 │
│  │ Medium: [Item 2, 3, 6]           (3)     │                 │
│  │ Hard:   [Item 4, 5, 7]           (3)     │                 │
│  └──────────────────────────────────────────┘                 │
│                                                                  │
│  Selection (for 5 questions):                                   │
│  ┌──────────────────────────────────────────┐                 │
│  │ 1 EASY:    Item 1                        │                 │
│  │ 2 MEDIUM:  Items 2, 3 (random choice)   │                 │
│  │ 2 HARD:    Items 4, 5 (random choice)   │                 │
│  └──────────────────────────────────────────┘                 │
│                                                                  │
│  Final Assessment Set: [Item 1, Item 2, Item 3, Item 4, Item 5] │
│                                                                  │
│  Distribution: ✅ 1 EASY, 2 MEDIUM, 2 HARD (1-2-2)           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📋 Database Schema Relations

```
┌──────────────────────────┐
│   UserOnboardingProgress │
├──────────────────────────┤
│ user_id (PK, FK)         │
│ selected_goals           │
│ marked_topics            │
│ experience_level         │
│ last_updated             │
└──────────────────────────┘
         │
         ▼
┌──────────────────────────┐
│   Session                │
├──────────────────────────┤
│ id (PK)                  │
│ user_id (FK)             │
│ session_type             │
│ canonical_phase          │
│ total_questions          │
│ correct_count            │
│ score_percent            │
│ completed_at             │
└──────────────────────────┘
         │
         ├─────────────────────────────────┐
         │                                 │
         ▼                                 ▼
    ┌─────────────────────┐         ┌──────────────────┐
    │  Interaction        │         │  PlacementResult │
    ├─────────────────────┤         ├──────────────────┤
    │ id (PK)             │         │ user_id (PK, FK) │
    │ session_id (FK)     │         │ topic_unit_id(PK)│
    │ item_id             │         │ score_pct        │
    │ is_correct          │         │ decision         │
    │ timestamp           │         │ user_choice      │
    │ answer_text         │         │ raw_answers      │
    └─────────────────────┘         └──────────────────┘
         │
         ▼
    ┌──────────────────────────────┐
    │   QuestionBankItem           │
    ├──────────────────────────────┤
    │ item_id (PK)                 │
    │ question                     │
    │ choices                      │
    │ answer_index                 │
    │ difficulty_prior             │
    │ unit_id (FK)                 │
    │ phase (placement|practice)   │
    └──────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────┐
    │   LearningUnit               │
    ├──────────────────────────────┤
    │ id (PK)                      │
    │ canonical_unit_id (FK)       │
    │ title                        │
    │ description                  │
    └──────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────┐
    │   CanonicalUnit              │
    ├──────────────────────────────┤
    │ id (PK)                      │
    │ name                         │
    │ parent_id (self-ref)         │
    └──────────────────────────────┘
```

---

## 🔀 Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│  (React/Next.js Components)                                      │
└──────────────────────────────────────────────────────────────────┘
   │                  │                     │                  │
   │ 1. Set Goals     │ 2. Get Topics       │ 5. Start         │ 6. Submit
   │    (POST)        │    (GET)            │ Assessment       │    Answers
   │                  │                     │    (POST)        │    (POST)
   ▼                  ▼                     ▼                  ▼
┌──────────────────────────────────────────────────────────────────┐
│                     FASTAPI ROUTERS                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ onboarding_router:                                       │   │
│  │  POST   /api/users/me/onboarding/goals                  │   │
│  │  GET    /api/onboarding/topics                          │   │
│  │  POST   /api/users/me/onboarding/known-topics           │   │
│  │  POST   /api/users/me/onboarding/experience-level      │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ placement_assessment_router:                             │   │
│  │  POST   /api/placement-assessment/start                 │   │
│  │  POST   /api/placement-assessment/submit                │   │
│  │  GET    /api/placement-assessment/results               │   │
│  │  PATCH  /api/placement-assessment/topic-decision        │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
   │                  │                     │                  │
   ▼                  ▼                     ▼                  ▼
┌──────────────────────────────────────────────────────────────────┐
│                     BUSINESS LOGIC SERVICES                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ onboarding_service:                                      │   │
│  │  • save_user_goals()                                     │   │
│  │  • get_topics_tree()                                     │   │
│  │  • save_known_topics()                                   │   │
│  │  • save_experience_level()                               │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ placement_assessment_service:                            │   │
│  │  • start_placement_assessment()                          │   │
│  │  • _bucket_select_5()  [1-2-2 distribution]             │   │
│  │  • _classify_decision() [score logic]                    │   │
│  │  • submit_placement_assessment()                         │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
   │                  │                     │                  │
   ▼                  ▼                     ▼                  ▼
┌──────────────────────────────────────────────────────────────────┐
│                  DATA ACCESS REPOSITORIES                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ canonical_question_repo:                                 │   │
│  │  • get_items_for_placement_bucketed()                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ placement_assessment_repo:                               │   │
│  │  • upsert()                                              │   │
│  │  • get_by_user_id()                                      │   │
│  │  • get_by_user_and_unit()                                │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
   │                  │                     │                  │
   ▼                  ▼                     ▼                  ▼
┌──────────────────────────────────────────────────────────────────┐
│                      DATABASE (PostgreSQL)                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Tables:                                                  │   │
│  │  • users                                                 │   │
│  │  • user_onboarding_progress                             │   │
│  │  • learning_units                                        │   │
│  │  • canonical_units                                       │   │
│  │  • question_bank (canonical items)                       │   │
│  │  • sessions                                              │   │
│  │  • interactions                                          │   │
│  │  • placement_assessment_results                          │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📈 Score Distribution Examples

```
┌────────────────────────────────────────────────────────────────┐
│ EXAMPLE 1: HIGH PERFORMER (80% score)                          │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Items: [Q1, Q2, Q3, Q4, Q5]                                 │
│  Answers: [✓, ✓, ✓, ✓, ✗]                                   │
│  Correct: 4 / 5 = 80%                                         │
│                                                                │
│  Decision: "skip" ✅                                           │
│  Reason: score ≥ 70%                                           │
│  Action: User can skip this topic                             │
│                                                                │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│ EXAMPLE 2: AVERAGE PERFORMER (60% score)                       │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Items: [Q1, Q2, Q3, Q4, Q5]                                 │
│  Answers: [✓, ✓, ✓, ✗, ✗]                                   │
│  Correct: 3 / 5 = 60%                                         │
│                                                                │
│  Decision: "review" ⚠️                                        │
│  Reason: 50% ≤ score < 70%                                    │
│  Action: User can choose to:                                  │
│    □ Skip (confident)                                         │
│    □ Relearn (needs review)                                   │
│                                                                │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│ EXAMPLE 3: LOW PERFORMER (40% score)                           │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Items: [Q1, Q2, Q3, Q4, Q5]                                 │
│  Answers: [✓, ✗, ✗, ✗, ✗]                                   │
│  Correct: 1 / 5 = 20%                                         │
│                                                                │
│  Decision: "relearn" ❌                                        │
│  Reason: score < 50%                                           │
│  Action: User MUST relearn this topic                         │
│          (No override option)                                  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 🧪 Testing Strategy by Layer

```
┌────────────────────────────────────────────────────────────────┐
│ LAYER 1: UNIT TESTS (No Database)                             │
├────────────────────────────────────────────────────────────────┤
│ ✅ Schema validation (Pydantic models)                         │
│ ✅ Router registration (FastAPI)                              │
│ ✅ Service logic (scoring, decisions)                         │
│ ✅ Utility functions (_bucket_select_5, _classify_decision)  │
│                                                                │
│ Tests: ~15 unit tests                                          │
│ Speed: <1 second                                               │
│ Command: pytest tests/test_*.py -v                            │
└────────────────────────────────────────────────────────────────┘
        │
        ▼
┌────────────────────────────────────────────────────────────────┐
│ LAYER 2: REPOSITORY TESTS (Mock Database)                      │
├────────────────────────────────────────────────────────────────┤
│ ✅ Query builders                                              │
│ ✅ Data fetching logic                                         │
│ ✅ CRUD operations (create, read, update, insert)            │
│                                                                │
│ Tests: ~10 repository tests                                    │
│ Speed: <1 second                                               │
│ Command: pytest tests/repositories/ -v                        │
└────────────────────────────────────────────────────────────────┘
        │
        ▼
┌────────────────────────────────────────────────────────────────┐
│ LAYER 3: INTEGRATION TESTS (Real Database)                    │
├────────────────────────────────────────────────────────────────┤
│ ✅ Step 1: Set goals                                           │
│ ✅ Step 2: Get topics                                          │
│ ✅ Step 3: Mark known topics                                   │
│ ✅ Step 4: Set experience level                                │
│ ✅ Step 5: Start placement                                     │
│ ✅ Step 6: Submit answers                                      │
│ ✅ Step 7: Complete journey                                    │
│ ✅ Step 8: Edge cases (mixed answers)                          │
│                                                                │
│ Tests: 8 integration tests                                     │
│ Speed: 2-5 seconds                                             │
│ Command: pytest tests/integration/test_onboarding_flow_e2e.py │
│ Status: ✅ READY (from file: test_onboarding_flow_e2e.py)    │
└────────────────────────────────────────────────────────────────┘
        │
        ▼
┌────────────────────────────────────────────────────────────────┐
│ LAYER 4: END-TO-END TESTS (Manual/Postman)                    │
├────────────────────────────────────────────────────────────────┤
│ ✅ Full journey through API endpoints                          │
│ ✅ Frontend integration                                        │
│ ✅ UI/UX verification                                          │
│                                                                │
│ Manual: See MANUAL_TESTING_GUIDE.md                           │
│ Postman: Import curl examples from guide                      │
│ Status: ✅ READY (documentation: MANUAL_TESTING_GUIDE.md)     │
└────────────────────────────────────────────────────────────────┘
```

---

## 📚 Quick Reference - Decision Matrix

```
┌─────────────────────────────────────────────────────────────┐
│ DECISION CLASSIFICATION QUICK REFERENCE                    │
├──────────────┬──────────────┬───────────────┬──────────────┤
│ Score Range  │ Decision     │ User Can...   │ Tests        │
├──────────────┼──────────────┼───────────────┼──────────────┤
│ ≥ 70%        │ "skip" ✅    │ Skip topic    │ test_step6   │
│              │              │ (no override) │ test_journey │
├──────────────┼──────────────┼───────────────┼──────────────┤
│ 50-70%       │ "review" ⚠️  │ Choose:       │ test_step6   │
│              │              │ • Skip        │ test_journey │
│              │              │ • Relearn     │ test_mixed   │
├──────────────┼──────────────┼───────────────┼──────────────┤
│ < 50%        │ "relearn" ❌ │ Must relearn  │ test_step6   │
│              │              │ (no override) │ test_journey │
│              │              │               │ test_mixed   │
└──────────────┴──────────────┴───────────────┴──────────────┘
```

---

## 🎓 Summary

This visual guide covers:
1. **Complete flow diagram** - 9-step onboarding journey
2. **Scoring logic** - How 60% = "review" decision
3. **Item selection** - The 1-2-2 distribution logic
4. **Database schema** - How data relates
5. **Data flow** - Frontend → Backend → Database
6. **Test coverage** - 4 layers of testing
7. **Decision matrix** - Quick reference

All documented and tested! ✅
