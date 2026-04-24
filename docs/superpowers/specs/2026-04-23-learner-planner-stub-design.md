# Learner And Planner Stub Persistence Design

> **Historical spec:** This document is preserved for implementation history only. Learner/planner tables now exist and runtime writes canonical state; use the current handoff docs as authority.

## Goal

Thêm lớp persistence tối thiểu để thu hẹp gap giữa runtime ORM hiện tại và schema spec mới, nhưng không phá grain `topic/module` cũ đang chạy.

## Scope

Thêm 6 bảng mới ở runtime ORM:

- `learner_mastery_kp`
- `goal_preferences`
- `waived_units`
- `plan_history`
- `rationale_log`
- `planner_session_state`

Kèm:

- Alembic migration
- re-export model trong `src/models/__init__.py`
- test metadata/migration tối thiểu

## Non-Goals

- chưa thay `mastery_scores`
- chưa đổi `learning_paths`
- chưa thay service planner/recommendation hiện có
- chưa thêm API/router
- chưa backfill dữ liệu từ canonical artifacts

## Design

### Compatibility strategy

Giữ nguyên runtime cũ:

- `mastery_scores` vẫn là topic/KC grain hiện tại
- `learning_paths` vẫn là topic-level plan item hiện tại

Thêm sidecar tables cho schema mới:

- `learner_mastery_kp` lưu latent ability ở grain `user × kp`
- `goal_preferences` lưu course scope và goal weights chính thức
- `waived_units` tách audit skip khỏi `learning_paths.action = skip`
- `plan_history`, `rationale_log`, `planner_session_state` làm landing zone cho planner v2 về sau

### Table intent

#### `learner_mastery_kp`

Mục tiêu:

- lưu posterior style data ở grain `kp_id`
- không ép runtime hiện tại phải bỏ `mastery_scores`

Field tối thiểu:

- `user_id`
- `kp_id`
- `theta_mu`
- `theta_sigma`
- `mastery_mean_cached`
- `n_items_observed`
- `updated_by`
- timestamps

#### `goal_preferences`

Mục tiêu:

- có source-of-truth cho selected courses và goal weights
- không phải suy từ `users` hoặc `learning_paths`

Field tối thiểu:

- `user_id`
- `goal_weights_json`
- `selected_course_ids`
- `goal_embedding`
- `goal_embedding_version`
- `derived_from_course_set_hash`
- timestamps

#### `waived_units`

Mục tiêu:

- lưu bằng chứng cho quyết định waive/skip

Field tối thiểu:

- `user_id`
- `learning_unit_id`
- `evidence_items`
- `mastery_lcb_at_waive`
- `skip_quiz_score`
- timestamps

#### `plan_history`

Mục tiêu:

- có shell table cho planner run/versioning

Field tối thiểu:

- `user_id`
- `parent_plan_id`
- `trigger`
- `recommended_path_json`
- `goal_snapshot_json`
- `weights_used_json`
- timestamps

#### `rationale_log`

Mục tiêu:

- audit vì sao 1 unit được rank/chọn

Field tối thiểu:

- `plan_history_id`
- `learning_unit_id`
- `rank`
- `reason_code`
- `term_breakdown_json`
- `rationale_text`
- timestamps

#### `planner_session_state`

Mục tiêu:

- giữ planner-local counters giữa các lần replan

Field tối thiểu:

- `user_id`
- `session_id`
- `last_plan_history_id`
- `bridge_chain_depth`
- `consecutive_bridge_count`
- `state_json`
- timestamps

## Testing strategy

- test metadata/model existence
- test enum-free shape và relationship availability
- test migration file có create/drop đủ 6 bảng
- test Alembic head vẫn một head

## Commit strategy

1. learner mastery + goal preferences
2. waived units
3. planning stub tables
