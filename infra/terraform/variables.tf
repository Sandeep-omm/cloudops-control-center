variable "enable_aws_resources" {
  description = "Set true only after reviewing the cost notes and supplying valid demo inputs."
  type        = bool
  default     = false
}

variable "enable_app_host" {
  description = "Set true to add a single EC2 host for the containerized demo."
  type        = bool
  default     = false
}

variable "aws_region" {
  description = "AWS region for the optional infrastructure example."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Short prefix used for named AWS resources."
  type        = string
  default     = "cloudops-demo"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,19}$", var.project_name))
    error_message = "project_name must be 3-20 lowercase letters, numbers, or hyphens and start with a letter."
  }
}

variable "db_username" {
  description = "Master username for this disposable demo database."
  type        = string
  default     = "cloudops_admin"
}

variable "db_instance_class" {
  description = "RDS instance class; availability and price vary by region and account."
  type        = string
  default     = "db.t4g.micro"
}

variable "db_multi_az" {
  description = "Enable RDS Multi-AZ for an HA demonstration; this can materially increase cost."
  type        = bool
  default     = false
}

variable "app_repo_url" {
  description = "Public HTTPS GitHub URL that the EC2 host clones at first boot."
  type        = string
  default     = "https://github.com/Sandeep-omm/cloudops-control-center.git"

  validation {
    condition     = can(regex("^https://github\\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\\.git$", var.app_repo_url))
    error_message = "app_repo_url must be an HTTPS GitHub repository URL ending in .git."
  }
}

variable "app_repo_branch" {
  description = "Branch containing the application and AWS Compose file."
  type        = string
  default     = "master"

  validation {
    condition     = can(regex("^[A-Za-z0-9._/-]+$", var.app_repo_branch))
    error_message = "app_repo_branch may contain only letters, numbers, dots, underscores, slashes, and hyphens."
  }
}

variable "vpc_cidr" {
  description = "CIDR range for the isolated demo VPC."
  type        = string
  default     = "10.42.0.0/16"
}

variable "tags" {
  description = "Additional default tags."
  type        = map(string)
  default     = { Owner = "portfolio" }
}
