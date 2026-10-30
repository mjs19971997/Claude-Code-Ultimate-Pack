# Kubernetes Security Hardening

Reference for Pod Security Admission, securityContext, RBAC, admission policy, NetworkPolicy, workload identity, Secrets and image verification. Verified against Kubernetes 1.35 to 1.37 documentation, the Pod Security Standards and ValidatingAdmissionPolicy (`admissionregistration.k8s.io/v1`, GA) (2026-10).

## 1. Pod Security Standards and Admission

Three cumulative profiles: `privileged` (no restrictions), `baseline` (blocks known privilege escalations) and `restricted` (current hardening practice). The built-in Pod Security Admission (PSA) controller applies them per namespace through labels, in three modes:

| Mode | Effect |
|---|---|
| `enforce` | Pods that violate the level are rejected |
| `audit` | Violations are recorded as audit annotations, pods are allowed |
| `warn` | Users get a warning, pods are allowed |

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: shop
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: latest
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/audit: restricted
```

Notes:

- `warn` and `audit` also run on workload resources (Deployment, Job), so mistakes show up at `kubectl apply`. `enforce` only checks the resulting Pods.
- `*-version` labels pin a level to the rules of a minor release or `latest`. Pin only when you need to delay a tightening, and revisit at each upgrade.
- Roll out in order: label with `warn` and `audit` first, read the warnings (`kubectl label --dry-run=server --overwrite ns --all pod-security.kubernetes.io/enforce=restricted` shows what would break), fix, then enforce.
- Exemptions (usernames, RuntimeClasses, namespaces) are set in the API server's `AdmissionConfiguration` for `PodSecurity`. Keep the list short. Do not exempt controller ServiceAccounts such as the replicaset controller; that exempts every user who can create the workload.
- Keep system namespaces (`kube-system`, CNI, CSI, node agents) at `privileged` or `baseline` as their vendors require, and nothing else.

What `restricted` requires (in addition to `baseline`, which forbids host namespaces, privileged containers, hostPath, host ports, extra capabilities and unconfined seccomp or AppArmor):

- Volume types limited to configMap, csi, downwardAPI, emptyDir, ephemeral, persistentVolumeClaim, projected, secret.
- `allowPrivilegeEscalation: false`.
- `runAsNonRoot: true` (pod or container level) and no `runAsUser: 0`.
- `seccompProfile.type` of `RuntimeDefault` or `Localhost`.
- `capabilities.drop` includes `ALL`; only `NET_BIND_SERVICE` may be added.

`readOnlyRootFilesystem` is not part of `restricted`, but is a good additional control with `emptyDir` mounts for writable paths.

## 2. Pod and container securityContext

```yaml
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 10001
    runAsGroup: 10001
    fsGroup: 10001
    seccompProfile: { type: RuntimeDefault }
  containers:
    - name: app
      image: registry.example.com/shop/api@sha256:<digest>
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities: { drop: ["ALL"] }
      volumeMounts: [{ name: tmp, mountPath: /tmp }]
  volumes: [{ name: tmp, emptyDir: {} }]
```

- AppArmor is set with `securityContext.appArmorProfile` (`type: RuntimeDefault`); the annotation form is deprecated.
- `hostUsers: false` runs the pod in a user namespace where the node and runtime support it, which limits the impact of a container escape. Check the pod user-namespace documentation for your version and runtime.
- Never use `privileged: true`, `hostNetwork`, `hostPID`, `hostPath` or `docker.sock`-style mounts in application namespaces.

## 3. RBAC

- Prefer `Role` and `RoleBinding` per namespace. A `ClusterRole` bound with a `RoleBinding` grants its rules only inside that namespace and is a good way to reuse a role definition.
- No wildcards in `verbs`, `resources` or `apiGroups` for workloads. Review grants of `escalate`, `bind`, `impersonate`, `create` on `pods/exec`, `secrets` read access, and `create` on `pods` (which can mount any ServiceAccount in the namespace).
- One ServiceAccount per workload; no use of the `default` ServiceAccount.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata: { name: orders-worker, namespace: shop }
automountServiceAccountToken: false
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata: { name: orders-worker, namespace: shop }
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    resourceNames: ["orders-feature-flags"]
    verbs: ["get", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata: { name: orders-worker, namespace: shop }
subjects:
  - { kind: ServiceAccount, name: orders-worker, namespace: shop }
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: orders-worker
```

Audit with `kubectl auth can-i --list --as=system:serviceaccount:shop:orders-worker -n shop`, and periodically list bindings to `cluster-admin`. Human access goes through an identity provider (OIDC) and groups, not shared kubeconfigs or long-lived client certificates. Tokens for ServiceAccounts are short-lived and bound to the pod (projected volume or TokenRequest); do not create legacy Secret-based tokens.

