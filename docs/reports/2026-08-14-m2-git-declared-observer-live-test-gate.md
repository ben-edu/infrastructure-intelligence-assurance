# Git Declared Observer Live Test Gate — 2026-08-14/15

## Status

Authentication accepted; parser/source-scope fixes pending final management-host acceptance.

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

## Live evidence already observed

The dedicated public key was initially attached to the wrong repository. Direct SSH authentication exposed the mistake without revealing private key material. The same key was moved to the intended repository.

Current direct SSH authentication succeeds as:

```text
ben-edu/api-cluster-infra
```

The observer successfully fetched exact revision:

```text
5767e0a4c583d0a0e8c87b2e24c42eaeb822a3b4
```

The first implementation used `kubectl create --dry-run=client` as a YAML parser. Without a kubeconfig, all supported documents failed normalization. Supplying the read-only kubeconfig as a diagnostic allowed 16 records to normalize, proving an unintended parser dependency on live Kubernetes configuration.

That diagnostic also produced duplicate FastAPI identities because the original source mapping recursively scanned raw Kustomize base, overlay, and patch YAML as if every file were an independent final declaration.

These results are treated as implementation defects, not accepted partial operation.

## Revised acceptance requirements

1. Repository tests pass from the management-host checkout.
2. Bootstrap preserves the existing Kubernetes observer and existing dedicated Git deploy key.
3. Git source sync succeeds without setting `KUBECONFIG` for the Git CLI.
4. Exact Git revision is recorded.
5. Direct manifests normalize locally.
6. FastAPI dev/prod declarations come only from rendered Kustomize targets at the exact Git revision.
7. No false default-namespace duplicates are produced from raw base/patch files.
8. `Secret`, `ConfigMap`, unsupported kinds, environment values, and raw manifest bodies are absent from declared evidence.
9. Transient Kustomize worktrees are removed after rendering.
10. Drift is evaluated against the current live Kubernetes snapshot without conflating evidence planes.
11. Any real render/normalization/source failure remains distinct from zero drift.
12. `mutation_allowed` remains `false` and Kubernetes RBAC is unchanged.

## Known first live comparison

The source repository contains:

```text
kubernetes/validation/nginx/nginx-validation.yaml
```

That manifest declares:

- Namespace `validation`;
- Deployment `validation/nginx-validation`;
- Service `validation/nginx-validation`;
- Ingress `validation/nginx-validation`.

The FastAPI Kustomize targets additionally exercise environment-specific namespace and image rendering.

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

Temporary Git worktrees used for Kustomize rendering are operational scratch state, not evidence artifacts, and must be removed after each sync.

The private key and raw repository/rendered manifest content must never be copied into reports, prompts, or evidence artifacts.
