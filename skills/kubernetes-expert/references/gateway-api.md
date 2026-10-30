# Gateway API and Ingress Migration

Reference for exposing HTTP, gRPC and TLS services with Gateway API and for migrating off Ingress and the retired ingress-nginx controller. Verified against Gateway API v1.6 (latest patch v1.6.3), ingress2gateway 1.0 and Kubernetes 1.35 to 1.37 (2026-10).

## 1. Resource model

| Resource | Owner | Purpose |
|---|---|---|
| GatewayClass | Platform / controller vendor | Names an implementation (controller) |
| Gateway | Cluster operators | Listeners (port, protocol, hostname, TLS) and which namespaces may attach routes |
| HTTPRoute, GRPCRoute, TLSRoute, TCPRoute, UDPRoute | App teams | Match rules and backends, attached to a Gateway through `parentRefs` |
| ReferenceGrant | Owner of the target namespace | Permits a cross-namespace reference (route to Service, Gateway to Secret) |
| BackendTLSPolicy | App teams | TLS from the gateway to the backend, with CA validation |
| ListenerSet | App teams | Lets a namespace add listeners to a shared Gateway, if the Gateway's `allowedListeners` permits it |

Status at v1.6 (project README and changelogs): GatewayClass, Gateway, HTTPRoute, GRPCRoute, ReferenceGrant, TLSRoute (v1 since 1.5), ListenerSet (Standard since 1.5), TCPRoute and UDPRoute (GA in 1.6, use `v1`; `v1alpha2` is deprecated), BackendTLSPolicy are served as `gateway.networking.k8s.io/v1`. The HTTPRoute CORS filter is in the Standard channel. Gateway API is installed as CRDs, not part of Kubernetes itself; the controller you pick decides which features and channels it supports.

## 2. Install the CRDs

Use the Standard channel unless you need an Experimental feature. Installing Experimental CRDs on top of Standard CRDs, and downgrading below 1.5 after installing 1.5 or later, is blocked by the `safe-upgrades.gateway.networking.k8s.io` ValidatingAdmissionPolicy that ships with the CRDs.

```bash
# Replace the tag with the current release from the project's releases page
kubectl apply --server-side -f \
  https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.6.3/standard-install.yaml
kubectl get crd | grep gateway.networking.k8s.io
```

Many implementations install or manage the CRDs themselves; do not apply two different versions from two tools. Pin the version in GitOps and review the release notes before bumping. TLSRoute validation uses CEL and needs Kubernetes 1.31 or newer.

## 3. Shared Gateway with per-team routes

The platform team owns the Gateway and the certificate. `allowedRoutes` limits which namespaces can attach.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: public
  namespace: gateway-system
spec:
  gatewayClassName: example-gateway-class   # from your implementation
  listeners:
    - name: https
      protocol: HTTPS
      port: 443
      hostname: "*.example.com"
      tls:
        mode: Terminate
        certificateRefs:
          - kind: Secret
            name: wildcard-example-com-tls
      allowedRoutes:
        namespaces:
          from: Selector
          selector:
            matchLabels:
              gateway-access: public
```

An app namespace opts in with the label `gateway-access: public`; reviewers should control who can label namespaces. Attach a route:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: shop
  namespace: shop
spec:
  parentRefs:
    - name: public
      namespace: gateway-system
      sectionName: https
  hostnames: ["shop.example.com"]
  rules:
    - matches:
        - path: { type: PathPrefix, value: /api }
      backendRefs:
        - name: shop-api
          port: 8080
    - backendRefs:
        - name: shop-web
          port: 8080
```

Check the result in status: `kubectl describe httproute -n shop shop` and look for `Accepted=True` and `ResolvedRefs=True` per parent.

## 4. TLS patterns

- **Terminate at the Gateway:** `tls.mode: Terminate` with `certificateRefs` to a `kubernetes.io/tls` Secret, usually issued by cert-manager.
- **Certificate in another namespace:** the Secret's namespace needs a ReferenceGrant:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: ReferenceGrant
metadata:
  name: allow-gateway-to-read-certs
  namespace: certs                  # namespace of the Secret
spec:
  from:
    - group: gateway.networking.k8s.io
      kind: Gateway
      namespace: gateway-system
  to:
    - group: ""
      kind: Secret
      name: wildcard-example-com-tls
