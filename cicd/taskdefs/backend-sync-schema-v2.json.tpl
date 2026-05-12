{
  "family": "__SYNC_SCHEMA_V2_TASK_FAMILY__",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "executionRoleArn": "__TASK_EXECUTION_ROLE_ARN__",
  "taskRoleArn": "__BACKEND_TASK_ROLE_ARN__",
  "containerDefinitions": [
    {
      "name": "sync-schema-v2",
      "image": "__IMAGE_URI__",
      "essential": true,
      "command": ["uv", "run", "python", "-m", "src.scripts.schema_v2.sync_schema_v2"],
      "environment": [
        { "name": "PYTHONPATH", "value": "/app" },
        { "name": "AGENT_GRAPH_CHECKPOINTER_SETUP", "value": "false" }
      ],
      "secrets": [
        { "name": "DATABASE_URL", "valueFrom": "__BACKEND_SECRET_ARN__:DATABASE_URL::" }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "__LOG_GROUP__",
          "awslogs-region": "__AWS_REGION__",
          "awslogs-stream-prefix": "sync-schema-v2"
        }
      }
    }
  ]
}
