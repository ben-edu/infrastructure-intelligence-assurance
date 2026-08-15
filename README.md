# Infrastructure Intelligence & Assurance Platform

Evidence-first infrastructure context and assurance platform.

## Current status

Milestone 0 — Evidence Contract is complete.

Milestone 1 — Kubernetes evidence, topology, and read-only planning preflight is complete and live-validated.

Milestone 2 now provides:

- bounded immutable Kubernetes snapshot history;
- trust-aware previous/current diff;
- evidence expiration and failed-collection signaling in comparisons;
- a dedicated read-only Git declared-state observer;
- renderer-aware normalization of supported Kubernetes declarations;
- declared-vs-observed drift evaluation without evidence-plane conflation;
- compact change context for operator/AI consumption.

The live loop runs on the management host every five minutes.

## Runtime model

```text
Private infrastructure Git
  -> dedicated read-only deploy key
  -> bare Git cache
  -> explicit direct manifests + rendered Kustomize targets
  -> supported-document safety gate
  -> local normalization + exact Git revision
                                  \
Kubernetes API                     \
  -> dedicated read-only identity   \
  -> normalized observed evidence    -> declared-vs-observed drift
  -> freshness / trust              -> compact change context
  -> topology / history / diff      -> planning / AI consumption
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

## Git declared-state source

The first configured source is:

```text
github.com/ben-edu/api-cluster-infra
branch: main
cluster: k3s-main
```

Authentication uses a dedicated read-only SSH deploy key generated on the management host. The runtime does not reuse a personal SSH key or administrator GitHub credential.

The declared scope is explicit. Direct manifests currently include BookStack and `validation/nginx`; FastAPI is observed only through its rendered dev and prod Kustomize overlays. Raw Kustomize bases and patches, Helm values, Secret examples, and unrelated YAML are not silently treated as final declarations.

The Git observer keeps a bare repository cache. For Kustomize rendering only, it materializes the exact fetched revision into a short-lived detached worktree under observer state and removes that worktree after rendering. Raw and rendered manifests are not persisted as evidence artifacts.

Direct supported manifests are parsed locally with `kubectl patch --local`. The parser/render environment removes kubeconfig variables so Git observation is not coupled to live Kubernetes discovery.

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

`Secret`, `ConfigMap`, and unsupported kinds are gated before object parsing and are not serialized into declared evidence. For supported workload documents, only explicitly modeled non-sensitive fields are retained. Raw environment values, Secret payloads, arbitrary ConfigMap payloads, credentials, and connection strings are not emitted.

The source state is independently recorded as:

```text
COMPLETE
PARTIAL
FAILED_TO_OBSERVE
```

A failed Git refresh does not make the previous declared bundle current. Drift becomes unknown until the source is observed successfully again.

## Trust rules

A failed or stale current Kubernetes collection is never used to claim that a resource disappeared.

Git-declared and live-observed state remain separate evidence planes. A Git source failure, stale declaration, partial declaration scope, or cluster mismatch cannot become a confident drift claim by inference.

Observed resources outside the configured declared scope are not automatically classified as drift.

Raw Kubernetes Secret values are never collected and the Kubernetes observer RBAC has no Secret access or mutating verbs.

`mutation_allowed` remains `false`.

## Install or refresh on the management host

```bash
sudo CLUSTER_ID=k3s-main ./scripts/bootstrap-observer.sh
```

The bootstrap creates the dedicated Git deploy key if it does not already exist and prints its public half. Register that public key on `ben-edu/api-cluster-infra` as a read-only deploy key. No additional Kubernetes permission is required.

After the deploy key is registered, the existing five-minute collector automatically refreshes Git declared evidence before each Kubernetes observation.

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
- `docs/milestone-2-history-diff-drift.md` for the current Milestone 2 architecture;
- `docs/milestone-2-git-declared-observer.md` for the current Git observer slice.
