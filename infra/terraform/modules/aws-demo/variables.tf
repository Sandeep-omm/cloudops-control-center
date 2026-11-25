variable "aws_region" {
  type = string
}

variable "project_name" {
  type = string
}

variable "db_username" {
  type = string
}

variable "db_instance_class" {
  type = string
}

variable "db_multi_az" {
  type = bool
}

variable "vpc_cidr" {
  type = string
}

variable "enable_app_host" {
  type = bool
}

variable "app_repo_url" {
  type = string
}

variable "app_repo_branch" {
  type = string
}
