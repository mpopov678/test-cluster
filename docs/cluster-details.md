# Cluster details

Detailed reference for the cluster described in the top-level README. Facts here
were read from the running nodes on 2026-10-16; re-check them before relying on
them.

## Proxmox

| Proxmox host | IP | VMs |
|---|---|---|
| ? | 192.168.88.5 | ? |
| ? | 192.168.88.6 | ? |
| ? | 192.168.88.7 | ? |

Host names and VM placement are unknown; each host runs one control plane and
one worker. During the 2026-10-16 outage cp1+w1 and cp3+w3 went down together,
which suggests cpN and wN share a host (unconfirmed).

## VMs

AlmaLinux 10.2 GenericCloud image, configured by Proxmox cloud-init.

| Role | Name | IP | vCPU | RAM | Disks |
|---|---|---|---|---|---|
| control plane | alma-cp1 | 192.168.88.101 | 2 | 4 GB | 60 GB |
| control plane | alma-cp2 | 192.168.88.102 | 2 | 4 GB | 60 GB |
| control plane | alma-cp3 | 192.168.88.103 | 2 | 4 GB | 60 GB |
| worker | alma-w1 | 192.168.88.16 | 4 | 16 GB | 60 GB + 100 GB (sdb) |
| worker | alma-w2 | 192.168.88.17 | 4 | 16 GB | 60 GB + 100 GB (sdb) |
| worker | alma-w3 | 192.168.88.19 | 4 | 16 GB | 60 GB + 100 GB (sdb) |

Node OS settings:
- swap off, containerd with `SystemdCgroup = true`
- SELinux permissive
- firewalld on; `192.168.88.0/24` is in the `trusted` zone (all LAN traffic allowed)
- `qemu-guest-agent` installed but not running

## Network

| Address | What |
|---|---|
| 192.168.88.1 | router / default gateway |
| 192.168.88.2 | DNS; RFC2136 target for external-dns (zone `lab.mpopov.net`) |
| 192.168.88.5-7 | Proxmox hosts (web UI on :8006) |
| 192.168.88.100 | Kubernetes API VIP (kube-vip, ARP), `https://192.168.88.100:6443` |
| 192.168.88.101-103 | control-plane nodes |
| 192.168.88.16, .17, .19 | worker nodes |
| 192.168.88.110-120 | Cilium LoadBalancer IP pool (L2 announcements) |
| 192.168.88.110 | Gateway `eg` (namespace `networking`), `*.lab.mpopov.net` HTTPS |
| 10.244.0.0/16 | pod network (Cilium cluster-pool IPAM, /24 per node, VXLAN) |
| 10.96.0.0/12 | service network |

The Cilium LB pool must never include the VIP (`.100`), or Cilium and kube-vip
both answer ARP for it.

## Kubernetes

| Component | Version / setting |
|---|---|
| Kubernetes (kubeadm) | v1.36.5 |
| etcd | 3.6.8, stacked (one member per control plane) |
| containerd | 2.4.2 |
| kube-vip | v1.2.4, static pod on each control plane, control-plane VIP only |
| Cilium | v1.20.2: kube-proxy replacement, VXLAN tunnel, L2 announcements, Gateway API (`cilium` GatewayClass) |
| CoreDNS | v1.14.2 |
| Storage | CubeFS CSI, `cfs-sc` (default StorageClass) |

Installed by hand, not in this repo: kube-vip (`/etc/kubernetes/manifests/kube-vip.yaml`,
copy in `/root/kube-vip.yaml`), Cilium, CubeFS, Gateway API CRDs.

## Access

- kubeconfig: `~/.kube/alma` (server `https://192.168.88.100:6443`). The default
  kubectl context points at a different (Omni/Talos) cluster, so always pass
  `--kubeconfig ~/.kube/alma`.
- SSH: `root@<node-ip>` works with the admin machine's key (verified on cp2 and w2).
  `mpopov@` and `almalinux@` are rejected.
- Proxmox hosts: no SSH key access from the admin machine.

## Known issues

- **Node IPs come from DHCP** (`ipv4.method: auto`). etcd and the apiserver bind
  to the node IP; a late lease at boot gives `bind: cannot assign requested address`.
  Fix: static IPs in each VM's Proxmox cloud-init
  (`ipconfig0: ip=192.168.88.101/24,gw=192.168.88.1`), or DHCP reservations.
- **kube-vip has `dhcp_mode=ipv4`** set alongside a static `address`; it should be
  removed on all three control planes.
- **`qemu-guest-agent` not running**: enable it and the agent option in Proxmox so
  VMs shut down cleanly and backups can freeze filesystems.
- **Two Proxmox hosts down = cluster down** (etcd needs 2 of 3).
- **kube-apiserver restart counts in the thousands** (~3,500 in 14 days as of
  2026-10-15), caused by etcd losing quorum/peers. Not caused by memory (no OOM)
  or disk (etcd WAL fsync < 32 ms).
- **Talos leftovers**: Longhorn values use the Talos path `/var/mnt/longhorn`, and
  Longhorn's `sc1` is marked default while `cfs-sc` already is. Longhorn is not
  currently installed; storage choice is undecided.
- **Plaintext credentials in this public repo** (external-dns TSIG key, RustFS keys,
  default Harbor/Grafana/RustFS admin passwords). They need rotating and moving to
  Secrets.

## Incident log

- **2026-10-15 ~19:10 UTC**: all six nodes rebooted at the same time; apiservers
  had been crashlooping because etcd failed to bind the node IP at boot (DHCP).
- **2026-10-16 14:22:21 UTC**: cp1, cp3, w1, w3 dropped off the network together
  (ARP incomplete from cp2), Proxmox hosts still up. etcd on cp2 lost quorum, so
  the API was down. Cause not yet found; suspects are Proxmox HA fencing (corosync
  quorum loss) or a stop-mode backup job.

## When the API is down

```bash
# Are the VMs up? (from the admin machine)
for ip in 101 102 103 16 17 19; do ping -c1 -W1 192.168.88.$ip >/dev/null && echo "$ip up" || echo "$ip DOWN"; done

# On a control plane: etcd health / quorum
crictl exec $(crictl ps --name etcd -q) etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key endpoint status --cluster -w table
```

If two control planes are down, start their VMs in Proxmox; etcd regains quorum
and the apiservers recover on their own. Never force a single-member etcd unless
the other two are permanently lost.
