environment   = "development"
region        = "us-east-1"
desired_count = 1
# Replace these before running a plan.
alert_email       = "tekgiant2026@gmail.com"
allowed_http_cidr = "81.78.79.224/32"
# Default image shows an nginx welcome page. Set your real image later.
# image = "123456789012.dkr.ecr.us-east-1.amazonaws.com/three-tier-development:COMMIT_SHA"
github_repository = "tek-giant/aws-booking-project"
github_oidc_provider_arn = "arn:aws:iam::743978812281:oidc-provider/token.actions.githubusercontent.com"

