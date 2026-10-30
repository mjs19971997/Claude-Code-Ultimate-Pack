---
name: kubernetes-expert
description: >-
  Designs, writes and reviews Kubernetes manifests and cluster operations on supported releases: Deployments, StatefulSets, Jobs, native sidecars, Services, Gateway API routing, NetworkPolicy, RBAC, Pod Security Admission, autoscaling (HPA, VPA, in-place resize, Karpenter), Helm, Kustomize, GitOps and version upgrades. Use when editing Kubernetes YAML, Helm charts or Kustomize overlays, debugging Pending/CrashLoopBackOff pods, migrating from Ingress or ingress-nginx to Gateway API, hardening namespaces, or planning a cluster upgrade. Not for writing Dockerfiles or Compose files (use docker-expert), CI pipeline definitions (use cicd-expert), or provisioning EKS and cloud resources with IaC (use terraform-expert or aws-expert).
license: MIT
metadata:
  version: "3.0.0"
---

# Kubernetes Expert

This skill covers running workloads on Kubernetes: the core API objects, networking with Services and Gateway API, storage, security (RBAC, Pod Security Admission, NetworkPolicy), autoscaling, packaging with Helm and Kustomize, GitOps delivery, and the upgrade path between minor versions. It does not cover building container images (docker-expert), the CI system that publishes them (cicd-expert), or creating the cluster's cloud infrastructure (terraform-expert, aws-expert).

> Verified against Kubernetes 1.37, 1.36 and 1.35 (1.34 reached end of life on 2026-10-27, 1.30 long before) and Gateway API v1.6 (2026-10).

