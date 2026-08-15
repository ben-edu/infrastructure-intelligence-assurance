# Infrastructure Intelligence & Assurance Platform

Evidence-first infrastructure context and assurance platform.

## Current status

Milestone 0 — Evidence Contract is complete.

Milestone 1 — Kubernetes evidence, topology, and read-only planning preflight is complete and live-validated.

Milestone 2 — bounded history, trust-aware diff, dedicated Git declared-state observation, and declared-vs-observed drift are complete and live-validated.

Milestone 3 now starts with a workload-centric operational inventory that joins existing evidence without creating a new source of truth.

The live loop runs on the management host every five minutes.

## Runtime model

```text
Private infrastructure Git
  -> dedicated read-only deploy key
  -> bare Git cache
  -> explicit direct-manifest and renderer targets
  -> normalized declared evidence + Git revision
                                  \
Kubernetes API                     \
  -> dedicated read-only identity   \
  -> normalized observed evidence    -> declared-vs-observed drift
  -> freshness / trust              -> compact change context
  -> topology / history / diff      -> workload operational inventory
                                      -> planning / AI consumption
```

Current-state and task artifacts remain separate from immutable history.

```text
/var/lib/infra-assurance/evidence/kubernetes.json
/var/lib/infra-assurance/evidence/context.json
/var/lib/infra-assurance/evidence/context.md
/var/lib/infra-assurance/evidence/topology.json
/var/lib/infra-assurance/evidence/topology.md
/var/lib/infra-assurance/evidence/diff.json
/var/lib/infra-assurance/evidence/diff.md
/var/lib/infra-assurance/evidence/drift.json
/var/lib/infra-assurance/evidence/drift.md
/var/lib/infra-assurance/evidence/change-context.json
/var/lib/infra-assurance/evidence/change-context.md
/var/lib/infra-assurance/evidence/inventory.json
/var/lib/infra-assurance/evidence/inventory.md
/var/lib/infra-assurance/evidence/preflight.json
/var/lib/infra-assurance/evidence/preflight.md
```

Bounded Kubernetes history:

```text
/var/lib/infra-assurance/history/kubernetes/index.json
/var/lib/infra-assurance/history/kubernetes/snapshots/*.json
```

Normalized Git declared state:

```text
/var/lib/infra-assurance/declared/current/records.json
/var/lib/infra-assurance/declared/source-status.json
/var/lib/infra-assurance/git/repos/*.git
```

The default Kubernetes history retention is 288 snapshots, approximately 24 hours at the current five-minute cadence. This remains replaceable local storage, not a final long-term database decision.

## Workload operational inventory

The first Dynamic Operational Inventory / CMDB projection covers currently observed:

```text
Deployment
StatefulSet
DaemonSet
```

Each workload entity combines traceable pointers and compact state from the existing evidence planes:

- current observed state and freshness;
- safe replica/scheduling fields and image references;
- direct Git declared coverage and workload comparison where available;
- Service selector-match relationships;
- composed Ingress route candidates;
- direct PVC references;
- latest related snapshot changes;
- related topology ambiguity and drift attention.

This inventory is derived state. Kubernetes evidence, Git-declared evidence, topology, history, and drift remain the supporting source artifacts.

A Service-to-workload relationship remains a selector-based inference. An Ingress route candidate composes an observed Ingress-to-Service reference with that inference and does not prove current Pod or EndpointSlice routing.

A workload missing from the configured Git scope is `OUTSIDE_DECLARED_SCOPE`, not automatically unmanaged or drifted. A namespace is not automatically treated as an application or ownership boundary.

## Git declared-state source

The first configured source is:

```text
github.com/ben-edu/api-cluster-infra
branch: main
cluster: k3s-main
```

The source mapping is explicit rather than a recursive YAML scan. BookStack and validation use configured direct manifest paths. FastAPI dev/prod use configured Kustomize targets rendered locally at the exact fetched revision. Helm values and example directories are outside the current declared-state contract.

