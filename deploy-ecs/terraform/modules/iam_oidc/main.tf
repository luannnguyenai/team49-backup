data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# GitHub Actions OIDC provider
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

# ----- Deploy role (assumed by GitHub Actions) -----
resource "aws_iam_role" "deploy" {
  name = "${var.name_prefix}-gha-deploy"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.github.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_repository}:*"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "deploy" {
  name = "${var.name_prefix}-gha-deploy-inline"
  role = aws_iam_role.deploy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ECRAuth"
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      },
      {
        Sid    = "ECRPush"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:CompleteLayerUpload",
          "ecr:GetDownloadUrlForLayer",
          "ecr:InitiateLayerUpload",
          "ecr:PutImage",
          "ecr:UploadLayerPart",
          "ecr:DescribeImages",
          "ecr:DescribeRepositories",
          "ecr:BatchGetImage"
        ]
        Resource = [
          "arn:aws:ecr:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:repository/a20-backend",
          "arn:aws:ecr:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:repository/a20-frontend"
        ]
      },
      {
        Sid    = "ECSDeploy"
        Effect = "Allow"
        Action = [
          "ecs:DescribeServices",
          "ecs:DescribeTaskDefinition",
          "ecs:DescribeTasks",
          "ecs:ListTasks",
          "ecs:RegisterTaskDefinition",
          "ecs:UpdateService",
          "ecs:RunTask",
          "ecs:StopTask"
        ]
        Resource = "*"
      },
      {
        Sid    = "ELBTargetHealthRead"
        Effect = "Allow"
        Action = [
          "elasticloadbalancing:DescribeTargetHealth"
        ]
        Resource = "*"
      },
      {
        Sid    = "CloudWatchLogsRead"
        Effect = "Allow"
        Action = [
          "logs:DescribeLogStreams",
          "logs:GetLogEvents"
        ]
        Resource = "*"
      },
      {
        Sid      = "PassRoleToTasks"
        Effect   = "Allow"
        Action   = "iam:PassRole"
        Resource = "*"
        Condition = {
          StringEquals = {
            "iam:PassedToService" = "ecs-tasks.amazonaws.com"
          }
        }
      }
    ]
  })
}

# ----- Task execution role (used by ECS to pull image, fetch secrets, write logs) -----
resource "aws_iam_role" "task_execution" {
  name = "${var.name_prefix}-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "task_execution_managed" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Allow execution role to read Secrets Manager values for app secrets
resource "aws_iam_role_policy" "task_execution_secrets" {
  name = "${var.name_prefix}-task-execution-secrets"
  role = aws_iam_role.task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "secretsmanager:GetSecretValue",
        "kms:Decrypt"
      ]
      Resource = "*"
    }]
  })
}

# ----- Backend task role (runtime app permissions) -----
resource "aws_iam_role" "backend_task" {
  name = "${var.name_prefix}-backend-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# Backend may need S3 read for asset bucket (signed URL generation needs s3:GetObject)
resource "aws_iam_role_policy" "backend_task_s3" {
  name = "${var.name_prefix}-backend-task-s3"
  role = aws_iam_role.backend_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject"]
        Resource = [
          "${var.asset_bucket_arn}/${var.asset_prefix}/*",
          "${var.asset_bucket_arn}/${var.canonical_bundle_prefix}/*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = var.asset_bucket_arn
      }
    ]
  })
}

# ----- Frontend task role (no special perms in v1) -----
resource "aws_iam_role" "frontend_task" {
  name = "${var.name_prefix}-frontend-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}
