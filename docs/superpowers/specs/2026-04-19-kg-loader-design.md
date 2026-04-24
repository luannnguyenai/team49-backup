# KG Phase 0 — Loader + Bridges YAML Design

> **Historical spec:** This document is preserved for implementation history only. Legacy KG runtime code has been removed; use canonical `prerequisite_edges` and the current handoff docs for production graph work.

**Date:** 2026-04-19
**Scope:** Task 2 of Knowledge Graph module — bridges YAML seed, DB-backed loader, test fixtures  
**Depends on:** `2026-04-19-kg-migration-schemas-design.md` (schemas already implemented)

---

## 1. Constraints

- All new files under `src/kg/**`, `data/`, `tests/kg/**` only.
- No imports from `src.assessment` or `src.tutor`.
- PyYAML for parsing (not JSON). Human-readable bridges file.
- No coupling to `build_kg.py` (builder is a separate phase).
- Phase 0 loader: no external API calls.
- All public functions: full type hints + Google-style docstrings.
- Commit after each task completes.

---

## 2. File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `data/kg_bridges.yaml` | Seed: 7 concepts, instance_of edges, transfers_to edges |
| Create | `src/kg/models_readonly.py` | Thin ORM models with slug columns (SELECT only) |
| Create | `src/kg/loader.py` | `load_sources()` — DB queries + YAML load + integrity checks |
| Create | `tests/kg/conftest.py` | Async fixtures: `db_with_seed`, `mini_bridges_path` |
| Create | `tests/kg/fixtures/mini_bridges.yaml` | Minimal bridges YAML for tests |
| Create | `tests/kg/test_loader.py` | 4 test cases |

---

## 3. kg_bridges.yaml — Full Seed Data

Topic slugs used match actual DB data from `data/topics.json`:
`nlp_transformers`, `cv_attention_transformers`, `cv_optimization`, `nlp_pretraining`,
`nlp_post_training`, `cv_captioning_seq2seq`, `cv_self_supervised`,
`cv_visualization_adversarial`, `cv_vision_language`

```yaml
concepts:
  - id: CON-self-attention
    name: Self-Attention
    description: Mechanism where each token/patch attends to all others via Q/K/V matrices.
    canonical_kc_slug: KC-NLP-self-attention

  - id: CON-optimization
    name: Gradient-Based Optimization
    description: First- and second-order methods (SGD, Adam, momentum) for minimising loss.
    canonical_kc_slug: KC-CV-optimization

  - id: CON-seq2seq-attention
    name: Seq2Seq with Attention
    description: Encoder-decoder architecture with additive/multiplicative attention (Bahdanau/Luong).
    canonical_kc_slug: KC-CV-seq2seq

  - id: CON-vlm
    name: Vision-Language Models
    description: Models that jointly encode image and text (CLIP, BLIP, Flamingo).
    canonical_kc_slug: KC-CV-vlm

  - id: CON-rlhf-ppo
    name: RLHF with PPO
    description: Reinforcement Learning from Human Feedback using Proximal Policy Optimisation.
    canonical_kc_slug: KC-NLP-rlhf

  - id: CON-self-supervised-pretrain
    name: Self-Supervised Pretraining
    description: Learning representations without labels via pretext tasks (MAE, SimCLR, BERT MLM).
    canonical_kc_slug: KC-CV-self-supervised

  - id: CON-adversarial
    name: Adversarial Robustness
    description: Adversarial examples, PGD attacks, and adversarial training for model robustness.
    canonical_kc_slug: KC-CV-adversarial

instance_of:
  - kc_slug: KC-NLP-self-attention
    concept_id: CON-self-attention
  - kc_slug: KC-CV-self-attention
    concept_id: CON-self-attention
  - kc_slug: KC-CV-optimization
    concept_id: CON-optimization
  - kc_slug: KC-NLP-optimization
    concept_id: CON-optimization
  - kc_slug: KC-CV-seq2seq
    concept_id: CON-seq2seq-attention
  - kc_slug: KC-NLP-seq2seq
    concept_id: CON-seq2seq-attention
  - kc_slug: KC-CV-vlm
    concept_id: CON-vlm
  - kc_slug: KC-NLP-vlm
    concept_id: CON-vlm
  - kc_slug: KC-NLP-rlhf
    concept_id: CON-rlhf-ppo
  - kc_slug: KC-CV-self-supervised
    concept_id: CON-self-supervised-pretrain
  - kc_slug: KC-NLP-self-supervised
    concept_id: CON-self-supervised-pretrain
  - kc_slug: KC-CV-adversarial
    concept_id: CON-adversarial

transfers_to:
  - from_topic: nlp_transformers
    to_topic: cv_attention_transformers
    weight: 0.95
    reason: CON-self-attention — identical Q/K/V mechanism
  - from_topic: cv_captioning_seq2seq
    to_topic: nlp_transformers
    weight: 0.88
    reason: CON-seq2seq-attention — attention mechanism precursor
  - from_topic: cv_optimization
    to_topic: nlp_pretraining
    weight: 0.82
    reason: CON-optimization — same Adam/LR-schedule knowledge applies
  - from_topic: nlp_transformers
    to_topic: cv_vision_language
    weight: 0.87
    reason: CON-vlm — transformer backbone transfers directly
  - from_topic: nlp_pretraining
    to_topic: nlp_post_training
    weight: 0.80
    reason: CON-rlhf-ppo — RLHF requires pretrained model
  - from_topic: cv_self_supervised
    to_topic: nlp_pretraining
    weight: 0.85
    reason: CON-self-supervised-pretrain — SSL objectives shared
  - from_topic: cv_visualization_adversarial
    to_topic: nlp_post_training
    weight: 0.72
    reason: CON-adversarial — robustness mindset transfers to alignment
```