Authentication uses a dedicated read-only SSH deploy key generated on the management host. The runtime does not reuse a personal SSH key or administrator GitHub credential.

The Git observer keeps a bare repository cache. Kustomize rendering uses a transient detached worktree at the exact fetched revision; it is removed after rendering and is not evidence storage.

Only these Kubernetes kinds can currently become declared evidence:

```text
Namespace
Deployment
StatefulSet
DaemonSet
Service
Ingress
PersistentVolumeClaim
```

`Secret`, `ConfigMap`, and unsupported kinds are not serialized into declared evidence. For supported workload documents, only explicitly modeled non-sensitive fields are retained. Raw environment values, Secret payloads, arbitrary ConfigMap payloads, credentials, and connection strings are not emitted.

The source state is independently recorded as:

```text
COMPLETE
PARTIAL
FAILED_TO_OBSERVE
```

A failed Git refresh does not make the previous declared bundle current. Drift becomes unknown until the source is observed successfully again.

The first live Git observer acceptance completed successfully at revision `5767e0a4c583d0a0e8c87b2e24c42eaeb822a3b4`: 27 declarations normalized, 26 were in sync, and one evidence-backed Ingress host drift was surfaced without automatic mutation.

## Trust rules

A failed or stale current Kubernetes collection is never used to claim that a resource disappeared.

Git-declared and live-observed state remain separate evidence planes. A Git source failure, stale declaration, or cluster mismatch cannot become drift by inference.

Observed resources outside the configured declared scope are not automatically classified as drift.

Raw Kubernetes Secret values are never collected and the Kubernetes observer RBAC has no Secret access or mutating verbs.

`mutation_allowed` remains `false`.

## Install or refresh on the management host

```bash
sudo CLUSTER_ID=k3s-main ./scripts/bootstrap-observer.sh
```

The existing five-minute collector refreshes Git declared evidence before each Kubernetes observation and then emits the current projections.

## Query workload inventory

```bash
sudo -u infra-assurance iia-inventory summary
sudo -u infra-assurance iia-inventory list
sudo -u infra-assurance iia-inventory list --attention-only
sudo -u infra-assurance iia-inventory list --namespace validation
sudo -u infra-assurance iia-inventory show \
  --namespace validation \
  --kind Deployment \
  --name nginx-validation
```

The inventory CLI reads the generated artifact only and performs no additional infrastructure query.

## Inspect Git source status

```bash
sudo -u infra-assurance iia-git-source status
sudo -u infra-assurance iia-git-source public-key
```

A manual safe refresh is also available:

```bash
sudo -u infra-assurance iia-git-source sync
```

## Inspect history

```bash
sudo -u infra-assurance iia-k8s-history status
sudo -u infra-assurance iia-k8s-history list --limit 10
```

## Run the read-only planning preflight

```bash
sudo -u infra-assurance iia-k8s-preflight \
  --request /etc/infra-assurance/examples/hypothetical-app-deployment.json
```

## Validate locally

```bash
python3 -m pytest -q
```

See:

- `docs/milestone-1-first-slice.md` for the collector trust boundary;
- `docs/decisions/0002-compact-operational-context.md` for context compaction;
- `docs/decisions/0003-kubernetes-topology-projection.md` for relationship trust semantics;
- `docs/decisions/0004-task-scoped-planning-preflight.md` for planning trust semantics;
- `docs/decisions/0005-bounded-file-history-and-trust-aware-diff.md` for history/diff semantics;
- `docs/decisions/0006-git-declared-drift-without-plane-conflation.md` for drift semantics;
- `docs/decisions/0007-dedicated-git-declared-observer.md` for the Git observer boundary;
- `docs/decisions/0008-workload-centric-operational-inventory.md` for the first CMDB projection boundary;
- `docs/milestone-2-history-diff-drift.md` for the Milestone 2 architecture;
- `docs/milestone-3-workload-operational-inventory.md` for the current Milestone 3 slice.
