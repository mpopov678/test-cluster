# Data Lake prerequisites

The data lake charts do not commit credentials and do not use ExternalSecrets. Create the required secrets before syncing the Argo CD data-lake applications.

Replace all angle-bracket placeholders before running these commands.

```bash
for ns in lakehouse spark unity-catalog iceberg trino; do
  kubectl create namespace "$ns" --dry-run=client -o yaml | kubectl apply -f -
  kubectl -n "$ns" create secret generic lakehouse-s3 \
    --from-literal=AWS_ACCESS_KEY_ID='admin' \
    --from-literal=AWS_SECRET_ACCESS_KEY='admin' \
    --dry-run=client -o yaml | kubectl apply -f -
done

kubectl create namespace iceberg --dry-run=client -o yaml | kubectl apply -f -
kubectl -n iceberg create secret generic nessie-db-app \
  --from-literal=username=nessie \
  --from-literal=password='admin' \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create namespace superset --dry-run=client -o yaml | kubectl apply -f -
kubectl -n superset create secret generic superset-db-app \
  --from-literal=username=superset \
  --from-literal=password='admin' \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n superset create secret generic superset-env \
  --from-literal=SUPERSET_SECRET_KEY='admin' \
  --from-literal=DB_USER=superset \
  --from-literal=DB_PASS='admin' \
  --from-literal=SQLALCHEMY_DATABASE_URI='postgresql+psycopg2://superset:admin@superset-db-rw.superset.svc.cluster.local:5432/superset?sslmode=require' \
  --from-literal=REDIS_HOST=valkey.valkey.svc.cluster.local \
  --from-literal=REDIS_PORT=6379 \
  --dry-run=client -o yaml | kubectl apply -f -
```