---

## 4. src/kg/models_readonly.py

Separate `DeclarativeBase` (`KGReadBase`) to avoid conflicting with `src.models.base.Base`.
Maps only columns needed for KG SELECT queries.

```python
class KGReadBase(DeclarativeBase): ...

class TopicRO(KGReadBase):
    __tablename__ = "topics"
    id: UUID PK
    slug: str | None
    name: str
    module_id: UUID
    status: str | None   # 'published' filter

class KnowledgeComponentRO(KGReadBase):
    __tablename__ = "knowledge_components"
    id: UUID PK
    slug: str | None
    name: str
    topic_id: UUID

class QuestionRO(KGReadBase):
    __tablename__ = "questions"
    id: UUID PK
    item_id: str
    topic_id: UUID
    review_status: str | None   # 'published' filter
```

No `relationship()` — SELECT-only.

---

## 5. src/kg/loader.py

### Public API

```python
async def load_sources(
    session: AsyncSession,
    data_dir: Path,
) -> LoadedSources:
    """Load curriculum data from DB and bridges YAML, with integrity validation."""
```

### Flow

```
1. DB queries (all via session.execute + select()):
   a. topics   WHERE status = 'published'   AND slug IS NOT NULL
   b. kcs      WHERE slug IS NOT NULL
   c. questions WHERE review_status = 'published'

2. Load data_dir / "kg_bridges.yaml" via PyYAML (yaml.safe_load)
   → validate via BridgesDoc Pydantic model

3. Integrity checks (raise ValueError on failure):
   a. instance_of:  kc_slug ∈ kc_slug_set
   b. instance_of:  concept_id ∈ concept_id_set
   c. transfers_to: from_topic ∈ topic_slug_set
   d. transfers_to: to_topic   ∈ topic_slug_set
   e. canonical_kc_slug (non-None) ∈ kc_slug_set

4. Build + return LoadedSources
```

### Error handling

| Situation | Exception | Message pattern |
|---|---|---|
| YAML syntax error | `yaml.YAMLError` (bubble up) | native PyYAML message |
| YAML schema invalid | `pydantic.ValidationError` (bubble up) | Pydantic field errors |
| KC slug not found | `ValueError` | `"instance_of references unknown kc_slug: 'KC-X'"` |
| Topic slug not found | `ValueError` | `"transfers_to references unknown topic: 'slug-x'"` |
| canonical_kc_slug not found | `ValueError` | `"concept 'CON-X' canonical_kc_slug 'KC-Y' not found"` |

---

## 6. Test Fixtures

### tests/kg/conftest.py

```python
@pytest_asyncio.fixture
async def db_with_seed(db_session: AsyncSession):
    """
    Inserts 2 mini modules (mini_cv, mini_nlp), 3 topics each,
    2 KCs per topic, 1 published question per KC.
    Uses the existing db_session transaction — rolls back automatically.
    """

@pytest.fixture
def mini_bridges_path(tmp_path) -> Path:
    """Copies tests/kg/fixtures/mini_bridges.yaml to tmp_path, returns path."""
```

### tests/kg/fixtures/mini_bridges.yaml

```yaml
concepts:
  - id: CON-mini-attention
    name: Mini Attention
    description: Test concept bridging mini_cv and mini_nlp.
    canonical_kc_slug: KC-mini-nlp-attention

instance_of:
  - kc_slug: KC-mini-nlp-attention
    concept_id: CON-mini-attention
  - kc_slug: KC-mini-cv-attention
    concept_id: CON-mini-attention

transfers_to:
  - from_topic: mini_nlp_t1
    to_topic: mini_cv_t1
    weight: 0.90
    reason: CON-mini-attention overlap
```

KC slugs `KC-mini-nlp-attention` and `KC-mini-cv-attention` match exactly what `db_with_seed` inserts.

---

## 7. Test Cases (tests/kg/test_loader.py)

| Test | Scenario | Expected |
|---|---|---|
| `test_load_sources_happy_path` | valid DB seed + valid YAML | counts match: 6 topics, 12 kcs, 12 questions, 2 bridges instance_of, 1 transfers_to |
| `test_invalid_kc_slug_raises` | YAML with unknown kc_slug | `ValueError` matching `"unknown kc_slug"` |
| `test_invalid_topic_slug_raises` | YAML with unknown topic slug in transfers_to | `ValueError` matching `"unknown topic"` |
| `test_malformed_yaml_raises` | file with invalid YAML syntax | `yaml.YAMLError` |

---

## 8. Seed Data Counts (db_with_seed)

- Modules: 2 (`mini_cv`, `mini_nlp`)
- Topics per module: 3 → total 6 (slugs: `mini_cv_t{1,2,3}`, `mini_nlp_t{1,2,3}`)
- KCs per topic: 2 → total 12 (slugs: `KC-mini-{module}-{topic_n}-kc{1,2}`)
- Questions per KC: 1, `review_status='published'` → total 12
- All topics: `status='published'`
