{
  "family": "__SEED_ACCOUNTS_TASK_FAMILY__",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "__TASK_EXECUTION_ROLE_ARN__",
  "taskRoleArn": "__BACKEND_TASK_ROLE_ARN__",
  "containerDefinitions": [
    {
      "name": "seed-accounts",
      "image": "__IMAGE_URI__",
      "essential": true,
      "command": ["uv", "run", "python", "-m", "src.scripts.create_seed_accounts"],
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
          "awslogs-stream-prefix": "seed-accounts"
        }
      }
    }
  ]
}
