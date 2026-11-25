# Optional AWS infrastructure example

This Terraform example describes the AWS mapping for CloudOps Control Center: a two-AZ VPC, isolated private database subnets, private PostgreSQL RDS, a private versioned S3 bucket, and an EC2 instance profile with prefix-scoped bucket permissions.

## Safe default

Resource creation is **disabled by default**. The local Docker Compose application does not need AWS credentials or this stack. The initial Terraform plan should create no AWS resources.

```powershell
Copy-Item terraform.tfvars.example terraform.tfvars
terraform init
terraform fmt -check -recursive
terraform validate
terraform plan -var-file=terraform.tfvars
```

To inspect the resource plan, first review the code and cost notes, then change `enable_aws_resources` to `true`. Terraform generates a unique bucket suffix and a database password. Do not commit Terraform state: it contains the generated password even though Terraform marks it sensitive.

This project does **not** automatically deploy the infrastructure. Do not run `terraform apply` unless you have reviewed the plan and are prepared for charges. RDS instance hours, storage, backups, CloudWatch log ingestion, S3 usage, and public networking charges depend on account, region, and usage. New Free Tier benefits are account-plan and credit based; they do not guarantee that this architecture will cost zero. Check current [AWS Free Tier terms](https://aws.amazon.com/free/) and [RDS pricing](https://aws.amazon.com/rds/pricing/) before enabling resources.

The example omits NAT gateways to avoid a recurring networking cost. Private subnets have no general internet route; the S3 gateway endpoint allows private S3 traffic. The RDS instance is not public, requires SSL, uses encrypted storage, and only accepts PostgreSQL connections from the application security group. Multi-AZ is configurable but disabled by default due to added cost.

The initial database baseline preserves the local `jobs` table. The Terraform RDS instance is a separate, empty database; migrating application data to it is not automated. `terraform destroy` removes the demo resources and the RDS configuration skips the final snapshot, so treat any cloud data there as disposable.
