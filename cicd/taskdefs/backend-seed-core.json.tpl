{
  "family": "__SEED_CORE_TASK_FAMILY__",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "executionRoleArn": "__TASK_EXECUTION_ROLE_ARN__",
  "taskRoleArn": "__BACKEND_TASK_ROLE_ARN__",
  "containerDefinitions": [
    {
      "name": "seed-core",
      "image": "__IMAGE_URI__",
      "essential": true,
      "command": [
        "sh",
        "-eu",
        "-c",
        "uv run python scripts/materialize_canonical_bundle.py --s3-uri \"$CANONICAL_BUNDLE_S3_URI\" --output-dir \"$CANONICAL_BUNDLE_LOCAL_DIR\"; uv run python scripts/seed.py --input-dir \"$CANONICAL_BUNDLE_LOCAL_DIR\""
      ],
      "environment": [
        { "name": "PYTHONPATH", "value": "/app" },
        { "name": "AGENT_GRAPH_CHECKPOINTER_SETUP", "value": "false" },
        { "name": "CANONICAL_BUNDLE_S3_URI", "value": "__CANONICAL_BUNDLE_S3_URI__" },
        { "name": "CANONICAL_BUNDLE_LOCAL_DIR", "value": "__CANONICAL_BUNDLE_LOCAL_DIR__" }
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
          "awslogs-stream-prefix": "seed-core"
        }
      }
    }
  ]
}
