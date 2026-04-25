# DL -> CV/NLP Learning Path Readiness

Date: 2026-04-25

This note summarizes whether the current canonical data can support a product
learning path shaped as:

```text
Deep Learning foundation (CS230) -> CV branch (CS231n)
                                  -> NLP branch (CS224n)
```

## Current Canonical Data

Source bundle:

`data/final_artifacts/cs224n_cs231n_cs230_v1/canonical`

Validation status:

- `hard_failure_count = 0`
- `rejected_items = 0`
- `courses = 3`
- `units = 376`
- `question_bank = 1276`
- `prerequisite_edges = 118`
- `pruned_edges = 44`

Course coverage:

| Course | Lectures | Units | Quiz-backed units | Questions |
|---|---:|---:|---:|---:|
| CS230 | 9 | 81 | 73 | 291 |
| CS231n | 18 | 139 | 139 | 381 |
| CS224n | 23 | 156 | 149 | 604 |

CS230 lecture titles are now canonical and product-safe:

| Order | Lecture |
|---:|---|
| 1 | Lecture 1: Introduction to Deep Learning |
| 2 | Lecture 2: Supervised, Self-Supervised, and Weakly Supervised Learning |
| 3 | Lecture 3: Full Cycle of a Deep Learning Project |
| 4 | Lecture 4: Adversarial Robustness and Generative Models |
| 5 | Lecture 5: Deep Reinforcement Learning |
| 6 | Lecture 6: AI Project Strategy |
| 7 | Lecture 7: Beyond the Model: Enhancing LLM Applications |
| 8 | Lecture 8: Career Advice in AI |
| 9 | Lecture 9: What Is Going On Inside My Model? |

## Verdict

The data is ready for a demo-quality DL -> CV/NLP path.

For production, the main missing piece is not content availability. The missing
piece is a product-level path template and planner policy that turns canonical
courses/units/KP edges into learner-facing routes.

The current graph is good enough to:

- Start fresh learners with CS230 foundation units.
- Branch learners toward CS231n when their goal is CV.
- Branch learners toward CS224n when their goal is NLP.
- Offer skip/waive opportunities when a learner has mastered shared KPs.
- Use mini-quiz and placement items from `question_bank` via `item_phase_map`.

It is not yet strong enough to rely purely on graph traversal for beautiful
course-level path ordering. The graph has 118 kept edges across 607 KPs, so it
should be combined with explicit product path templates.

## Recommended Product Path Model

Use a hybrid approach:

1. Product template decides macro order.
2. Prerequisite graph gates/skip/bridge inside that order.
3. Learner mastery personalizes which units are learned, skipped, reviewed, or bridged.

Do not expose KP or prerequisite graph language in the UI.

### Track: Fresh Learner Interested In CV

Default route:

```text
CS230 foundation:
  L1 Introduction to Deep Learning
  L2 Supervised, Self-Supervised, and Weakly Supervised Learning
  L4 Adversarial Robustness and Generative Models

Then CS231n core:
  L1 Introduction
  L2 Image Classification with Linear Classifiers
  L3 Regularization and Optimization
  L4 Neural Networks and Backpropagation
  L5 Image Classification with CNNs
  L6 CNN Architectures

Then advanced CV options:
  L9 Detection / Segmentation / Visualization
  L12 Self-supervised Learning
  L13-L14 Generative Models
  L15 3D Vision
  L16 Vision and Language
```

Rationale:

- CS230 L1-L2 gives the deep learning and representation-learning frame.
- CS230 L4 gives generative-model concepts that connect to CS231n generative modules.
- CS231n L1-L6 is the true CV spine.

### Track: Fresh Learner Interested In NLP

Default route:

```text
CS230 foundation:
  L1 Introduction to Deep Learning
  L2 Supervised, Self-Supervised, and Weakly Supervised Learning
  L7 Beyond the Model: Enhancing LLM Applications
  L9 What Is Going On Inside My Model?

Then CS224n core:
  L1 Intro and Word Vectors
  L4 Word Vectors and Language Models
  L5 Backpropagation / Neural Networks
  L7 Recurrent Neural Networks
  L8 Sequence to Sequence Models
  L9 Attention / LLM Intro
  L10 Self-Attention and Transformers
  L11 Pretraining

Then advanced NLP options:
  L13 Post-training
  L14 Natural Language Generation
  L15 Benchmarking
  L16 Efficient Training
  L18 Multimodal Deep Learning
  L20 Reasoning and Agents
```

Rationale:

- CS230 L7 gives product-level LLM/RAG/agents context before deep CS224n modules.
- CS230 L9 gives interpretability context that connects to later model-behavior topics.
- CS224n remains the main NLP technical course.