## Contents
1. [Scope](#1-scope)
2. [Core Expertise](#2-core-expertise)
3. [Workflow](#3-workflow)
4. [Decision Rules](#4-decision-rules)
5. [Coding Standards](#5-coding-standards)
6. [Project Structure](#6-project-structure)
7. [Design Patterns](#7-design-patterns)
8. [Best Practices](#8-best-practices)
9. [Performance](#9-performance)
10. [Security](#10-security)
11. [Testing](#11-testing)
12. [Review Checklist](#12-review-checklist)
13. [Production Notes](#13-production-notes)
14. [Examples](#14-examples)
15. [Common Mistakes](#15-common-mistakes)
16. [References](#16-references)

## 1. Scope

- Workload objects: Pod, Deployment, StatefulSet, DaemonSet, Job, CronJob; probes, lifecycle hooks, native sidecars, init containers.
- Networking: Service types, EndpointSlice, DNS, Gateway API (Gateway, HTTPRoute, GRPCRoute, TLS/TCP routes), legacy Ingress, NetworkPolicy.
- Storage: PersistentVolumeClaim, StorageClass, CSI, volume snapshots, StatefulSet volume templates.
- Security: RBAC, ServiceAccounts and bound tokens, Pod Security Admission, securityContext, seccomp and AppArmor, admission policies, Secrets and encryption at rest.
- Scheduling and scaling: requests and limits, QoS, affinity, topology spread, taints, priority, HPA, VPA, in-place resize, Cluster Autoscaler, Karpenter.
- Delivery: Helm, Kustomize, Argo CD, Flux, progressive delivery.
- Operations: upgrades, deprecated API removal, debugging, backups (Velero), etcd for self-managed control planes.

## 2. Core Expertise

- **Release cadence.** About three minor releases per year; the project supports the three most recent minors with roughly 14 months of patches each. Managed services (EKS, GKE, AKS) publish their own support calendars and extended-support pricing; check them.
- **Version skew.** kubelet may be up to three minors older than the API server and never newer; upgrade the control plane one minor at a time, then nodes.
- **Native sidecars** (stable since 1.33): an `initContainers` entry with `restartPolicy: Always` starts before the app containers, keeps running, and is stopped after them. Use for proxies, log shippers and credential refreshers.
- **In-place Pod resize** (stable since 1.35): CPU and memory requests and limits are mutable through the `resize` subresource, often without a restart; `resizePolicy` per resource controls restarts. VPA can use it through its in-place update mode (check your VPA version).
- **Gateway API** is the successor to Ingress: role-oriented (GatewayClass for the platform, Gateway for cluster operators, Routes for app teams), portable matching, header and weight-based routing, cross-namespace references controlled by `ReferenceGrant` and `allowedRoutes`.
- **ingress-nginx retirement.** The Kubernetes ingress-nginx project was retired on 2026-03-24: no further releases or security fixes. Migrate to a Gateway API implementation (`ingress2gateway` 1.0 converts manifests) or to a maintained ingress controller.
- **EndpointSlice** replaces the deprecated v1 Endpoints API for consumers that watch endpoints.
- **Pod Security Admission** with namespace labels `pod-security.kubernetes.io/enforce|audit|warn` at `privileged`, `baseline` or `restricted`.
- **Admission policy in CEL:** ValidatingAdmissionPolicy (GA) for in-tree validation without webhooks; Kyverno or OPA Gatekeeper for mutation, generation and image verification.
- **AppArmor** through `securityContext.appArmorProfile` (the old annotations are deprecated).
- **Bound ServiceAccount tokens** via projected volumes or the TokenRequest API; legacy Secret-based tokens are not auto-created.
- **Dynamic Resource Allocation** (core APIs GA in 1.34) for GPUs and other devices through ResourceClaims.
- **Topology-aware routing:** Service `trafficDistribution` (newer values `PreferSameZone` and `PreferSameNode`; check the docs for your version).
- **Tooling:** kubectl (`debug`, `diff`, `events`, `auth can-i`), Helm 3 with OCI registries, Kustomize, kubeconform, Argo CD / Flux.

## 3. Workflow

1. **Classify the workload:** stateless (Deployment), stateful with identity (StatefulSet or an operator), per-node agent (DaemonSet), batch (Job/CronJob).
2. **Define the contract:** ports, health endpoints (startup, readiness, liveness), shutdown behaviour (SIGTERM handling, drain time), config and secrets, persistent data.
3. **Size it:** measure, then set requests; set memory limits; decide on CPU limits per policy (many teams omit them to avoid throttling).
4. **Expose it:** ClusterIP Service; HTTP from outside through an HTTPRoute on a shared Gateway; NetworkPolicy for who may call it.
5. **Secure it:** namespace PSA `restricted`, dedicated ServiceAccount with only the RBAC it needs, `automountServiceAccountToken: false` unless it calls the API.
6. **Make it resilient:** at least two replicas, PodDisruptionBudget, topology spread across zones, HPA where load varies.
7. **Package it:** Helm chart or Kustomize base plus overlays; render and validate (`helm template | kubeconform`) in CI.
8. **Deliver it:** GitOps (Argo CD or Flux) from a Git repo; progressive rollout for risky changes.
9. **Observe it:** metrics, logs, events; alert on restarts, pending pods and SLO burn.
10. **Upgrade it:** before each cluster minor upgrade, scan for removed APIs and test on a staging cluster.

## 4. Decision Rules

- **Gateway API for new HTTP exposure.** Keep existing Ingress only where the controller is maintained; plan ingress-nginx migrations now.
- **StatefulSet or operator for databases.** Prefer a mature operator (it handles failover, backups and upgrades) or a managed database outside the cluster over a hand-written StatefulSet.
- **HPA on the signal that tracks load.** CPU works for CPU-bound services; queue depth or request rate needs a metrics adapter (Prometheus Adapter) or KEDA. Do not run HPA and VPA on the same resource metric for the same workload.
- **Karpenter vs Cluster Autoscaler:** Karpenter for fast, flexible node provisioning and consolidation where supported (AWS, Azure); Cluster Autoscaler where node groups are the provider's model.
- **Helm vs Kustomize:** Helm to distribute a configurable package; Kustomize to patch a known base per environment. Rendering a Helm chart and patching the output with Kustomize is fine; templating inside Kustomize is not.
- **Cluster per environment** for production isolation; namespaces with quotas and NetworkPolicy for teams inside an environment.
- **Built-in first for policy:** PSA plus ValidatingAdmissionPolicy cover most guardrails; add Kyverno/Gatekeeper when you need mutation, generation or signature verification.
- **Secrets:** sync from an external store (External Secrets Operator, Secrets Store CSI driver) or encrypt in Git (Sealed Secrets, SOPS); enable encryption at rest with a KMS provider.
- **Images by digest** in production manifests, set by CI; tags only as human-readable aliases.

## 5. Coding Standards

- YAML, one object per document, `---` separated; `apiVersion` set to the stable version (`apps/v1`, `autoscaling/v2`, `policy/v1`, `gateway.networking.k8s.io/v1`).
- Recommended labels: `app.kubernetes.io/name`, `instance`, `version`, `component`, `part-of`, `managed-by`. Selectors use only stable labels (`name`, `instance`), never `version`.
- Always set `metadata.namespace` in manifests that are not rendered by a tool that sets it.
- Names are DNS-1123 (`payment-service`); ServiceAccounts one per workload, named after it.
- Containers: `resources.requests` for CPU and memory, `resources.limits.memory`; `securityContext` complete for PSA `restricted`; probes on real endpoints.
- Deployments: `revisionHistoryLimit`, explicit `strategy`, `progressDeadlineSeconds`; `minReadySeconds` when readiness flaps.
- Reference config and secrets by name (`envFrom`, `valueFrom`, volumes); no inline secret values.
- Select namespaces in NetworkPolicy with the automatic `kubernetes.io/metadata.name` label.
- Helm: `helm lint`, values documented, `values.schema.json` for validation, no logic that hides required fields.

## 6. Project Structure

```
platform-gitops/
├── clusters/
│   ├── production-us-east-1/
│   │   ├── infrastructure.yaml      # Argo CD Applications / Flux Kustomizations
│   │   └── apps.yaml
│   └── staging-us-east-1/
├── infrastructure/
│   ├── gateway/                     # GatewayClass, shared Gateways, certificates
│   ├── cert-manager/
│   ├── external-secrets/
│   └── policies/                    # PSA labels, ValidatingAdmissionPolicies, Kyverno
└── apps/
    └── payment-service/
        ├── base/                    # Deployment, Service, HPA, PDB, NetworkPolicy, HTTPRoute
        │   └── kustomization.yaml
        └── overlays/
            ├── staging/
            └── production/
```

## 7. Design Patterns

- **Native sidecar:** proxy or log shipper as `initContainers` with `restartPolicy: Always`; it is ready before the app and outlives it during shutdown.
- **Init container:** one-shot setup (schema check, file rendering). Run migrations as a separate Job or a GitOps sync hook, not in every pod start.
- **Shared Gateway, per-team Routes:** the platform team owns Gateways and TLS; app namespaces attach HTTPRoutes allowed by `allowedRoutes`.
- **Canary or blue-green:** HTTPRoute `backendRefs` weights, Argo Rollouts or Flagger driven by metrics.
- **Operator:** a CRD plus controller for stateful software (databases, Kafka, certificates); prefer maintained community operators.
- **GitOps:** Git is the desired state; the controller reconciles and reports drift; humans change Git, not the cluster.
- **Default-deny network:** namespace-wide deny, then explicit allows per workload, including DNS egress.

## 8. Best Practices

- Readiness gates traffic, liveness restarts, startup protects slow boots; never point liveness at a dependency check.
- Handle SIGTERM: stop accepting, finish in-flight work within `terminationGracePeriodSeconds`; a short `preStop` sleep covers endpoint propagation delay.
- PDB on every multi-replica workload; make sure it still allows at least one eviction, or node drains hang.
- Topology spread across zones (`whenUnsatisfiable: ScheduleAnyway` unless strict spread matters more than scheduling).
- Quotas and LimitRanges per namespace so one team cannot starve others.
- Pin chart and add-on versions; upgrade add-ons deliberately with release notes.
- Keep `kubectl apply` out of production; use `kubectl diff` and GitOps.

## 9. Performance

- Requests drive scheduling and HPA utilization; set them from observed usage (VPA in recommendation mode, or metrics).
- CPU limits cause CFS throttling at low average utilization; omit them or set them generously for latency-sensitive services, keep memory limits.
- Use in-place resize to adjust a running pod's resources without rescheduling where the workload tolerates it.
- `trafficDistribution` and topology-aware routing cut cross-zone latency and cost.
- Karpenter consolidation or Cluster Autoscaler scale-down reduce idle nodes; protect critical pods with PDBs and `karpenter.sh/do-not-disrupt` where needed.
- Ephemeral-storage requests and limits prevent disk-pressure evictions.

## 10. Security

- Namespaces labelled `pod-security.kubernetes.io/enforce: restricted` (plus `warn` and `audit`), with documented exceptions for system add-ons.
- securityContext: `runAsNonRoot: true`, `allowPrivilegeEscalation: false`, `capabilities.drop: ["ALL"]`, `seccompProfile.type: RuntimeDefault`, `readOnlyRootFilesystem: true` with `emptyDir` for writable paths.
- RBAC: Roles per namespace, no wildcards, no `cluster-admin` for workloads, review `escalate`, `bind`, `impersonate` and `pods/exec` grants. Check with `kubectl auth can-i --list --as=system:serviceaccount:ns:sa`.
- `automountServiceAccountToken: false` for pods that do not call the API; cloud access through workload identity (EKS Pod Identity or IRSA, GKE Workload Identity, Azure Workload Identity), not static keys in Secrets.
- NetworkPolicy default deny for ingress and egress; requires a CNI that enforces it (Cilium, Calico, cloud CNIs with policy enabled).
- Image provenance: signed images verified at admission (Kyverno, Sigstore policy-controller); scan in CI and continuously.
- Encryption at rest for Secrets with a KMS v2 provider; audit logging enabled on the API server.
- Benchmark with kube-bench (CIS) and keep the control plane on a supported version.

## 11. Testing

- Schema: `kubeconform -strict` against the target cluster version, including CRD schemas.
- Charts: `helm lint`, `helm template` in CI, `helm-unittest` for template logic, chart-testing (`ct lint`, `ct install` on kind).
- Policies: Kyverno CLI or `kubectl apply --dry-run=server` against a cluster with the policies installed.
- Ephemeral clusters (kind, k3d) for integration tests of manifests and operators.
- Behaviour drills in staging: node drain respects PDBs, HPA scales under load, NetworkPolicy blocks unexpected traffic, rollback to the previous digest works.
- Upgrade rehearsal: restore or clone staging, upgrade one minor, run smoke tests.

## 12. Review Checklist

- [ ] Stable `apiVersion`s; nothing removed in the target cluster version (checked with pluto or the deprecation guide).
- [ ] Image by digest (or immutable tag set by CI); no `latest`.
- [ ] Requests for CPU and memory, memory limit, probes, graceful shutdown.
- [ ] securityContext meets PSA `restricted`; namespace labels present.
- [ ] Dedicated ServiceAccount, least-privilege RBAC, token automount off unless needed.
- [ ] Replicas >= 2, PDB, topology spread, HPA bounds sensible.
- [ ] NetworkPolicy default deny plus explicit allows, DNS egress included.
- [ ] HTTP exposure through Gateway API (or a maintained Ingress controller) with TLS.
- [ ] Secrets come from a secret manager or encrypted source, not plain YAML in Git.
- [ ] Labels follow `app.kubernetes.io/*`; selectors immutable and minimal.
- [ ] Refactoring: raw manifests moved to a chart or Kustomize base; Ingress migrated to HTTPRoute; sidecars converted to native sidecars; migrations moved out of pod startup.

## 13. Production Notes

- Upgrade cadence: stay within the supported window; on managed services, track extended-support dates to avoid surprise charges or forced upgrades.
- Before each upgrade: check `apiserver_requested_deprecated_apis` metrics and audit logs for clients still calling deprecated APIs; upgrade add-ons (CNI, CSI, ingress or gateway controller) to versions that support the target.
- Logs to stdout/stderr, collected by a node agent (Grafana Alloy, Fluent Bit, OpenTelemetry Collector). Promtail reached end of life in March 2026.
- Alert on: pods Pending > N minutes, CrashLoopBackOff, OOMKilled, PVC Pending, HPA at max, certificate expiry, GitOps sync failures.
- Back up cluster objects and volumes (Velero or the provider's tool); on self-managed clusters snapshot etcd and rehearse restores.
- Debug with `kubectl describe`, `kubectl events --for pod/x`, `kubectl logs --previous`, `kubectl debug -it pod/x --image=busybox --target=app`.

## 14. Examples

### Example 1: Hardened namespace and Deployment with PDB, HPA and NetworkPolicy

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: payments
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/audit: restricted
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service
  namespace: payments
  labels: { app.kubernetes.io/name: payment-service, app.kubernetes.io/part-of: payments }
spec:
  replicas: 3
  revisionHistoryLimit: 5
  strategy: { type: RollingUpdate, rollingUpdate: { maxSurge: 1, maxUnavailable: 0 } }
  selector:
    matchLabels: { app.kubernetes.io/name: payment-service }
  template:
    metadata:
      labels: { app.kubernetes.io/name: payment-service, app.kubernetes.io/part-of: payments }
    spec:
      serviceAccountName: payment-service
      automountServiceAccountToken: false
      terminationGracePeriodSeconds: 30
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        seccompProfile: { type: RuntimeDefault }
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector: { matchLabels: { app.kubernetes.io/name: payment-service } }
      containers:
        - name: app
          image: ghcr.io/acme/payment-service:1.4.2   # CI rewrites this to name@sha256:digest
          ports: [{ name: http, containerPort: 8080 }]
          envFrom: [{ configMapRef: { name: payment-service-config } }]
          env:
            - name: DB_PASSWORD
              valueFrom: { secretKeyRef: { name: payment-service-db, key: password } }
          resources:
            requests: { cpu: 250m, memory: 256Mi }
            limits: { memory: 512Mi }
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities: { drop: ["ALL"] }
          startupProbe: { httpGet: { path: /healthz, port: http }, periodSeconds: 5, failureThreshold: 30 }
          readinessProbe: { httpGet: { path: /readyz, port: http }, periodSeconds: 5 }
          livenessProbe: { httpGet: { path: /healthz, port: http }, periodSeconds: 10 }
          lifecycle:
            preStop: { sleep: { seconds: 5 } }   # no shell needed in the image
          volumeMounts: [{ name: tmp, mountPath: /tmp }]
      volumes: [{ name: tmp, emptyDir: {} }]
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata: { name: payment-service, namespace: payments }
spec:
  maxUnavailable: 1
  selector: { matchLabels: { app.kubernetes.io/name: payment-service } }
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: { name: payment-service, namespace: payments }
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: payment-service }
  minReplicas: 3
  maxReplicas: 30
  metrics:
    - type: Resource
      resource: { name: cpu, target: { type: Utilization, averageUtilization: 70 } }
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: default-deny, namespace: payments }
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: payment-service, namespace: payments }
spec:
  podSelector: { matchLabels: { app.kubernetes.io/name: payment-service } }
  policyTypes: [Ingress, Egress]
  ingress:
    - from:
        - namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: gateway-system } }
      ports: [{ protocol: TCP, port: 8080 }]
  egress:
    - to:
        - namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: kube-system } }
          podSelector: { matchLabels: { k8s-app: kube-dns } }
      ports: [{ protocol: UDP, port: 53 }, { protocol: TCP, port: 53 }]
    - to:
        - namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: databases } }
      ports: [{ protocol: TCP, port: 5432 }]
```

### Example 2: Gateway API instead of Ingress

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata: { name: public, namespace: gateway-system }
spec:
  gatewayClassName: example-gateway-class    # provided by your Gateway API implementation
  listeners:
    - name: http
      protocol: HTTP
      port: 80
      allowedRoutes: { namespaces: { from: Same } }
    - name: https
      protocol: HTTPS
      port: 443
      hostname: api.example.com
      tls:
        mode: Terminate
        certificateRefs: [{ kind: Secret, name: api-example-com-tls }]
      allowedRoutes:
        namespaces:
          from: Selector
          selector: { matchLabels: { kubernetes.io/metadata.name: payments } }
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata: { name: redirect-to-https, namespace: gateway-system }
spec:
  parentRefs: [{ name: public, sectionName: http }]
  rules:
    - filters:
        - type: RequestRedirect
          requestRedirect: { scheme: https, statusCode: 301 }
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata: { name: payment-service, namespace: payments }
spec:
  parentRefs: [{ name: public, namespace: gateway-system, sectionName: https }]
  hostnames: ["api.example.com"]
  rules:
    - matches: [{ path: { type: PathPrefix, value: /payments } }]
      backendRefs: [{ name: payment-service, port: 80 }]
```

### Example 3: Native sidecar and in-place resize

```yaml
apiVersion: v1
kind: Pod
metadata: { name: worker, namespace: payments }
spec:
  securityContext: { runAsNonRoot: true, runAsUser: 10001, seccompProfile: { type: RuntimeDefault } }
  initContainers:
    - name: log-shipper
      image: fluent/fluent-bit:4.0        # pin the version you run
      restartPolicy: Always               # makes it a native sidecar
      resources: { requests: { cpu: 50m, memory: 64Mi }, limits: { memory: 128Mi } }
      securityContext: { allowPrivilegeEscalation: false, capabilities: { drop: ["ALL"] } }
  containers:
    - name: app
      image: ghcr.io/acme/worker:2.1.0
      resizePolicy:
        - { resourceName: cpu, restartPolicy: NotRequired }
        - { resourceName: memory, restartPolicy: RestartContainer }
      resources: { requests: { cpu: 500m, memory: 512Mi }, limits: { memory: 1Gi } }
      securityContext: { allowPrivilegeEscalation: false, capabilities: { drop: ["ALL"] } }
```

```bash
# Raise CPU on the running pod without recreating it (Kubernetes 1.35+ stable)
kubectl -n payments patch pod worker --subresource resize --type merge \
  -p '{"spec":{"containers":[{"name":"app","resources":{"requests":{"cpu":"1"}}}]}}'
kubectl -n payments get pod worker -o jsonpath='{.status.containerStatuses[0].resources}'
```

## 15. Common Mistakes

- **Running an end-of-life minor.** No security patches; upgrades become multi-hop. Track the release calendar and the managed provider's dates.
- **Staying on ingress-nginx.** It no longer receives security fixes; migrate to Gateway API or a maintained controller.
- **Sidecars as regular containers.** They start in random order and keep Jobs from completing; use native sidecars.
- **No requests, or limits equal to tiny guesses.** Pods land on full nodes or get OOMKilled and throttled; measure and size.
- **Liveness probe on dependencies.** A database blip restarts every pod; liveness checks only the process itself.
- **`latest` or mutable tags.** Nodes run different code and rollbacks are ambiguous; deploy digests.
- **Privileged or root pods in app namespaces.** PSA `restricted` and a complete securityContext prevent it.
- **NetworkPolicy without DNS egress,** or selecting namespaces by labels nobody sets; use `kubernetes.io/metadata.name`.
- **PDB that allows zero disruptions** (`minAvailable` equal to replicas): node drains and upgrades stall.
- **Manual `kubectl apply` or `edit` in production:** drift from Git and no audit trail; change Git and let GitOps sync.
- **Ignoring API removals** until the upgrade fails; scan manifests, charts and live clients before each minor upgrade.
- **Secrets committed as base64 YAML:** base64 is encoding, not encryption.

## 16. References

- [references/gateway-api.md](references/gateway-api.md): Ingress and ingress-nginx migration, Gateway API resources, TLS, canary weights, cross-namespace rules.
- [references/security-hardening.md](references/security-hardening.md): PSA, RBAC patterns, ValidatingAdmissionPolicy, NetworkPolicy recipes, workload identity, image verification.
- [references/upgrades-and-operations.md](references/upgrades-and-operations.md): release support, version skew, deprecated API scanning, upgrade runbook, debugging and backups.
- Official docs: https://kubernetes.io/docs/ , https://kubernetes.io/releases/ , https://gateway-api.sigs.k8s.io/ , https://kubernetes.io/docs/concepts/security/pod-security-standards/ , https://github.com/kubernetes-sigs/ingress2gateway
