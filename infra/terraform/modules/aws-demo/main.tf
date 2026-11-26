data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_ami" "al2023" {
  count       = var.enable_app_host ? 1 : 0
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
  filter {
    name   = "root-device-type"
    values = ["ebs"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

locals {
  availability_zones = slice(data.aws_availability_zones.available.names, 0, 2)
  deployment_name    = "${var.project_name}-${random_id.deployment.hex}"
  subnet_indexes = {
    for index, zone in local.availability_zones : zone => index
  }
}

resource "random_id" "deployment" {
  byte_length = 4
}

resource "random_password" "database" {
  length  = 32
  special = false
}

resource "random_password" "grafana" {
  count   = var.enable_app_host ? 1 : 0
  length  = 32
  special = false
}

resource "random_password" "app_database" {
  count   = var.enable_app_host ? 1 : 0
  length  = 32
  special = false
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "${local.deployment_name}-vpc" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${local.deployment_name}-igw" }
}

resource "aws_subnet" "public" {
  for_each = local.subnet_indexes

  vpc_id                  = aws_vpc.main.id
  availability_zone       = each.key
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, each.value)
  map_public_ip_on_launch = false
  tags                    = { Name = "${local.deployment_name}-public-${each.key}" }
}

resource "aws_subnet" "private" {
  for_each = local.subnet_indexes

  vpc_id            = aws_vpc.main.id
  availability_zone = each.key
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, each.value + 16)
  tags              = { Name = "${local.deployment_name}-private-${each.key}" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  tags = { Name = "${local.deployment_name}-public" }
}

resource "aws_route_table_association" "public" {
  for_each = aws_subnet.public

  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  for_each = local.subnet_indexes

  vpc_id = aws_vpc.main.id
  tags   = { Name = "${local.deployment_name}-private-${each.key}" }
}

resource "aws_route_table_association" "private" {
  for_each = aws_subnet.private

  subnet_id      = each.value.id
  route_table_id = aws_route_table.private[each.key].id
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [for table in aws_route_table.private : table.id]
  tags              = { Name = "${local.deployment_name}-s3-endpoint" }
}

resource "aws_security_group" "application" {
  name        = "${local.deployment_name}-application"
  description = "Network identity for future application compute; no inbound rules by default."
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${local.deployment_name}-application" }
}

resource "aws_vpc_security_group_egress_rule" "application_https" {
  security_group_id = aws_security_group.application.id
  description       = "HTTPS egress for package and AWS API access."
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_egress_rule" "application_database" {
  security_group_id            = aws_security_group.application.id
  description                  = "PostgreSQL egress to the RDS security group only."
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
  referenced_security_group_id = aws_security_group.database.id
}

resource "aws_security_group" "database" {
  name        = "${local.deployment_name}-database"
  description = "PostgreSQL is reachable only from the application security group."
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${local.deployment_name}-database" }
}

resource "aws_vpc_security_group_ingress_rule" "database_from_application" {
  security_group_id            = aws_security_group.database.id
  description                  = "PostgreSQL from the application security group only."
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
  referenced_security_group_id = aws_security_group.application.id
}

resource "aws_db_subnet_group" "database" {
  name       = "${local.deployment_name}-database"
  subnet_ids = [for subnet in aws_subnet.private : subnet.id]
  tags       = { Name = "${var.project_name}-database" }
}

resource "aws_db_parameter_group" "database" {
  name   = "${local.deployment_name}-postgres16"
  family = "postgres16"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  tags = { Name = "${local.deployment_name}-postgres16" }
}

resource "aws_db_instance" "database" {
  identifier                      = "${local.deployment_name}-db"
  engine                          = "postgres"
  engine_version                  = "16"
  instance_class                  = var.db_instance_class
  allocated_storage               = 20
  storage_type                    = "gp3"
  storage_encrypted               = true
  db_name                         = "cloudops"
  username                        = var.db_username
  password                        = random_password.database.result
  port                            = 5432
  db_subnet_group_name            = aws_db_subnet_group.database.name
  vpc_security_group_ids          = [aws_security_group.database.id]
  parameter_group_name            = aws_db_parameter_group.database.name
  publicly_accessible             = false
  multi_az                        = var.db_multi_az
  backup_retention_period         = 1
  auto_minor_version_upgrade      = true
  apply_immediately               = true
  deletion_protection             = false
  skip_final_snapshot             = true
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  tags = { Name = "${local.deployment_name}-db" }
}

resource "aws_s3_bucket" "uploads" {
  bucket = "${local.deployment_name}-uploads"
  tags   = { Name = "${local.deployment_name}-uploads" }
}

resource "aws_s3_bucket_public_access_block" "uploads" {
  bucket                  = aws_s3_bucket.uploads.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  rule {
    id     = "expire-demo-inputs"
    status = "Enabled"
    filter { prefix = "incoming/" }
    expiration { days = 7 }
    noncurrent_version_expiration { noncurrent_days = 7 }
  }

  rule {
    id     = "expire-demo-results"
    status = "Enabled"
    filter { prefix = "results/" }
    expiration { days = 30 }
    noncurrent_version_expiration { noncurrent_days = 30 }
  }
}

resource "aws_iam_role" "application" {
  name = "${local.deployment_name}-application"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = { Name = "${var.project_name}-application" }
}

resource "aws_iam_role_policy" "application_storage" {
  name = "${local.deployment_name}-object-access"
  role = aws_iam_role.application.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListRequiredPrefixes"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = aws_s3_bucket.uploads.arn
        Condition = {
          StringLike = { "s3:prefix" = ["incoming/*", "results/*"] }
        }
      },
      {
        Sid    = "ManageDemoObjects"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = [
          "${aws_s3_bucket.uploads.arn}/incoming/*",
          "${aws_s3_bucket.uploads.arn}/results/*",
        ]
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "application_ssm_core" {
  count      = var.enable_app_host ? 1 : 0
  role       = aws_iam_role.application.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_ssm_parameter" "database_url" {
  count       = var.enable_app_host ? 1 : 0
  name        = "/${var.project_name}/${random_id.deployment.hex}/database-url"
  description = "Encrypted connection string for the portfolio app host."
  type        = "SecureString"
  value       = "postgresql+psycopg://cloudops_app:${random_password.app_database[0].result}@${aws_db_instance.database.address}:5432/${aws_db_instance.database.db_name}?sslmode=require"
  tier        = "Standard"

  tags = { Name = "${local.deployment_name}-database-url" }
}

resource "aws_ssm_parameter" "database_admin_url" {
  count       = var.enable_app_host ? 1 : 0
  name        = "/${var.project_name}/${random_id.deployment.hex}/database-admin-url"
  description = "Encrypted one-time bootstrap connection string for the demo database."
  type        = "SecureString"
  value       = "postgresql://${var.db_username}:${random_password.database.result}@${aws_db_instance.database.address}:5432/${aws_db_instance.database.db_name}?sslmode=require"
  tier        = "Standard"

  tags = { Name = "${local.deployment_name}-database-admin-url" }
}

resource "aws_ssm_parameter" "app_database_password" {
  count       = var.enable_app_host ? 1 : 0
  name        = "/${var.project_name}/${random_id.deployment.hex}/app-database-password"
  description = "Encrypted restricted application database password."
  type        = "SecureString"
  value       = random_password.app_database[0].result
  tier        = "Standard"

  tags = { Name = "${local.deployment_name}-app-database-password" }
}

resource "aws_ssm_parameter" "grafana_password" {
  count       = var.enable_app_host ? 1 : 0
  name        = "/${var.project_name}/${random_id.deployment.hex}/grafana-password"
  description = "Encrypted Grafana administrator password for the portfolio app host."
  type        = "SecureString"
  value       = random_password.grafana[0].result
  tier        = "Standard"

  tags = { Name = "${local.deployment_name}-grafana-password" }
}

resource "aws_iam_role_policy" "application_runtime" {
  count = var.enable_app_host ? 1 : 0
  name  = "${local.deployment_name}-runtime-secrets"
  role  = aws_iam_role.application.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadApplicationDatabaseUrl"
        Effect = "Allow"
        Action = ["ssm:GetParameter"]
        Resource = [
          aws_ssm_parameter.database_url[0].arn,
          aws_ssm_parameter.database_admin_url[0].arn,
          aws_ssm_parameter.app_database_password[0].arn,
          aws_ssm_parameter.grafana_password[0].arn,
        ]
      },
      {
        Sid      = "DecryptOnlyApplicationParameterViaSsm"
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = "ssm.${var.aws_region}.amazonaws.com"
            "kms:EncryptionContext:PARAMETER_ARN" = [
              aws_ssm_parameter.database_url[0].arn,
              aws_ssm_parameter.database_admin_url[0].arn,
              aws_ssm_parameter.app_database_password[0].arn,
              aws_ssm_parameter.grafana_password[0].arn,
            ]
          }
        }
      }
    ]
  })
}

