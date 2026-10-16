# test-cluster

GitOps repo for a homelab Kubernetes cluster.

## Setup

- **Hardware:** a Proxmox datacenter with 3 Proxmox nodes.
- **VMs:** each Proxmox node runs one control-plane VM and one worker VM, all
  built from the AlmaLinux 10 cloud image. Losing one Proxmox node leaves the
  cluster running.
- Ansible package is used to configure alma for k8s

## GitOps layout

```
bootstrap/argocd/         Argo CD itself (kustomize), applied once by hand, then self-managed
  kustomization.yaml      pinned upstream install + patches
  argocd.yaml             Application that manages bootstrap/argocd (Argo CD manages itself)
  root-app.yaml           Application that picks up every apps/*/application.yaml
apps/<name>/
  application.yaml        the Argo CD Application (chart repo + version live here)
  values.yaml             Helm values for the upstream chart (optional)
  manifests/              extra plain YAML deployed alongside the chart (optional)
```

## Bootstrap

```bash
kubectl apply -k bootstrap/argocd --server-side
```

The first apply can fail on the `Application` objects because the CRDs aren't
established yet; rerun the same command once and it will succeed. From then on
Argo CD syncs itself and `root-app` from `main`.

## Adding an app

Create `apps/<name>/application.yaml` (copy an existing one), plus `values.yaml`
and/or `manifests/` as needed. `root-app` picks it up automatically.

## Upgrading Argo CD

Bump the `?ref=` in `bootstrap/argocd/kustomization.yaml` and push.
