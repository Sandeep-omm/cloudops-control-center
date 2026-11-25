output "vpc_id" {
  description = "Demo VPC ID (null while resource creation is disabled)."
  value       = try(module.aws_demo[0].vpc_id, null)
}

output "private_subnet_ids" {
  description = "Private subnet IDs for the database and future application tasks."
  value       = try(module.aws_demo[0].private_subnet_ids, null)
}

output "database_endpoint" {
  description = "Private PostgreSQL endpoint. Not publicly accessible."
  value       = try(module.aws_demo[0].database_endpoint, null)
}

output "uploads_bucket" {
  description = "Private bucket for incoming and result objects."
  value       = try(module.aws_demo[0].uploads_bucket, null)
}

output "application_instance_profile" {
  description = "EC2 app instance profile with scoped S3, SSM, and encrypted parameter access."
  value       = try(module.aws_demo[0].application_instance_profile, null)
}

output "app_instance_id" {
  description = "SSM-managed EC2 host ID (null unless app hosting is enabled)."
  value       = try(module.aws_demo[0].app_instance_id, null)
}

output "app_instance_public_ip" {
  description = "Public IP for outbound-only EC2 connectivity (null unless app hosting is enabled)."
  value       = try(module.aws_demo[0].app_instance_public_ip, null)
}

output "grafana_password_parameter" {
  description = "SSM parameter name for the encrypted Grafana login password."
  value       = try(module.aws_demo[0].grafana_password_parameter, null)
}
