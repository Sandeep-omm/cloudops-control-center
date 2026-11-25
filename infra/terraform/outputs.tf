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
  description = "Least-privilege EC2 instance profile for a future app host."
  value       = try(module.aws_demo[0].application_instance_profile, null)
}
