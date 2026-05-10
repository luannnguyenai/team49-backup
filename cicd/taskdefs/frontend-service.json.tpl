{
  "family": "__FRONTEND_TASK_FAMILY__",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "__TASK_EXECUTION_ROLE_ARN__",
  "taskRoleArn": "__FRONTEND_TASK_ROLE_ARN__",
  "containerDefinitions": [
    {
      "name": "__ECS_FRONTEND_SERVICE_NAME__",
      "image": "__IMAGE_URI__",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 3000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        { "name": "NODE_ENV", "value": "production" },
        { "name": "PORT", "value": "3000" },
        { "name": "HOSTNAME", "value": "0.0.0.0" },
        { "name": "NEXT_TELEMETRY_DISABLED", "value": "1" }
      ],
      "secrets": [],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "__LOG_GROUP__",
          "awslogs-region": "__AWS_REGION__",
          "awslogs-stream-prefix": "__ECS_FRONTEND_SERVICE_NAME__"
        }
      }
    }
  ]
}
