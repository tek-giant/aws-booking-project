# Booking application

This learning app replaces the nginx welcome page. It saves a description and GBP amount and lists the latest 100 bookings. Use fictional data: it has no user accounts and the existing ALB uses HTTP restricted to your public IP.

## Files

- app.py: routes, input validation, database access.
- templates/index.html: booking form and table.
- Dockerfile: packages the app; listens on port 80 to match existing ECS.
- requirements.txt: Python dependencies.
- test_app.py: tests using temporary local SQLite.

## Local preview first

From the project root (the directory containing infra and app), with Docker Desktop running:

```bash
docker build --platform linux/amd64 -t booking-demo:local ./app
docker run --rm --name booking-demo -p 127.0.0.1:8080:80 -e LOCAL_DEMO=1 booking-demo:local
```

Open http://localhost:8080. Enter a fictional booking, save, then refresh. Keep Terminal running. Press Ctrl+C to stop; local preview data is deleted when the container is removed.

This preview uses SQLite inside the container and makes no AWS calls. It does not prove PostgreSQL connectivity. Do not set LOCAL_DEMO on ECS.

## AWS configuration

Your existing ECS task already supplies DB_HOST, DB_NAME, DB_SECRET_ARN and AWS_REGION. The app retrieves credentials using its task role, connects to PostgreSQL with TLS certificate verification and creates its bookings table on first database access. It reads current credentials for each connection to accommodate secret rotation. SQL uses parameter binding; output is HTML-escaped.

The container listens on port 80, matching your current load balancer and ECS task. The / route exercises the database (503 on failure), and /health tests only the web process. Existing ALB checks on / therefore require database connectivity.

Before deployment, build and push a Linux amd64 image to the ECR repository output by Terraform, using a new immutable tag each time. The existing deploy-app GitHub workflow can deploy an existing image after its OIDC setup. We have not pushed or deployed this app yet.

Important: your ECS service has ignore_changes = [desired_count, task_definition]. Merely changing Terraform's image variable and applying will not update the running service. Deployment must explicitly update the ECS service to a new task definition revision (as the supplied GitHub workflow does).

For this demo, the app uses the existing RDS-managed master credentials. Before production use, add HTTPS, authentication, a restricted database user, explicit migrations and dependency locking. Two Gunicorn workers serve the app; schema initialization is serialized across replicas with a PostgreSQL transaction lock. Repeated saves create separate bookings; no idempotency or asynchronous worker is included.

## Tests without Docker

Use a virtual environment and install requirements.txt, then run `python -m unittest -v test_app.py` from this app folder. Tests cover persistence in the local store, amount validation, escaped output, cross-site form rejection and database failure handling. AWS/PostgreSQL integration must still be tested after deployment.

## References

- https://docs.aws.amazon.com/secretsmanager/latest/userguide/retrieving-secrets-python-sdk.html
- https://www.psycopg.org/psycopg3/docs/basic/install.html
