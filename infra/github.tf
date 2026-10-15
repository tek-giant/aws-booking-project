# Optional: supply BOTH values to enable the application deployment role.
variable "github_repository" {
  type        = string
  default     = ""
  description = "Exact GitHub owner/repository."
}
variable "github_oidc_provider_arn" {
  type        = string
  default     = ""
  description = "Existing AWS IAM OIDC provider for token.actions.githubusercontent.com."
}
resource "aws_iam_role" "github" {
  count = var.github_repository != "" && var.github_oidc_provider_arn != "" ? 1 : 0
  name  = "${local.name}-github-deploy"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = var.github_oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = { StringEquals = {
        "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        "token.actions.githubusercontent.com:sub" = "repo:tek-giant@302092145/aws-booking-project@1419860165:environment:${var.environment}"
      } }
    }]
  })
}
resource "aws_iam_role_policy" "github" {
  count = length(aws_iam_role.github)
  role  = aws_iam_role.github[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # ECR login requires a wildcard; image access stays limited to this repository.
      { Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*" },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability", "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart", "ecr:CompleteLayerUpload", "ecr:PutImage",
          "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer", "ecr:DescribeImages"
        ]
        Resource = aws_ecr_repository.app.arn
      },
      { Effect = "Allow", Action = ["ecs:DescribeServices", "ecs:UpdateService"], Resource = aws_ecs_service.app.id },
      { Effect = "Allow", Action = ["ecs:DescribeTaskDefinition", "ecs:RegisterTaskDefinition"], Resource = "*" },
      { Effect = "Allow", Action = ["iam:PassRole"], Resource = [aws_iam_role.execution.arn, aws_iam_role.task.arn], Condition = { StringEquals = { "iam:PassedToService" = "ecs-tasks.amazonaws.com" } } }
    ]
  })
}
output "github_deploy_role_arn" { value = try(aws_iam_role.github[0].arn, null) }
