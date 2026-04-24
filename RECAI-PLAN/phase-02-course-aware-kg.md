# Phase 02: Course-Aware KG

## Goal

Extend the materialized KG so `course` becomes a first-class graph entity rather than an external item looked up beside the graph.

## Why This Phase Exists

The current KG is topic-centric.
The target recommendation engine is course-centric.

That gap means the engine cannot yet answer cleanly:

- which course best remediates weak topics
- which course best advances from current strengths
- which course best fits prerequisite readiness
- which courses are siblings, bridges, or next steps

This phase adds the graph structure required to answer those questions with graph-native features.

## Scope

This phase covers:

- course node representation in the graph model
- course-to-topic and course-to-KC edges
- course-to-course prerequisite and progression edges
- bridge and transfer edges relevant to course recommendation

This phase does **not** yet implement final ranking logic.

## New And Modified Modules

### Modify

- `src/kg/schemas.py`
  Add `course` as a node kind and add any edge types needed for course-aware recommendation.
- `src/kg/models.py`
  Reflect schema changes if ORM-level validation or enums need updating.
- `src/kg/builder.py`
  Emit course-aware nodes and edges from normalized inputs.
- `src/kg/repository.py`
  Support new node and edge types without special cases.
- `alembic/versions/*`
  Add a migration if enums or constraints need expansion.

### Add

- `src/kg/course_builder.py`
  Isolate course graph emission logic from the generic builder.
- `tests/kg/test_course_graph_build.py`
  Validate course-aware edge generation.
- `tests/kg/test_course_graph_sync.py`
  Validate persisted course-aware graph rows.

## Graph Structures To Add

### Nodes

- `course`

### Edge Families

- `course -> topic`
  Course covers or teaches these topics.
- `course -> kc`
  Course develops or requires these KCs.
- `course -> course`
  Course progression, prerequisite, or recommended-after relationships.
- `course -> concept`
  Optional later edge family if concept-level explainability is required.

### Edge Semantics

Edge families should support recommendation features, not just ontology purity.

At minimum, define edges for:

- `COVERS`
- `DEVELOPS`
- `REQUIRES_KC`
- `ALIGNS_WITH`
- `TRANSFERS_TO`

If current enums are insufficient, expand them deliberately and document meaning clearly.

## Data Inputs

This phase depends on stable mappings between courses and learning entities.

Preferred mapping order:

1. explicit join tables
2. canonical course-unit-topic lineage in DB
3. import-generated mapping tables

Do not rely on free-form title matching for recommendation-critical graph edges.

## Feature Intent

The course-aware KG must support extraction of:

- prerequisite readiness
- remediation coverage
- advancement alignment
- topic transfer potential
- graph distance to goal topics
- availability-aware candidate neighborhoods

The graph should be rich enough that the later ranker can ask:

- what topics does this course fix
- what strong topics does it build on
- how far is it from the learner's goal
- what course should logically come before or after it

## Testing Plan

### Unit Tests

- course nodes are emitted once per canonical course
- course-topic edges map correctly from source lineage
- course-KC edges map correctly from topic and unit mappings
- prerequisite and progression edges are deterministic

### Integration Tests

- syncing the course-aware build writes expected `kg_edges`
- stale generated course edges are soft-deleted on source removal
- no duplicate semantic edges are inserted

### Explainability Regression Tests

- for a seeded course, the graph can recover:
  - taught topics
  - remediated topics
  - advancement topics
  - prerequisite dependencies

## Suggested Commit Slices

1. `feat: add course node support to kg schemas`
2. `feat: add course-aware kg builder module`
3. `feat: emit course-topic and course-kc edges`
4. `feat: add course-course graph relations`
5. `test: cover course-aware kg build and sync`

## Done When

- `course` is a first-class graph node
- graph edges support course recommendation features directly
- graph sync persists course-aware nodes and edges correctly
- later recommendation logic can derive candidate features from graph structure without bootstrap hacks
