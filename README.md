Install self-managed argocd:
kubectl create ns argocd
kubectl apply -k bootstrap/argocd/base --server-side

Install apps:
kubectl apply -k bootstrap/workloads/base