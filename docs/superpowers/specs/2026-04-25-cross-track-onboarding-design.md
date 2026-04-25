# Cross-Track Onboarding Design

## Goal

Redesign onboarding so the system can recommend a multi-course, multi-unit learning path instead of forcing the learner to choose courses before diagnosis.

The new onboarding must support:

- `primary track` + `supporting track`
- self-estimated starting level
- assessment driven by a blueprint layer above canonical `question_bank`
- post-assessment recommendation of a cross-track learning path

## Product Direction

The onboarding should be `goal-first` and `diagnosis-first`, not `course-first`.

The learner should answer:

1. what they primarily want to learn
2. what secondary area may support that goal
3. what outcome they want
4. what level they believe they are at
5. a short assessment tailored from those signals
6. practical learning constraints

Only after those steps should the system recommend courses and units.

## Problems With Current Flow

- It asks the learner to choose courses before the system has diagnosed readiness.
- It mixes intent capture, self-report, and planning constraints in one early form.
- It asks "what do you already know?" but the current runtime does not use that signal as the main assessment scope driver.
- It reduces recommendation quality because the learner is pushed to pick a solution before the product understands the problem.
- It does not fit the desired output model of a system-generated cross-track learning path.

## Non-Goals

- Do not redesign the entire planner in this phase.
- Do not build a fully adaptive multi-stage CAT engine in the first iteration.
- Do not require question-level manual tagging beyond what canonical metadata already provides.
- Do not ask the learner to manually assemble their own path.

## Target User Model

The learner may:

- know they want `NLP` or `Computer Vision`
- want a secondary area for support, such as foundations or transfer knowledge
- be unsure which course is the correct entry point
- be able to estimate their level roughly, but not accurately enough for final placement

The system should therefore treat self-estimated level as a seed signal, not as truth.

## Proposed Onboarding Flow

### Step 1: Primary Track

The learner chooses one main direction, for example:

- NLP
- Computer Vision
- ML Foundations
- Undecided

This defines the dominant recommendation axis.

### Step 2: Supporting Track

The learner chooses one secondary direction, for example:

- ML Foundations
- NLP
- Computer Vision
- None

This does not compete equally with the primary track. It exists to authorize bridge content and cross-track recommendations.

### Step 3: Goal

The learner chooses what they are trying to achieve, for example:

- prepare for research
- build projects
- get job-ready
- strengthen foundations
- switch domain

This affects the later path shape, especially whether the planner prefers depth, breadth, or practical application.

### Step 4: Self-Estimated Level

The learner chooses:

- beginner
- intermediate
- advanced
- not sure

This only seeds assessment difficulty and length. It must not directly determine the final path.

### Step 5: Assessment

The assessment service resolves a blueprint using:

- primary track
- supporting track
- goal
- self-estimated level

It then builds a question pool from canonical runtime data and serves a short placement assessment.

### Step 6: Constraints

After assessment, ask:

- available hours per week
- target deadline
- preferred learning method
- optional pace preference such as `go deep` vs `move fast`

These constraints personalize the recommended path without overloading the learner before they have seen value.

### Step 7: Recommendation

The system returns a recommended learning path containing:

- core units from the primary track
- bridge units from the supporting track
- skipped units where evidence is sufficient
- estimated time
- explanation of why the path was chosen

## UX Principles

### Goal Before Solution

Ask what the learner wants to become good at before asking what course they want.

### Progressive Commitment

Do not ask for detailed schedule commitments before the system has established the learner's level and shown useful output.

### Explainability

The learner must be able to understand why a path includes both primary-track and supporting-track content.

### Controlled Cross-Track Mixing

Cross-track does not mean equal-weight blending. The system should preserve a dominant primary axis and a bounded supporting axis.

## Assessment Blueprint Layer

### Purpose

Add a layer above canonical `question_bank` that decides how to assemble an assessment from existing metadata.

This avoids hardcoding course-first logic into onboarding and avoids requiring full scope metadata to already exist on each question.

## Minimum Blueprint Schema

Each blueprint should contain:

