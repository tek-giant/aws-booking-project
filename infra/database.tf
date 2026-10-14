resource "aws_db_subnet_group" "main" {
  name       = local.name
  subnet_ids = aws_subnet.private[*].id
}
resource "aws_db_instance" "main" {
  identifier                  = local.name
  engine                      = "postgres"
  instance_class              = var.db_instance_class
  allocated_storage           = 20
  storage_type                = "gp3"
  storage_encrypted           = true
  db_name                     = "appdb"
  username                    = "appadmin"
  manage_master_user_password = true
  db_subnet_group_name        = aws_db_subnet_group.main.name
  vpc_security_group_ids      = [aws_security_group.db.id]
  publicly_accessible         = false
  multi_az                    = local.production
  backup_retention_period     = local.production ? 14 : 7
  deletion_protection         = local.production
  skip_final_snapshot         = !local.production
  final_snapshot_identifier   = "${local.name}-final"
  copy_tags_to_snapshot       = true
}