## 4. Admission policy with CEL

ValidatingAdmissionPolicy runs CEL inside the API server, with no webhook to operate. A policy plus a binding; roll out with `Warn`/`Audit` before `Deny`:

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: require-image-digest
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: ["apps"]
        apiVersions: ["v1"]
        operations: ["CREATE", "UPDATE"]
        resources: ["deployments", "statefulsets", "daemonsets"]
  validations:
    - expression: >-
        object.spec.template.spec.containers.all(c, c.image.contains('@sha256:'))
      message: "container images must be referenced by digest (name@sha256:...)"
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: require-image-digest-production
spec:
  policyName: require-image-digest
  validationActions: ["Warn", "Audit"]      # switch to ["Deny"] after fixing violations
  matchResources:
    namespaceSelector:
      matchLabels:
        environment: production
```

Use Kyverno, OPA Gatekeeper or Kubewarden when you need mutation, resource generation, external data or signature verification. Kyverno 1.17 moved to CEL-based policy types under `policies.kyverno.io/v1` (ValidatingPolicy, MutatingPolicy, GeneratingPolicy, ImageValidatingPolicy) and deprecated `ClusterPolicy`, with removal planned for 1.20; write new Kyverno policies with the new types and read its migration guide for existing ones. MutatingAdmissionPolicy is the in-tree counterpart for mutation; check its feature state for your version.

## 5. NetworkPolicy recipes

NetworkPolicy is enforced only by CNIs that support it (Cilium, Calico, cloud CNIs with policy enabled). Policies are additive allow rules on top of a default deny.

Default deny for a namespace:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: default-deny-all, namespace: shop }
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
```

Allow DNS and one dependency, select namespaces with the automatic `kubernetes.io/metadata.name` label:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: orders-egress, namespace: shop }
spec:
  podSelector: { matchLabels: { app.kubernetes.io/name: orders } }
  policyTypes: [Egress]
  egress:
    - to:
        - namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: kube-system } }
          podSelector: { matchLabels: { k8s-app: kube-dns } }
      ports: [{ protocol: UDP, port: 53 }, { protocol: TCP, port: 53 }]
    - to:
        - podSelector: { matchLabels: { app.kubernetes.io/name: postgres } }
      ports: [{ protocol: TCP, port: 5432 }]
```

Notes: allow traffic from the gateway or ingress namespace and from the monitoring namespace explicitly; egress to cloud metadata endpoints (169.254.169.254) should stay blocked for pods that do not need it; standard NetworkPolicy has no FQDN rules, so use the CNI's extension for egress by DNS name.

## 6. Workload identity and Secrets

- Cloud access: use workload identity, not static keys. On EKS, EKS Pod Identity (an association between a ServiceAccount and an IAM role created through the EKS API) or IRSA (annotation `eks.amazonaws.com/role-arn` on the ServiceAccount); GKE Workload Identity Federation; Azure Workload Identity. Scope each role to one workload.
- Secrets: enable encryption at rest with a KMS provider (KMS v2) on self-managed control planes (managed services expose a setting). RBAC `get`/`list` on Secrets is equivalent to reading them; restrict it.
- Prefer mounting Secrets as files over environment variables (env values appear in `kubectl describe`, crash dumps and child processes).
- Keep secret material out of Git: External Secrets Operator or the Secrets Store CSI driver sync from a secret manager; Sealed Secrets or SOPS encrypt in Git. Base64 is encoding only.
- Rotate on a schedule and on staff changes; use short-lived credentials where the provider supports them.

## 7. Supply chain and runtime

- Deploy images by digest, set by CI after build, scan and signing.
- Sign with Sigstore cosign (keyless through the CI provider's OIDC identity or a managed key) and verify at admission: Kyverno ImageValidatingPolicy or the Sigstore policy-controller. Pin the expected issuer and subject (the exact workflow identity), not a wildcard for the whole organization.
- Pull from a private registry through an image pull Secret on the ServiceAccount, or node-level credential providers.
- Run only images that come from approved registries: enforce with an admission policy on `image` prefixes.
- Use a runtime detection tool (Falco, Tetragon) for exec-in-container, unexpected network egress and file writes in read-only paths.
- Audit logging on the API server, shipped off-cluster, with a policy that records Secrets and RBAC changes at `Metadata` level or higher.

## 8. Cluster benchmarks

Run kube-bench (CIS Kubernetes Benchmark) on self-managed control planes and nodes, and the provider's equivalent on managed clusters. Keep the control plane and nodes on a supported minor (see upgrades-and-operations.md), restrict the API server endpoint, protect kubelet and etcd ports, and disable anonymous authentication.
