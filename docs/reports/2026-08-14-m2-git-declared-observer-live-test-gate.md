# Git Declared Observer Live Test Gate — 2026-08-14/15

## Status

Accepted on the management host.

The dedicated Git observer now satisfies the Milestone 2 live gate. One real declared-vs-observed drift remains visible and is intentionally not mutated by this read-only phase.

## Scope

Validate the first autonomous Git-declared evidence source for Milestone 2.

Source:

```text
github.com/ben-edu/api-cluster-infra
branch: main
cluster: k3s-main
```

Configured direct manifests:

```text
kubernetes/bookstack/01-pvc.yaml
kubernetes/bookstack/02-mariadb.yaml
kubernetes/bookstack/03-bookstack.yaml
kubernetes/validation/nginx/nginx-validation.yaml
```

Configured Kustomize targets:

```text
kubernetes/fastapi-platform/overlays/dev
kubernetes/fastapi-platform/overlays/prod
```

## Diagnostic history

The dedicated public key was initially attached to the wrong repository. Direct SSH authentication exposed the mistake without revealing private key material. The same key was moved to the intended repository and authentication then succeeded as `ben-edu/api-cluster-infra`.

The first observer implementation also exposed two defects during live testing:

1. `kubectl create --dry-run=client` still depended on Kubernetes configuration in this environment. Without a kubeconfig, supported manifests failed normalization.
2. Recursively scanning all YAML under `kubernetes/` treated Kustomize bases, overlays, and patches as independent final declarations, producing false duplicate identities.

The implementation was corrected so direct manifests are parsed locally and FastAPI dev/prod are taken only from rendered Kustomize targets at the exact Git revision.

## Final management-host acceptance

Repository branch:

```text
feature/m2-git-declared-observer
head: 6c3ff5d add durable Git declared-state observation
```

Repository tests:

```text
64 passed in 0.71s
```

The bootstrap completed successfully and the one-shot Kubernetes evidence service exited with `status=0/SUCCESS`.

Git source observation completed without an injected `KUBECONFIG`:

```text
status: COMPLETE
revision: 5767e0a4c583d0a0e8c87b2e24c42eaeb822a3b4
normalized_records: 27
skipped_documents: 3
errors: []
```

The transient Kustomize worktree check produced no remaining paths after the sync.

The 27 normalized declarations contain:

- direct BookStack PVC, Deployment, Service, and Ingress resources;
- direct validation Namespace, Deployment, Service, and Ingress resources;
- FastAPI dev resources rendered into namespace `fastapi-platform-dev`;
- FastAPI prod resources rendered into namespace `fastapi-platform`.

No false default-namespace duplicate identities were reported.

## Drift result

The final drift report was evaluated successfully:

```text
status: EVALUATED
declared_records: 27
in_sync: 26
drift: 1
unknown: 0
loader_errors: 0
```

The only drift is:

```text
Ingress/validation/nginx-validation
field: backends
declared host: k3s-master.soria-academie.fr
observed host: k3s-master.behnam.fr
service: nginx-validation
service_port: 80
path: /
```

The exact Git revision declares `k3s-master.soria-academie.fr`, so the mismatch is a real declared-vs-observed difference rather than parser, Kustomize, or identity noise.

No automatic repair is attempted. Initial platform phases remain read-only; resolving this drift requires deciding whether Git or the live cluster represents the intended target state and then making that change through the authoritative infrastructure workflow.

## Change context

The generated compact change context reported:

```text
mutation_allowed: false
recent_changes: 0
drift_attention: 1
unknowns: 0
required_live_verification: 0
```

The drift is therefore surfaced as evidence-backed operator attention, not converted into an inferred repair action.

## Acceptance result

All revised acceptance requirements pass:

1. Repository tests pass from the management-host checkout.
2. Bootstrap preserves the Kubernetes observer and dedicated Git identity.
3. Git source sync succeeds without injecting `KUBECONFIG` into the Git CLI.
4. Exact Git revision is recorded.
5. Direct manifests normalize locally.
6. FastAPI dev/prod declarations come only from rendered Kustomize targets at the exact revision.
7. No false default-namespace duplicates are produced from raw base/patch files.
8. Sensitive and unsupported documents do not become declared evidence.
9. Transient Kustomize worktrees are removed after rendering.
10. Drift is evaluated against current observed evidence without evidence-plane conflation.
11. Source/render/normalization failures remain distinct from zero drift.
12. `mutation_allowed` remains `false` and Kubernetes RBAC remains read-only.

## Expected persistent artifacts

```text
/etc/infra-assurance/git-source.json
/etc/infra-assurance/git/api-cluster-infra_ed25519
/etc/infra-assurance/git/api-cluster-infra_ed25519.pub
/etc/infra-assurance/git/known_hosts
/var/lib/infra-assurance/git/repos/*.git
/var/lib/infra-assurance/declared/current/records.json
/var/lib/infra-assurance/declared/source-status.json
/var/lib/infra-assurance/evidence/drift.json
/var/lib/infra-assurance/evidence/drift.md
/var/lib/infra-assurance/evidence/change-context.json
```

Temporary Git worktrees used for Kustomize rendering are operational scratch state, not evidence artifacts, and are removed after each sync.

The private key and raw repository/rendered manifest content must never be copied into reports, prompts, or evidence artifacts.
