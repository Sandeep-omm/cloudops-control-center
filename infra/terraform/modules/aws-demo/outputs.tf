output "vpc_id" {
  value = aws_vpc.main.id
}

output "private_subnet_ids" {
  value = [for subnet in aws_subnet.private : subnet.id]
}

output "database_endpoint" {
  value = aws_db_instance.database.address
}

output "uploads_bucket" {
  value = aws_s3_bucket.uploads.bucket
}

output "application_instance_profile" {
  value = aws_iam_instance_profile.application.name
}

output "app_instance_id" {
  value = try(aws_instance.application[0].id, null)
}

output "app_instance_public_ip" {
  value = try(aws_instance.application[0].public_ip, null)
}

output "grafana_password_parameter" {
  value = try(aws_ssm_parameter.grafana_password[0].name, null)
}
