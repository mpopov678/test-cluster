# CLAUDE.md

GitOps repo for a homelab kubeadm cluster (AlmaLinux 10 VMs on 3 Proxmox nodes),
deployed by a self-managed Argo CD. `README.md` is the high-level overview for
humans; keep it high level (no IPs, specs or troubleshooting).

Detailed cluster facts (IPs, VM specs, versions, access, known issues, incident
log, recovery steps) live in [docs/cluster-details.md](docs/cluster-details.md).
Read it before working on the cluster, and update it when you learn something new
or a fact changes.

## Git workflow

- The user commits changes themselves. Never run `git commit`, `git push`, or
  anything else that creates commits or changes remotes.
- After making changes, suggest a commit message: a short summary line, then a
  blank line and a brief body when the change needs explaining.
- Work on a branch other than `main` when changes are substantial; creating or
  switching branches is fine.
- The repo is public on GitHub. Don't add secrets.

## Repo layout

- `bootstrap/argocd/`: Argo CD install (kustomize, pinned version) plus the
  `argocd` (self-managing) and `root-app` Applications.
- `apps/<name>/application.yaml`: one Argo CD Application per app. `root-app` picks
  these up via `include: '*/application.yaml'`.
- `apps/<name>/values.yaml`: Helm values for the upstream chart, read through a
  source with `ref: values`.
- `apps/<name>/manifests/`: plain YAML deployed alongside the chart. The `ref: values`
  source also carries the `path`, so each app has at most 2 sources.
- Every app Application has `syncPolicy.retry` (limit -1) so apps that need
  another app's CRDs recover on a fresh cluster. `argocd` and `root-app`
  deliberately have no retry and no finalizer.

## Cluster access

- Always pass `--kubeconfig ~/.kube/alma`; the default context is a different cluster.
- SSH as `root@<node-ip>`. Stick to read-only commands unless the user asks for changes.
