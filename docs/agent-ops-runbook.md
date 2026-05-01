# Agent Ops Runbook

## In-Progress Conflicts

Look up `agent_graph_runs` by `thread_id` and status `created`, `running`, or `interrupted`.

If a user receives `409 in_progress`, confirm whether the active run is still moving. Non-interrupted active runs should be allowed to finish or be marked `failed_retryable` only after the request worker is known to be dead.

## Stuck Pending Actions

Look up `agent_pending_actions` by `conversation_id`, `thread_id`, or `action_id`.

If `expires_at` is in the past and status is `awaiting_confirmation`, run the pending-action janitor. Expired actions must not be approved from stale user confirmations.

HTTP entrypoint:

```bash
curl -X POST "$API_BASE/api/agent/ops/pending-actions/janitor" \
  -H "x-admin-token: $ADMIN_TOKEN"
```

## Response Persist Failed After Graph Success

Look up the run by `incoming_message_id`.

If `response_ref` exists, reuse `agent_response_payloads.payload_json` instead of regenerating the assistant response. A retry for the same `incoming_message_id` must return the same persisted response.

## Interrupted Run Finalization

When an action is approved, rejected, or expired, verify that the latest interrupted run for the thread is finalized as `succeeded` or `cancelled`.

This prevents a completed action from leaving the thread permanently blocked by `409 in_progress`.

## State Migration Failure

Archive the old thread, create a new thread for the conversation, and attach a migration note message.

Do not mutate committed assessment, progress, mastery, or planner state during thread recovery.