- `blueprint_id`
- `primary_track`
- `supporting_track`
- `goal`
- `self_level_band`
- `phase`
- `core_unit_ids` and/or `core_kp_ids`
- `bridge_unit_ids` and/or `bridge_kp_ids`
- `question_mix`
- `difficulty_policy`
- `question_count`
- `selection_rules`
- `path_handoff_rules`

### Meaning Of Key Fields

- `core_*` identifies the dominant assessment pool for the primary track.
- `bridge_*` identifies optional cross-track assessment pool for transfer readiness.
- `question_mix` controls how many questions come from core vs bridge pools.
- `difficulty_policy` converts self-estimated level into allowed difficulty bands.
- `selection_rules` constrain pool sampling, such as coverage across units or KPs.
- `path_handoff_rules` define how assessment output should seed later path generation.

## Runtime Assessment Flow

1. onboarding stores `primary_track`, `supporting_track`, `goal`, and `self_level_band`
2. assessment resolves the closest matching blueprint
3. blueprint expands into canonical unit/KP pools
4. selector queries canonical runtime tables
5. selector samples questions according to mix, coverage, and difficulty policy
6. learner completes assessment
7. assessment returns structured readiness signals instead of only one overall score

## Canonical Data Sources

The assessment runtime should keep using canonical runtime tables, not raw bootstrap files:

- `question_bank`
- `item_phase_map`
- `item_kp_map`
- `unit_kp_map`
- `learning_units`

The raw JSON files remain bootstrap/import sources, not direct runtime recommendation sources.

## Blueprint Resolution Rules

Resolution should try the most specific blueprint first, then fall back safely:

1. exact match on primary, supporting, goal, and self level
2. same primary, goal, and self level with no supporting specialization
3. same primary and self level with default goal
4. primary-track default placement blueprint

This prevents runtime failure when blueprint coverage is incomplete.

## Assessment Output Contract

Assessment should return at least:

- `primary_track_score`
- `supporting_track_score`
- `foundation_readiness`
- `bridge_readiness`
- `recommended_entry_band`
- per-unit or per-KP weakness signals where possible

Do not rely on a single overall score if the downstream product is a structured learning path.

## Learning Path Generation Rules

The planner should use onboarding and assessment together:

- `primary track` defines the main spine of the path
- `supporting track` authorizes bridge units and supporting courses
- `goal` shapes depth vs breadth vs practical orientation
- `assessment` determines readiness, skips, and entry point
- `constraints` determine pacing and scheduling

The resulting path may include:

- one or more primary-track courses
- supporting-track units inserted as prerequisites or bridges
- skip or quick-review decisions when mastery is already sufficient

## Example Outcome

For `primary=NLP`, `supporting=Computer Vision`, `goal=build projects`, `self_level=beginner`:

- assessment should mostly test NLP foundations
- a smaller portion should test bridge concepts relevant to multimodal or representation transfer
- recommendation should likely start with NLP foundations
- supporting CV units should appear only where they unlock the stated direction

The system should not flatten this into a generic "study everything" path.

## Error Handling

- If no blueprint resolves, fall back to a primary-track default placement blueprint.
- If canonical pool is too small, reduce question count rather than failing hard.
- If supporting-track bridge pool is empty, continue with core-only assessment and record that bridge evidence is unavailable.
- If learner selects `Undecided`, route to a broad foundation blueprint instead of forcing a domain-specific one.

## Rollout Strategy

### Phase 1

- add new onboarding fields for primary track, supporting track, goal, and self-estimated level
- add blueprint configuration and resolution
- keep assessment non-adaptive but blueprint-driven
- generate structured readiness output

### Phase 2

- use assessment output to generate better bridge-aware learning paths
- improve explainability in recommendation UI

### Phase 3

- optionally introduce adaptive branching inside assessment if blueprint-driven placement proves insufficient

## Success Criteria

- learners are no longer forced to choose courses before diagnosis
- onboarding directly supports cross-track recommendation
- assessment scope is built from blueprint logic, not course preselection
- the planner can recommend a multi-course, multi-unit path with explicit bridge content
- recommendation explanations are understandable to the learner
