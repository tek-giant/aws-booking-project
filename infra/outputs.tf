output "website_url" { value = "http://${aws_lb.main.dns_name}" }
output "ecr_repository" { value = aws_ecr_repository.app.repository_url }
output "database_host" { value = aws_db_instance.main.address }
output "database_secret_arn" { value = aws_db_instance.main.master_user_secret[0].secret_arn }
output "ecs_cluster" { value = aws_ecs_cluster.main.name }
output "ecs_service" { value = aws_ecs_service.app.name }
