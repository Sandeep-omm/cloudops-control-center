# Local Kubernetes demo

This optional local cluster deployment runs PostgreSQL, the API, the worker, Prometheus, and Grafana. It uses a local persistent volume for uploads and results; the AWS deployment uses S3. No cloud resources are needed.

## Prerequisites

- Docker Desktop with the Linux engine running
- `kubectl`
- A working Kubernetes context, such as Docker Desktop Kubernetes or a local Minikube cluster
- `kustomize` support in `kubectl`

Check that a local cluster is selected and reachable:

```powershell
kubectl config current-context
kubectl cluster-info
```

If no context is set, enable Kubernetes in Docker Desktop settings or start a local cluster before continuing. These manifests are designed for a small single-node portfolio demo.

## Build and prepare secrets

Build the image on the same Docker engine used by the local cluster. With Minikube, load the image into its node after building:

```powershell
docker build -t cloudops-control-center:local .
minikube image load cloudops-control-center:local
```

Create the namespace and a local-only Kubernetes Secret. These demo values are only for a trusted local cluster; do not use them in AWS or a shared cluster.

```powershell
kubectl create namespace cloudops --dry-run=client -o yaml | kubectl apply -f -
kubectl create secret generic cloudops-secrets `
  --namespace cloudops `
  --from-literal=postgres-user=cloudops_app `
  --from-literal=postgres-password=local-dev-change-me `
  --from-literal=database-url=postgresql+psycopg://cloudops_app:local-dev-change-me@postgres:5432/cloudops `
  --from-literal=grafana-password=local-dev-grafana
```

## Deploy in dependency order

```powershell
kubectl apply -k deploy/kubernetes/00-database
kubectl wait --namespace cloudops --for=condition=Ready pod -l app=postgres --timeout=180s
kubectl apply -k deploy/kubernetes/01-migrate
kubectl wait --namespace cloudops --for=condition=complete job/cloudops-migrate --timeout=180s
kubectl apply -k deploy/kubernetes/02-app
kubectl apply -k deploy/kubernetes/03-monitoring
kubectl get pods,pvc,services --namespace cloudops
```

Open three PowerShell windows and keep each port-forward running:

```powershell
kubectl port-forward --namespace cloudops service/api 8080:8000
kubectl port-forward --namespace cloudops service/grafana 3001:3000
kubectl port-forward --namespace cloudops service/prometheus 9091:9090
```

Visit `http://localhost:8080`, `http://localhost:3001`, and `http://localhost:9091`. The Grafana username is `admin`; use the local-only password created in the Secret command. Submit the sample job and confirm it completes and appears in the metrics dashboard.

## Troubleshooting and cleanup

```powershell
kubectl get pods --namespace cloudops
kubectl describe pod --namespace cloudops <pod-name>
kubectl logs --namespace cloudops deployment/api
kubectl logs --namespace cloudops deployment/worker
kubectl logs --namespace cloudops job/cloudops-migrate
```

Remove workloads and the namespace when finished:

```powershell
kubectl delete namespace cloudops
```

Deleting the namespace also deletes its persistent volumes when the cluster's storage class uses a `Delete` reclaim policy. This deployment is for demonstrating Kubernetes primitives; it is not a production multi-node setup and does not enable public ingress, autoscaling, TLS, or authentication.
