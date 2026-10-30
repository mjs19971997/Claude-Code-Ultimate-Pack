# Upgrades and Operations

Reference for release support, version skew, deprecated API scanning, upgrade runbooks, debugging and backups. Verified against the Kubernetes release schedule and version skew policy (supported minors on 2026-10-30: 1.37, 1.36, 1.35; 1.34 reached end of life on 2026-10-27) (2026-10).

## 1. Release support

| Minor | Released | End of life |
|---|---|---|
| 1.37 | 2026-08-26 | 2027-10-28 |
| 1.36 | 2026-04-22 | 2027-06-28 |
| 1.35 | 2025-12-17 | 2027-02-28 |
| 1.34 | 2025-08-27 | 2026-10-27 (ended) |
| 1.33 and older | | 1.33 ended 2026-06-28; 1.32 ended 2026-02-28; 1.31 and 1.30 ended in 2025 |

- The project maintains release branches for the three most recent minors, with about 14 months from release to end of life (a maintenance-mode period in the last two months). Security fixes are backported only to these branches.
- Roughly three minors per year. Plan one upgrade every four to six months to stay inside the window.
- Managed services (EKS, GKE, AKS) have their own calendars and often keep a version available longer, sometimes at extra cost, or force-upgrade at the end. Check the provider's page, not the upstream table, for the date that matters to you.
- Source of truth: the release schedule at kubernetes.io/releases and the patch release page. Re-check before quoting dates.

## 2. Version skew

- kube-apiserver: in an HA control plane, instances may differ by at most one minor.
- kubelet: not newer than kube-apiserver; up to three minors older.
- kube-proxy: not newer than kube-apiserver; up to three minors older, and within three minors of the kubelet on the same node.
- kube-controller-manager, kube-scheduler, cloud-controller-manager: not newer than kube-apiserver, at most one minor older.
- kubectl: within one minor of kube-apiserver, older or newer.

Consequence: upgrade the control plane one minor at a time, then nodes. A node pool may skip minors only within the skew limit, but replacing nodes with new images (rather than in-place upgrades) is the cleaner path. Update to the latest patch of the current minor before starting, and move to the latest patch of the target.

## 3. Find removed and deprecated APIs

Do this before every upgrade, against three sources: manifests in Git, rendered Helm charts, and live API clients.

```bash
# Manifests and rendered charts (pluto, from Fairwinds)
pluto detect-files -d ./manifests --target-versions k8s=v1.37.0
helm template ./chart | pluto detect - --target-versions k8s=v1.37.0
pluto detect-helm -o wide --target-versions k8s=v1.37.0     # releases already installed

# Live clients still calling deprecated APIs (API server metric)
kubectl get --raw /metrics | grep apiserver_requested_deprecated_apis

# Schema check with the target version
kubeconform -strict -kubernetes-version 1.37.0 -summary ./manifests
```

The `apiserver_requested_deprecated_apis` series carries `group`, `version`, `resource` and `removed_release` labels; the audit log annotation `k8s.io/deprecated` identifies the caller. Fix the caller (an old CI tool, an operator, a controller) rather than the object. The official Deprecated API Migration Guide lists each removal and its replacement; at the time of writing the last removal listed is `flowcontrol.apiserver.k8s.io/v1beta3` in 1.32. Check the guide for your target version, and for the feature gates and CRDs your add-ons use.

Commonly met removals from older releases, in case old manifests surface: `extensions/v1beta1` and `networking.k8s.io/v1beta1` Ingress (use `networking.k8s.io/v1`, `pathType` required), `policy/v1beta1` PodDisruptionBudget (use `policy/v1`), `autoscaling/v2beta1` and `v2beta2` HPA (use `autoscaling/v2`), `batch/v1beta1` CronJob (use `batch/v1`), and PodSecurityPolicy (use Pod Security Admission).

## 4. Pre-upgrade checklist

