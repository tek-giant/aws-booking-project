variable "region" { default = "eu-west-2" }
variable "environment" {
  type = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Choose development, staging or production."
  }
}
variable "image" {
  default     = "public.ecr.aws/docker/library/nginx:stable"
  description = "Default is only a welcome-page smoke test. Replace with your app image."
}
variable "container_port" { default = 80 }
variable "health_check_path" { default = "/" }
variable "desired_count" { default = 1 }
variable "db_instance_class" { default = "db.t3.micro" }
variable "alert_email" {
  type        = string
  description = "Confirm the SNS subscription email after apply."
}
variable "allowed_http_cidr" {
  type        = string
  description = "Your public IP with /32, e.g. 203.0.113.10/32."
}
locals {
  name       = "three-tier-${var.environment}"
  production = var.environment == "production"
}