resource "aws_instance" "application" {
  count                       = var.enable_app_host ? 1 : 0
  ami                         = data.aws_ami.al2023[0].id
  instance_type               = "t3.small"
  subnet_id                   = values(aws_subnet.public)[0].id
  vpc_security_group_ids      = [aws_security_group.application.id]
  iam_instance_profile        = aws_iam_instance_profile.application.name
  associate_public_ip_address = true
  monitoring                  = false
  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    aws_region                  = jsonencode(var.aws_region)
    app_repo_url                = jsonencode(var.app_repo_url)
    app_repo_branch             = jsonencode(var.app_repo_branch)
    database_param              = jsonencode(aws_ssm_parameter.database_url[0].name)
    database_admin_param        = jsonencode(aws_ssm_parameter.database_admin_url[0].name)
    app_database_password_param = jsonencode(aws_ssm_parameter.app_database_password[0].name)
    grafana_param               = jsonencode(aws_ssm_parameter.grafana_password[0].name)
    uploads_bucket              = jsonencode(aws_s3_bucket.uploads.bucket)
  })

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }

  root_block_device {
    volume_size           = 20
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  tags = { Name = "${local.deployment_name}-application" }

  depends_on = [
    aws_iam_role_policy_attachment.application_ssm_core,
    aws_iam_role_policy.application_runtime,
    aws_ssm_parameter.database_url,
    aws_ssm_parameter.database_admin_url,
    aws_ssm_parameter.app_database_password,
    aws_ssm_parameter.grafana_password,
  ]
}

resource "aws_iam_instance_profile" "application" {
  name = "${local.deployment_name}-application"
  role = aws_iam_role.application.name
  tags = { Name = "${local.deployment_name}-application" }
}
