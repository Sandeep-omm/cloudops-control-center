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
