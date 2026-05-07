Install self-managed argocd:
```bash
kubectl create ns argocd
kubectl apply -k bootstrap/argocd/base --server-side
```

Install apps:
```bash
kubectl apply -k bootstrap/workloads/base
```