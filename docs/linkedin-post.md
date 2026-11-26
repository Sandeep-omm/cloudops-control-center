# LinkedIn post draft

I built **CloudOps Control Center**, a cloud operations and data-processing demo that brings together backend development, infrastructure as code, containers, Kubernetes, CI/CD, and observability.

The app accepts CSV jobs through a FastAPI interface, stores job state in PostgreSQL, and processes work asynchronously with a separate worker. Prometheus collects service metrics and Grafana displays request and latency dashboards.

The project can run locally with Docker Compose or on a local Kubernetes cluster. Its optional AWS deployment is managed with Terraform and demonstrates a VPC, private RDS, S3-backed uploads and results, scoped IAM access, EC2, and Systems Manager access without opening application ports to the internet.

I also added automated tests and GitHub Actions checks for migrations, linting, compilation, container builds, and AWS Compose configuration.

This is a hands-on portfolio project, not a public production service. The repository includes setup instructions, architecture notes, security considerations, and known limitations.

Project repository: [add your GitHub repository link]

Next, I’m capturing a short walkthrough and verifying the end-to-end AWS S3 processing flow.

#CloudComputing #AWS #Kubernetes #Terraform #Docker #DevOps #Python #Observability
