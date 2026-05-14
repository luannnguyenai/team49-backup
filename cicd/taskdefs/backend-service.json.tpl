{
  "family": "__BACKEND_TASK_FAMILY__",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "__TASK_EXECUTION_ROLE_ARN__",
  "taskRoleArn": "__BACKEND_TASK_ROLE_ARN__",
  "containerDefinitions": [
    {
      "name": "__ECS_BACKEND_SERVICE_NAME__",
      "image": "__IMAGE_URI__",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        { "name": "PORT", "value": "8000" },
        { "name": "DEBUG", "value": "false" },
        { "name": "LOG_LEVEL", "value": "INFO" },
        { "name": "DB_ECHO", "value": "false" },
        { "name": "AGENT_GRAPH_CHECKPOINTER_SETUP", "value": "false" },
        { "name": "AGENT_GRAPH_CHECKPOINTER_BACKEND", "value": "postgres" },
        { "name": "ASSET_STORAGE_PROVIDER", "value": "s3" },
        { "name": "AWS_REGION", "value": "__AWS_REGION__" },
        { "name": "AWS_DEFAULT_REGION", "value": "__AWS_REGION__" },
        { "name": "AWS_S3_BUCKET", "value": "a20-course-assets-prod" },
        { "name": "AWS_S3_PREFIX", "value": "courses" },
        { "name": "AWS_CLOUDWATCH_LOG_GROUPS", "value": "/ecs/__ECS_BACKEND_SERVICE_NAME__,/ecs/a20-frontend,/ecs/__ECS_BACKEND_SERVICE_NAME__-migrate,/ecs/__ECS_BACKEND_SERVICE_NAME__-bootstrap,/ecs/__ECS_BACKEND_SERVICE_NAME__-seed-core,/ecs/__ECS_BACKEND_SERVICE_NAME__-sync-schema-v2,/ecs/__ECS_BACKEND_SERVICE_NAME__-seed-accounts" },
        { "name": "CLOUDFRONT_DOMAIN", "value": "__CLOUDFRONT_DOMAIN__" },
        { "name": "ASSET_URL_EXPIRE_SECONDS", "value": "900" },
        { "name": "FRONTEND_BASE_URL", "value": "__PRODUCTION_FRONTEND_URL__" },
        { "name": "CORS_ORIGINS", "value": "[\"__PRODUCTION_FRONTEND_URL__\"]" },
        { "name": "ALGORITHM", "value": "HS256" },
        { "name": "ACCESS_TOKEN_EXPIRE_MINUTES", "value": "30" },
        { "name": "REFRESH_TOKEN_EXPIRE_DAYS", "value": "7" },
        { "name": "MODEL_PROVIDER", "value": "openai" },
        { "name": "DEFAULT_MODEL", "value": "gpt-5.4-mini" },
        { "name": "FAST_MODEL", "value": "gpt-5.4-nano" },
        { "name": "MODEL_EXTRA_KWARGS", "value": "{}" },
        { "name": "LLM_REQUEST_TIMEOUT_SECONDS", "value": "30" },
        { "name": "LLM_MAX_RETRIES", "value": "1" },
        { "name": "LOKI_URL", "value": "http://loki.obs.a20-prod.internal:3100" }
      ],
      "secrets": [
        { "name": "DATABASE_URL", "valueFrom": "__BACKEND_SECRET_ARN__:DATABASE_URL::" },
        { "name": "REDIS_URL", "valueFrom": "__BACKEND_SECRET_ARN__:REDIS_URL::" },
        { "name": "SECRET_KEY", "valueFrom": "__BACKEND_SECRET_ARN__:SECRET_KEY::" },
        { "name": "OPENAI_API_KEY", "valueFrom": "__BACKEND_SECRET_ARN__:OPENAI_API_KEY::" },
        { "name": "ANTHROPIC_API_KEY", "valueFrom": "__BACKEND_SECRET_ARN__:ANTHROPIC_API_KEY::" },
        { "name": "GEMINI_API_KEY", "valueFrom": "__BACKEND_SECRET_ARN__:GEMINI_API_KEY::" },
        { "name": "LANGFUSE_SECRET_KEY", "valueFrom": "__BACKEND_SECRET_ARN__:LANGFUSE_SECRET_KEY::" },
        { "name": "LANGFUSE_PUBLIC_KEY", "valueFrom": "__BACKEND_SECRET_ARN__:LANGFUSE_PUBLIC_KEY::" },
        { "name": "GMAIL_APP_PASSWORD", "valueFrom": "__BACKEND_SECRET_ARN__:GMAIL_APP_PASSWORD::" },
        { "name": "AI_LOG_API_KEY", "valueFrom": "__BACKEND_SECRET_ARN__:AI_LOG_API_KEY::" },
        { "name": "ADMIN_TOKEN", "valueFrom": "__BACKEND_SECRET_ARN__:ADMIN_TOKEN::" }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "__LOG_GROUP__",
          "awslogs-region": "__AWS_REGION__",
          "awslogs-stream-prefix": "__ECS_BACKEND_SERVICE_NAME__"
        }
      }
    }
  ]
}
