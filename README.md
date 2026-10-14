# Simple AWS three-tier starter

Start with **development**. These files create real AWS resources and incur AWS charges, including NAT, ALB, Fargate and RDS. Nothing has been deployed by creating these files.

## What this starter does

Browser → public Application Load Balancer → private ECS Fargate container → private PostgreSQL RDS database.

The initial container is an nginx welcome page to test the ALB and container networking. It does **not** connect to PostgreSQL and does not implement bookings, expenses, invoices, SQS or a worker. Your actual application code was not supplied.

Your description mixed EC2 Auto Scaling Groups and ECS. This starter chooses **ECS Fargate**, with task autoscaling and no EC2 Auto Scaling Group. It uses two availability zones, one NAT gateway, one state per environment, and flat files instead of modules to keep it easy to follow.

## Files

| File | Purpose |
| --- | --- |
| bootstrap/main.tf | Creates the encrypted, versioned S3 state bucket and KMS key |
| infra/versions.tf | Terraform/provider requirements and S3 backend |
| infra/variables.tf | Settings you can change |
| infra/network.tf | VPC, public/private subnets, NAT, security groups |
| infra/database.tf | Private PostgreSQL with managed password and backups |
| infra/application.tf | ECR, ALB, ECS, IAM roles, logging and autoscaling |
| infra/monitoring.tf | CPU alarm and email subscription |
| infra/github.tf | Optional GitHub OIDC application deployment role |
| infra/environments/ | Separate environment values and backend examples |
| .github/workflows/validate.yml | Formatting and validation on push/PR |
| .github/workflows/deploy-app.yml | Manually deploys an existing container image |

## 1. Prerequisites

Install Terraform 1.10 or newer (below 2.0) and AWS CLI v2. The supplied CI uses Terraform 1.14.6. AWS provider is constrained to 5.x. This corrects the original `require_version` spelling to `required_version` and sets a minimum that supports S3 native locking.

Authenticate using your AWS profile/SSO and check the account:

```bash
aws sso login --profile YOUR_PROFILE
export AWS_PROFILE=YOUR_PROFILE
aws sts get-caller-identity
```

Use an identity authorized to provision the resources in these files. The optional GitHub role only deploys application revisions; it cannot provision infrastructure.

## 2. Create the state bucket once

Run from this starter's root folder. Replace the example bucket name with a globally unique name:

```bash
terraform -chdir=bootstrap init
terraform -chdir=bootstrap plan -var='bucket_name=YOUR_UNIQUE_STATE_BUCKET' -out=bootstrap.tfplan
terraform -chdir=bootstrap apply bootstrap.tfplan
terraform -chdir=bootstrap output
```

Save the bucket name and KMS key ARN. Bootstrap uses local state: keep bootstrap/terraform.tfstate securely backed up, outside Git. Do not delete the bootstrap directory after applying it. The bucket/key have destruction protection.

## 3. Fill in development settings

Edit `infra/environments/development.tfvars`:

- `alert_email`: your email address.
- `allowed_http_cidr`: your public IPv4 address followed by `/32`. The example address will not allow your browser through.
- Keep the default image and port for the first welcome-page test.

Copy the backend example:

```bash
cp infra/environments/development.s3.tfbackend.example infra/environments/development.s3.tfbackend
```

Edit the new file and replace the bucket and KMS placeholders with bootstrap outputs. Keep its `development/terraform.tfstate` key. Backend region must match the state bucket region.

## 4. Preview and create the infrastructure

```bash
terraform -chdir=infra init -backend-config=environments/development.s3.tfbackend
terraform fmt -check -recursive
terraform -chdir=infra validate
terraform -chdir=infra plan -var-file=environments/development.tfvars -out=development.tfplan
terraform -chdir=infra apply development.tfplan
terraform -chdir=infra output website_url
```

Review the plan before applying it. RDS creation can take several minutes. Open the output URL from the IP you allowed; expect the nginx welcome page. Confirm the SNS subscription email to enable alerts. In AWS, check ECS service tasks, healthy ALB targets and `/ecs/three-tier-development` logs.

Both `.terraform.lock.hcl` files are included, selecting AWS provider 5.100.0. Commit them with the configuration. Never commit state, saved plans, passwords or AWS credentials.

## 5. Connect your real application

