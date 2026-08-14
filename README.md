# Infrastructure Intelligence & Assurance Platform

Evidence-first infrastructure context and assurance platform.

## Current status

Milestone 0 — Evidence Contract is complete.

Milestone 1 — Kubernetes evidence, topology, and read-only planning preflight is complete and live-validated.

Milestone 2 adds a durable read-only change-awareness layer:

- bounded immutable Kubernetes snapshot history;
- trust-aware previous/current diff;
- evidence expiration and failed-collection signaling in comparisons;
- declared-vs-observed drift evaluation for normalized Git evidence;
- compact change context for operator/AI consumption.

The live Kubernetes observer runs on the management host with dedicated read-only credentials and a five-minute systemd timer.

## Runtime model

```text
Kubernetes API
  -> dedicated read-only observer identity
  -> normalized current evidence
  -> freshness and trust evaluation
  -> compact operational context
  -> topology
  -> bounded immutable history
  -> trust-aware diff
  -> declared-vs-observed drift
  -> compact change context
  -> task-scoped planning preflight / AI consumption
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

Bounded history:

```text
/var/lib/infra-assurance/history/kubernetes/index.json
/var/lib/infra-assurance/history/kubernetes/snapshots/*.json
```

The default history retention is 288 snapshots, approximately 24 hours at the current five-minute cadence. This is deliberately replaceable local storage, not a final long-term database decision.

## Trust rules

A failed or stale current collection is never used to claim that a resource disappeared.

Git-declared and live-observed state remain separate evidence planes. Drift is evaluated only when normalized Git evidence is actually configured. No declared source produces `DECLARED_STATE_UNAVAILABLE`, not zero drift.

Observed resources outside a configured declared scope are not automatically classified as drift.

Raw Secret values are never collected and the Kubernetes observer RBAC has no Secret access or mutating verbs.

## Install or refresh on the management host

```bash
sudo CLUSTER_ID=k3s-main ./scripts/bootstrap-observer.sh
```

No additional Kubernetes permission is required for Milestone 2.

## Inspect history

```bash
iia-k8s-history status
iia-k8s-history list --limit 10
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
- `docs/milestone-2-history-diff-drift.md` for the current Milestone 2 slice.
