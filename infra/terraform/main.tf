module "aws_demo" {
  count  = var.enable_aws_resources ? 1 : 0
  source = "./modules/aws-demo"

  aws_region        = var.aws_region
  project_name      = var.project_name
  db_username       = var.db_username
  db_instance_class = var.db_instance_class
  db_multi_az       = var.db_multi_az
  vpc_cidr          = var.vpc_cidr
}