Your image must run Linux x86_64, listen on `0.0.0.0` at `container_port`, and answer `health_check_path` successfully without authentication. Configure those Terraform variables to match the app **before its first deployment**.

The task provides `DB_HOST`, `DB_NAME`, `DB_SECRET_ARN` and `AWS_REGION`. Your application must use its AWS task role to read the Secrets Manager JSON at `DB_SECRET_ARN`, obtain `username` and `password`, and connect on port 5432 with TLS. The nginx image ignores these variables. Runtime secret retrieval supports RDS-managed password rotation if the app refreshes credentials appropriately. For a real application, create a separate restricted database user rather than using the master user.

Build and push your application image into the ECR repository returned by Terraform. No Dockerfile is included because your application and dependencies are unknown. Use an immutable commit tag or digest. ECR scan-on-push is enabled; this starter does not automatically block deployments on scan findings.

## 6. Optional GitHub deployment

1. Put the starter files at your repository root, including the hidden `.github` directory.
2. In AWS IAM, create or reuse the GitHub OIDC provider: URL `https://token.actions.githubusercontent.com`, audience `sts.amazonaws.com`. Do not create a duplicate if your account already has one.
3. Set `github_repository = "OWNER/REPO"` and `github_oidc_provider_arn = "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"` in the environment tfvars. Plan/apply again.
4. Create GitHub environments named development, staging and production. In each, set variables `AWS_DEPLOY_ROLE_ARN` to its Terraform output and `AWS_REGION` to `eu-west-2`. Restrict deployment branches to main and configure required reviewers for production before using it.
5. Run **Deploy existing application image** from GitHub Actions and provide the environment and existing image URI.

The role trusts only the specified repo and GitHub environment. It can update this ECS service, register/describe task definitions (which need wildcard resource access here), and pass only the two ECS roles. No long-lived AWS keys are used. It does not push images or provision infrastructure.

Terraform creates the initial task definition; after that the application workflow owns service task revisions. Terraform ignores service `task_definition` changes to avoid undoing deployments. If you change task settings (ports, environment, roles, CPU, etc.) in Terraform, apply them, then explicitly update the ECS service to the new Terraform-created task definition before using the image-only deployment workflow. Run infrastructure and application deployments separately, never concurrently.

The workflow waits for stability and fails if ECS rolled back instead of deploying the requested revision. A failed initial deployment has no previous healthy revision to roll back to.

## Other environments

Copy and fill in each environment's backend example and tfvars. Use a separate working copy per environment to avoid accidentally switching state. Each uses a different state key and resource names. Production enables two tasks, multi-AZ RDS, longer backups and database deletion protection, but remains a teaching starter, not a complete production design.

## Scope and deliberate simplifications

- HTTP is limited to your configured IP for testing. Add an ACM certificate and HTTPS listener before real use or sensitive traffic.
- One NAT gateway is cheaper/simpler but is an availability dependency across both zones.
- Built-in RDS automated backups are included. AWS Backup, cross-region replication and restore testing are not implemented.
- CloudWatch application logs and a CPU email alarm are included. Broader availability/database alarms are not.
- CI validates Terraform. Automated infrastructure plan/apply, Checkov, Trivy, TFLint, application tests and Docker image builds require additional setup and are not claimed as implemented.
- This is an AWS starter, not local Docker Compose testing. An AWS account is required to apply it.

## Clean up development resources

First inspect the destroy plan, then apply it only when you intend to delete the environment:

```bash
terraform -chdir=infra plan -destroy -var-file=environments/development.tfvars -out=destroy.tfplan
terraform -chdir=infra apply destroy.tfplan
```

Development/staging skip final DB snapshots, so make a manual snapshot first if you need the data. ECR repositories containing images must be emptied deliberately before deletion. Production has RDS deletion protection. The bootstrap state bucket and KMS key remain protected and are not destroyed with the environment.

## Reference

- S3 backend and locking: https://developer.hashicorp.com/terraform/language/backend/s3
- ECS service and circuit breaker: https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecs_service

## Validation performed

Terraform 1.14.6: `terraform fmt -check -recursive` passed, and `terraform validate` passed for both bootstrap and infra with AWS provider 5.100.0. No AWS plan, apply, application test or GitHub workflow run was performed. Account-specific settings and runtime behavior still need testing.
