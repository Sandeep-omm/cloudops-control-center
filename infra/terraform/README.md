# Optional AWS infrastructure example

This Terraform example describes the AWS mapping for CloudOps Control Center: a two-AZ VPC, isolated private database subnets, private PostgreSQL RDS, a private versioned S3 bucket, and an EC2 instance profile with prefix-scoped bucket permissions. An optional single EC2 host can run the API, worker, Prometheus, and Grafana containers.

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

## Optional EC2 app host

The host is disabled by default. The repository URL must be publicly cloneable because the one-time bootstrap script clones it at launch. The host has no inbound security-group rules or SSH key; it uses Systems Manager Session Manager. It receives an auto-assigned public IPv4 address only for outbound access to AWS Systems Manager, GitHub, and container registries, which can incur an hourly IPv4 charge. The EC2 instance and RDS instance can incur ongoing charges while running.

After applying the base stack and pushing the app deployment files to the configured GitHub branch, inspect the host plan:

```powershell
$env:AWS_PROFILE = "cloudops-demo"
terraform plan `
  -var="enable_aws_resources=true" `
  -var="enable_app_host=true" `
  -var="aws_region=ap-southeast-2" `
  -var="app_repo_url=https://github.com/Sandeep-omm/cloudops-control-center.git" `
  -var="app_repo_branch=master"
```

Review the proposed EC2 instance, SecureString parameters, and IAM policy changes before applying. Terraform creates a restricted `cloudops_app` database login; the RDS master credentials are used only by a one-shot bootstrap container. Generated passwords are stored in Terraform state, so keep that state private and never commit it. The EC2 user-data script contains no passwords; it retrieves secrets from SSM Parameter Store at boot, then passes the master credentials only to the bootstrap container.

After applying, wait for the instance to appear as **Online** in Systems Manager. Use the AWS CLI Session Manager plugin to forward the API port to your computer:

```powershell
$instanceId = terraform output -raw app_instance_id
aws ssm start-session --target $instanceId --document-name AWS-StartPortForwardingSession --parameters portNumber="8080",localPortNumber="8080" --profile cloudops-demo --region ap-southeast-2
```

While the session stays open, visit `http://localhost:8080`. Forward Grafana in a second PowerShell window using remote port `3001` and local port `3301` to avoid local port conflicts:

```powershell
aws ssm start-session --target $instanceId --document-name AWS-StartPortForwardingSession --parameters portNumber="3001",localPortNumber="3301" --profile cloudops-demo --region ap-southeast-2
```

Visit `http://localhost:3301`. Retrieve Grafana's generated password with `aws ssm get-parameter --name (terraform output -raw grafana_password_parameter) --with-decryption --query Parameter.Value --output text --profile cloudops-demo --region ap-southeast-2`; keep that value private.

### Update an existing EC2 demo host

The bootstrap script runs only when the host is initialized. After pushing the updated project to the configured branch, connect to the instance through an SSM shell and pull the code:

```bash
sudo git -C /opt/cloudops-control-center pull --ff-only origin master
```

Get the bucket name in the local Terraform directory with `terraform output -raw uploads_bucket`. Copy that non-secret bucket name into the SSM shell, then add the S3 settings and rebuild the application services:

```bash
sudo sed -i '/^OBJECT_STORAGE_BACKEND=/d;/^S3_BUCKET=/d;/^AWS_REGION=/d' /opt/cloudops-control-center/.env.app
sudo sh -c 'echo OBJECT_STORAGE_BACKEND=s3 >> /opt/cloudops-control-center/.env.app && echo S3_BUCKET=YOUR_BUCKET_NAME >> /opt/cloudops-control-center/.env.app && echo AWS_REGION=ap-southeast-2 >> /opt/cloudops-control-center/.env.app'
sudo chmod 0600 /opt/cloudops-control-center/.env.app
sudo docker compose --project-directory /opt/cloudops-control-center --file /opt/cloudops-control-center/compose.aws.yaml up --detach --build api worker
```

Replace `YOUR_BUCKET_NAME` with the Terraform output. The EC2 role already has the scoped permissions for the bucket’s `incoming/` and `results/` prefixes. After the redeploy, submit a small CSV through the API and confirm its result is available from `/api/v1/jobs/{job_id}/result`.

This is a single-node portfolio deployment, not a production high-availability service. The app has no user authentication, so keep access through Session Manager and do not add public inbound rules.

The initial database baseline preserves the local `jobs` table. The Terraform RDS instance is a separate, empty database; migrating application data to it is not automated. `terraform destroy` removes the demo resources and the RDS configuration skips the final snapshot, so treat any cloud data there as disposable.

To remove all demo resources after confirming the database and uploaded objects are disposable:

```powershell
terraform destroy `
  -var="enable_aws_resources=true" `
  -var="enable_app_host=true" `
  -var="aws_region=ap-southeast-2" `
  -var="app_repo_url=https://github.com/Sandeep-omm/cloudops-control-center.git" `
  -var="app_repo_branch=master"
```