### Track: Learner Already Has DL Background

Skip most CS230 foundation by default, but run placement/skip verification over:

- CS230 L1/L2 core DL and representation-learning concepts.
- CS231n L1-L4 if CV selected.
- CS224n L1/L4/L5 if NLP selected.

If the learner passes skip verification, mark units in `waived_units`, not
`completed_units`.

## Useful Existing Bridge Edges

The graph already has useful CS230-to-branch bridges:

### Toward NLP / CS224n

- `Encoding versus embedding -> Word vectors and embedding spaces`
- `Encoding versus embedding -> Contextual representations and embeddings`
- `Agent-environment transition vocabulary -> Reinforcement learning and RLHF for NLG`
- `In-context learning -> In-context and few-shot multimodal reasoning`
- `Saliency via input gradients -> Limits of attribution methods for behavioral inference`

### Toward CV / CS231n

- `Data-driven supervised learning pipeline -> Nearest neighbor classification`
- `Encoding versus embedding -> SimCLR contrastive representation learning`
- `Forward diffusion process -> Diffusion denoising intuition`
- `Generative modeling as distribution learning -> GAN latent generator distribution`
- `Diffusion denoising intuition -> Diffusion mathematical perspectives`
- `Latent diffusion models -> Text-to-video diffusion scaling`
- `SimCLR contrastive representation learning -> Contrastive vision-language pretraining`

These bridges are enough for demo path explanations and skip/bridge suggestions.
They are still sparse for fully automatic long-horizon planning.

## Onboarding Implication

The first onboarding question should be goal/interest, not course-first.

Recommended options:

- `Computer Vision`
- `Natural Language Processing`
- `Generative AI / LLM Applications`
- `Deep Learning Foundations`

Then ask experience level:

- `Fresh`
- `Có nền`
- `Chuyên sâu`

Behavior:

- `Fresh`: few questions, recommend template path, no heavy unit picking.
- `Có nền`: section/lecture-level known-content selection plus medium placement.
- `Chuyên sâu`: unit-level known-content selection plus longer optional placement.

This matches subscription-style product positioning better than course-first
catalog positioning. Courses remain visible, but learner-facing path starts from
goal/topic.

## Planner Policy

Do not let the planner free-roam the whole graph at first.

Recommended planner order:

1. Load selected path template from `goal_preferences`.
2. Pick the next unit by course/lecture/unit order inside that template.
3. Run prereq gate from `prerequisite_edges`.
4. Run skip gate from `learner_mastery`.
5. If prereq gap exists, offer bridge.
6. If mastery is high, offer skip verification.
7. Otherwise show the lecture unit normally.

This keeps UX predictable while still using the graph for personalization.

## Data Gaps To Fix Next

### 1. Product path templates

Need a small app-level config, for example:

```json
{
  "path_id": "dl_to_cv",
  "goal": "Computer Vision",
  "ordered_blocks": [
    {"course_id": "CS230", "lecture_ids": ["lecture-01", "lecture-02", "lecture-04"]},
    {"course_id": "CS231n", "lecture_ids": ["cs231n-lecture-1", "cs231n-lecture-2", "cs231n-lecture-3", "cs231n-lecture-4", "cs231n-lecture-5", "cs231n-lecture-6"]}
  ]
}
```

Without this, the graph is too sparse to reliably produce a beautiful path by
itself.

### 2. Course/goal metadata

`courses.jsonl` currently has empty `track_tags`. The KP rows have useful tags,
but course cards and onboarding need product-level metadata:

- `goal_tags`
- `recommended_for`
- `path_role`: `foundation`, `branch_core`, `advanced`
- `available_status`

### 3. More cross-course edges later

Current cross-course bridge coverage is enough for demo but sparse for production.
After product path templates are in place, add focused P5 review for:

- CS230 L1/L2 -> CS231n L1-L6
- CS230 L1/L2/L7 -> CS224n L1/L4/L5/L10/L11
- CS230 L4 -> CS231n L13-L16

### 4. UI/player policy

For lecture playback, the UI should use full lecture video, not segment-only video.
Segments should appear as chapter markers on the timeline, and mini-quizzes should
trigger at segment boundaries or be queued to the end of the lecture depending on
user setting.

## Next Implementation Tasks

Recommended order:

1. Add product path templates for `dl_to_cv`, `dl_to_nlp`, and `dl_foundation`.
2. Update onboarding to select goal first, then experience level.
3. Map onboarding output into `goal_preferences.selected_course_ids` and path template id.
4. Update planner to follow path template order, using KG only for prereq/skip/bridge.
5. Update player to use full lecture video with segment markers and mini-quiz checkpoints.
6. Add focused cross-course P5 pass later if planner explanations feel thin.