```

- **Passthrough:** a listener with `protocol: TLS` and `tls.mode: Passthrough`, routed by SNI with a `TLSRoute` (`v1`). The gateway never sees plaintext, so no HTTP matching.
- **HTTP to HTTPS redirect:** an HTTPRoute on the port-80 listener with a `RequestRedirect` filter (`scheme: https`, `statusCode: 301`).
- **Gateway to backend TLS:** `BackendTLSPolicy` with `targetRefs` to the Service, `validation.hostname` and CA certificate references. Confirm your implementation supports it before relying on it.

## 5. Traffic splitting, headers and gRPC

Weighted canary (weights are relative):

```yaml
rules:
  - backendRefs:
      - { name: shop-web-stable, port: 8080, weight: 90 }
      - { name: shop-web-canary, port: 8080, weight: 10 }
```

Route a header to a canary and add a response header:

```yaml
rules:
  - matches:
      - headers:
          - { name: x-canary, value: "true" }
    filters:
      - type: ResponseHeaderModifier
        responseHeaderModifier:
          add:
            - { name: x-served-by, value: canary }
    backendRefs:
      - { name: shop-web-canary, port: 8080 }
```

gRPC uses `GRPCRoute` with method matching; Gateway API recommends it over HTTPRoute for gRPC traffic:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GRPCRoute
metadata: { name: orders, namespace: shop }
spec:
  parentRefs: [{ name: public, namespace: gateway-system, sectionName: https }]
  hostnames: ["grpc.example.com"]
  rules:
    - matches:
        - method: { service: shop.v1.OrderService }
      backendRefs: [{ name: orders, port: 9090 }]
```

Request mirroring, retries, timeouts and CORS are available as route fields or filters; the supported subset depends on the implementation's conformance report.

## 6. Migrating from Ingress and ingress-nginx

The Kubernetes project retired the ingress-nginx controller on 2026-03-24: no further releases, bug fixes or security fixes. Existing installs keep running, which is the risk. The Kubernetes Steering and Security Response Committees note that no alternative is a drop-in replacement, so plan and test the migration.

1. **Inventory:** `kubectl get ingress -A -o yaml`, plus the annotations in use (rewrite, auth, rate limit, snippets, canary, proxy buffers). Annotations with no Gateway API equivalent need an implementation-specific policy or a different design.
2. **Choose an implementation** with a Gateway API conformance report covering the features you need (check the project's conformance reports), and install it with its documentation.
3. **Convert** with ingress2gateway (1.0, a SIG Network project) and review the output; it warns about untranslated fields and does not copy annotations:

```bash
go install github.com/kubernetes-sigs/ingress2gateway@v1.0.0   # or: brew install ingress2gateway
ingress2gateway print --providers=ingress-nginx -n shop > gateway-shop.yaml
```

   Use `--input-file` to convert manifests from Git instead of a live cluster.
4. **Run both side by side:** the new Gateway gets its own load balancer address. Test with `curl --resolve host:443:<new-ip>` before touching DNS.
5. **Shift traffic** by lowering DNS TTL, using weighted DNS records if available, and moving a small share first. Keep the old controller until error rates and latency match.
6. **Verify behavior differences** (path matching type, trailing slashes, body size limits, timeouts, header handling, redirect codes). Encode them in route fields or implementation policies and add them to smoke tests.
7. **Remove** the old Ingress objects and controller after a full traffic cycle.

Other Ingress controllers that are still maintained keep working with `networking.k8s.io/v1` Ingress, but new HTTP exposure should use Gateway API.

## 7. Operating notes

- One Gateway per trust boundary (public, internal), not per app. Listener hostnames prevent routes from hijacking each other's hosts.
- Give app teams RBAC on HTTPRoute, GRPCRoute and Service in their namespace only; Gateways, GatewayClasses, ReferenceGrants and BackendTLSPolicy belong to the platform team.
- Review every ReferenceGrant like a firewall rule: grant to a named object where possible.
- Alert on routes where `Accepted` or `ResolvedRefs` is false and on certificate expiry.
- Read the implementation's release notes on each Gateway API CRD bump; implementations lag the spec.
