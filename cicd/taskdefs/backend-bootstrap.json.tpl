{
  "family": "__BOOTSTRAP_TASK_FAMILY__",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "executionRoleArn": "__TASK_EXECUTION_ROLE_ARN__",
  "taskRoleArn": "__BACKEND_TASK_ROLE_ARN__",
  "containerDefinitions": [
    {
      "name": "bootstrap",
      "image": "__IMAGE_URI__",
      "essential": true,
      "command": [
        "sh",
        "-c",
        "set -e; uv run python scripts/seed_lectures.py; uv run python -m src.scripts.schema_v2.backfill_schema_v2 --apply --report-path reports/backfill.json; uv run python -m src.scripts.schema_v2.validate_schema_v2 --report-path reports/validate.json; uv run python -m src.scripts.pipeline.check_canonical_runtime_parity; uv run python -m src.scripts.create_seed_accounts"
      ],
      "environment": [
        { "name": "PYTHONPATH", "value": "/app" },
        { "name": "AGENT_GRAPH_CHECKPOINTER_SETUP", "value": "false" }
      ],
      "secrets": [
        { "name": "DATABASE_URL", "valueFrom": "__BACKEND_SECRET_ARN__:DATABASE_URL::" },
        { "name": "REDIS_URL", "valueFrom": "__BACKEND_SECRET_ARN__:REDIS_URL::" },
        { "name": "SECRET_KEY", "valueFrom": "__BACKEND_SECRET_ARN__:SECRET_KEY::" }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "__LOG_GROUP__",
          "awslogs-region": "__AWS_REGION__",
          "awslogs-stream-prefix": "bootstrap"
        }
      }
    }
  ]
}