1. Read the release notes ("Urgent upgrade notes" and "Deprecation") for every minor between current and target.
2. Check that add-ons support the target: CNI, CSI drivers, CoreDNS, kube-proxy replacement, metrics-server, cert-manager, Gateway API controller and CRD version, GitOps tool, service mesh, autoscalers, policy engines, operators.
3. Confirm admission webhooks tolerate the new API server (they use `admissionregistration.k8s.io/v1` and a valid serving certificate), and set `failurePolicy` deliberately.
4. Back up: etcd snapshot (self-managed), cluster objects and volumes (Velero or the provider's tool). Test a restore at least once.
5. Check PodDisruptionBudgets will not block drains: `kubectl get pdb -A` and look for `ALLOWED DISRUPTIONS` of 0.
6. Check capacity: surge nodes or spare room so drains can reschedule.
7. Rehearse on a staging cluster built from the same GitOps repo.
8. Announce a window, freeze deployments, and have a rollback plan. Control plane minor upgrades are not reversible in place; the rollback is a restore or a new cluster, so the rehearsal and the backup matter.

## 5. Upgrade runbook (kubeadm clusters)

Managed clusters: use the provider's upgrade path for the control plane, then roll node pools (new node image, surge, cordon, drain), and read the provider's notes for add-on versions. The self-managed sequence:

```bash
# First control plane node (package repo is per minor: pkgs.k8s.io/.../v1.36/)
sudo apt-get update && sudo apt-get install -y kubeadm='1.36.x-*'
kubeadm version
sudo kubeadm upgrade plan
sudo kubeadm upgrade apply v1.36.x

# Each other control plane node
sudo kubeadm upgrade node

# Each node (control plane and workers), one at a time
kubectl drain <node> --ignore-daemonsets --delete-emptydir-data
sudo apt-get install -y kubelet='1.36.x-*' kubectl='1.36.x-*'
sudo systemctl daemon-reload && sudo systemctl restart kubelet
kubectl uncordon <node>
```

On worker nodes run `sudo kubeadm upgrade node` after upgrading the kubeadm package and before restarting the kubelet. Replace `x` with the patch release you chose and pin it; use your distribution's equivalent of the `apt-get` lines.

After each minor: `kubectl get nodes`, `kubectl get pods -A | grep -vE 'Running|Completed'`, check that controllers, DNS and the CNI are healthy, run smoke tests, then upgrade add-ons and move the next minor. Do not run two minors on one day without soak time.

## 6. Rolling out workloads safely

- `kubectl rollout status deploy/<name> --timeout=5m`; set `progressDeadlineSeconds` so stuck rollouts fail.
- `kubectl rollout undo deploy/<name>` reverts to the previous ReplicaSet; with GitOps, revert the commit instead.
- Probes and `minReadySeconds` gate rollout speed; PDBs and `maxUnavailable` protect availability during drains.
- Risky changes: canary with Gateway API weights, Argo Rollouts or Flagger with metric analysis.

## 7. Debugging

```bash
kubectl get pods -A -o wide --field-selector=status.phase!=Running
kubectl describe pod <pod> -n <ns>                    # events, probe failures, scheduling reasons
kubectl events -n <ns> --for pod/<pod>
kubectl logs <pod> -n <ns> -c <container> --previous  # last crashed instance
kubectl debug -it pod/<pod> -n <ns> --image=busybox:1.37 --target=<container>
kubectl debug node/<node> -it --image=busybox:1.37    # host filesystem at /host
kubectl top pod -n <ns> --containers                  # needs metrics-server
kubectl auth can-i create deployments -n <ns> --as=system:serviceaccount:<ns>:<sa>
```

Common signals:

| Symptom | First checks |
|---|---|
| Pending | `describe` events: insufficient CPU/memory, taints, node affinity, topology spread, PVC unbound, quota |
| ImagePullBackOff | image name and tag or digest, pull Secret on the ServiceAccount, registry reachability from the node |
| CrashLoopBackOff | `logs --previous`, exit code, config and Secret keys, liveness probe too strict |
| OOMKilled | memory limit versus usage, JVM or runtime heap flags, memory leaks |
| Running but not Ready | readiness endpoint, Service selector and port names, NetworkPolicy, EndpointSlice contents |
| Node drain hangs | PDB with zero allowed disruptions, pods without a controller, finalizers |
| HTTPRoute not serving | route `Accepted` and `ResolvedRefs` conditions, ReferenceGrant, listener `allowedRoutes`, Gateway address |

## 8. Backup and restore

- **Cluster objects and volumes:** Velero (or the provider's backup service) with scheduled backups, volume snapshots through CSI, and a restore drill into a scratch cluster. Back up namespaces, CRDs and PVCs together. GitOps repos restore declarative state; Velero covers data and dynamically created objects.
- **etcd (self-managed):**

```bash
sudo ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /backup/etcd-$(date +%F).db
```

  Copy the snapshot off the node, encrypt it (it contains Secrets), and test restores with `etcdutl snapshot restore` in a lab. Managed control planes handle etcd for you.
- **Databases:** use the database's own backup mechanism (operator-managed backups, point-in-time recovery) in addition to volume snapshots.

## 9. Routine operations

- Monthly: apply patch releases (nodes and control plane), refresh node images, review expiring certificates (`kubeadm certs check-expiration` on kubeadm clusters).
- Quarterly: plan the next minor, review RBAC bindings, namespace quotas and unused resources, and test a restore.
- Alert on: Pending pods, CrashLoopBackOff and OOMKilled rates, PVC Pending, HPA at max replicas, API server error rates and latency, etcd leader changes and disk latency, certificate expiry, node NotReady, GitOps sync failures.
- Keep the number of cluster-wide custom controllers small and track their upgrade policy; an abandoned operator is a future outage.
