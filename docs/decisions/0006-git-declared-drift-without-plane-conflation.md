# ADR 0006 — Evaluate Git-Declared Drift Without Conflating Evidence Planes

## Status

Accepted for Milestone 2 implementation.

## Context

The architecture contract assigns different authority to Git and live infrastructure:

- Git represents reviewed declared state;
- live APIs represent runtime observed state;
- a difference is drift;
- neither plane may overwrite the meaning of the other.

A missing declared source is not evidence that runtime resources are unmanaged, and it is not evidence that drift is zero.

The platform also must not ingest arbitrary repository contents into AI context because Kubernetes manifests can contain Secret values, ConfigMap payloads, environment values, or sensitive connection material.

## Decision

The first Milestone 2 drift engine consumes only normalized declared `ObservationEnvelope` records.

A record is accepted as declared Git evidence only when:

- `plane=declared`;
- `provenance.source_type=git`;
- a concrete Git `revision` is present;
- the Kubernetes subject identity is explicit.

Arbitrary YAML manifests are not read directly by the drift engine.

The first drift evaluation is declaration-driven: every configured declared record is compared with the matching current observed identity. Runtime resources outside the configured declared scope are not automatically classified as drift.

The first result classes are:

- `IN_SYNC` — all comparable declared fields match current observed evidence;
- `DRIFT` — existence or a comparable declared field differs;
- `UNKNOWN` — current observed evidence or declared evidence is stale/failed/partial, or the current collector does not expose a comparable field.

If no normalized declared source is configured, the report status is:

```text
DECLARED_STATE_UNAVAILABLE
```

This is intentionally different from an evaluated report with zero drift.

## Current real source candidate

Repository discovery identified `ben-edu/api-cluster-infra` as a real infrastructure repository. Its `kubernetes/` tree contains workload declarations, including the existing validation NGINX manifest.

The current Milestone 2 slice does not automatically clone or parse all repository manifests. A dedicated Git observer identity, explicit source mapping, and safe normalization boundary must be established before that repository is fed into the drift engine automatically.

## Security

The declared evidence boundary must exclude:

- Kubernetes Secret payloads;
- secret-bearing environment values;
- complete sensitive connection strings;
- private keys and tokens;
- arbitrary ConfigMap payloads unless explicitly proven non-sensitive and required.

Git provenance may retain repository identity, source path, and revision.

## Consequences

- Drift reports remain evidence-backed instead of inferred from repository absence.
- Git and runtime state can be compared without merging the records.
- Future Git collectors can evolve independently from the drift engine as long as they emit the declared evidence contract.
- The first live M2 run may correctly report declared state as unavailable until the Git observer is configured.

## Deferred

- dedicated Git observer credential;
- automated fetch of private infrastructure repositories;
- safe YAML/Kustomize/Helm normalization;
- declared scope completeness semantics for observed-only resources;
- repository ownership and CMDB linkage.
