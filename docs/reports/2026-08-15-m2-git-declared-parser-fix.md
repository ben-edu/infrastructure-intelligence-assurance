# Git Declared Parser and Source-Scope Correction — 2026-08-15

## Status

Accepted and live-validated on `mgmt-automation`.

## Trigger

Live Git authentication succeeded against `ben-edu/api-cluster-infra`, but the first declared-state sync exposed two implementation defects before PR acceptance.

## Observed evidence

Without a kubeconfig, the original parser produced zero normalized records and multiple `DECLARED_MANIFEST_PARSE_FAILED` errors.

As a diagnostic only, running the same source sync with the existing read-only Kubernetes kubeconfig produced 16 normalized records at revision:

```text
5767e0a4c583d0a0e8c87b2e24c42eaeb822a3b4
```

That run also produced three `DUPLICATE_DECLARED_IDENTITY` errors for FastAPI resources in the default namespace.

## Interpretation

The parser was incorrectly coupled to Kubernetes client discovery/configuration.

The source mapping was also too broad: recursively scanning raw Kustomize base, overlays, and patches treated intermediate source files as independent declarations.

## Correction

- use `kubectl patch --local` for direct supported manifest parsing;
- explicitly remove `KUBECONFIG` and `KUBERNETES_MASTER` from the local parser/render environment;
- replace recursive `kubernetes/` scanning with explicit direct-manifest paths;
- render only the FastAPI dev/prod Kustomize targets at the exact fetched revision;
- materialize Kustomize input in a transient detached Git worktree and remove it after rendering;
- keep Secret, ConfigMap, Helm values, example credentials, and unsupported kinds outside normalized declared evidence;
- add regression tests for local parsing, Kustomize target scope, sensitive-kind gating, and rejection of the legacy broad include-path configuration.

## Final live acceptance

Repository tests passed:

```text
64 passed in 0.71s
```

The corrected source sync succeeded as the `infra-assurance` service identity with `KUBECONFIG` explicitly removed:

```text
status: COMPLETE
revision: 5767e0a4c583d0a0e8c87b2e24c42eaeb822a3b4
normalized_records: 27
skipped_documents: 3
errors: []
```

No false duplicate identities remained. FastAPI declarations were rendered into the intended namespaces `fastapi-platform-dev` and `fastapi-platform`, and the transient Kustomize worktree check returned no residual paths.

The subsequent drift evaluation completed with 26 records in sync and one real Ingress host drift. The exact Git revision declares `k3s-master.soria-academie.fr`, while current observed evidence reports `k3s-master.behnam.fr` for `Ingress/validation/nginx-validation`.

The drift is preserved for operator attention. The platform does not mutate either Git or Kubernetes in this read-only phase.
