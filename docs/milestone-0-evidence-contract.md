# Milestone 0 — Evidence Contract

## Purpose

Define the smallest contract needed to represent trustworthy Kubernetes evidence and produce compact, task-oriented AI context without accessing live infrastructure.

This milestone deliberately does not define a CMDB, persistent database, monitoring architecture, backup system, UI, OpenTelemetry pipeline, or collector runtime.

## 1. Observation envelope

Each observation is represented by one `ObservationEnvelope`.

The envelope separates three independent dimensions:

1. `existence` — what the evidence says about whether the subject exists;
2. `observation_status` — whether the observation attempt succeeded completely;
3. freshness — whether a previously successful observation is still current.

These dimensions must not be collapsed into one status enum.

### Minimum fields

- `schema_version`
- `evidence_id`
- `plane`
- `subject`
- `existence`
- `observation_status`
- `attempted_at`
- `observed_at`
- `expires_at`
- `data`
- `provenance`
- `errors`

### Kubernetes subject identity

For the first vertical slice, a subject is identified by:

- cluster;
- API group;
- kind;
- namespace, when namespaced;
- name.

Kubernetes runtime UID is intentionally not the primary cross-plane identity because declared Git state normally does not contain the live UID.

## 2. Provenance

Minimum provenance answers: where did this evidence come from, how was it obtained, and with which collector version?

Required fields:

- `source_type`
- `source_id`
- `collector`
- `collector_version`
- `operation`

`revision` is optional and is used when a source has a stable revision, such as a Git commit.

Examples:

```json
{
  "source_type": "kubernetes_api",
  "source_id": "lab-k3s",
  "collector": "kubernetes-observer",
  "collector_version": "0.1.0",
  "operation": "GET Deployment/soria/api"
}
```

```json
{
  "source_type": "git",
  "source_id": "github.com/example/platform-config",
  "collector": "git-observer",
  "collector_version": "0.1.0",
  "operation": "read manifests/soria/deployment.yaml",
  "revision": "8d09c56"
}
```

## 3. Freshness and expiration

Freshness is derived rather than stored in the evidence envelope.

For a successful observation:

```text
now <= expires_at  -> CURRENT
now >  expires_at  -> STALE
```

`expires_at` does not mean the evidence should be deleted. It means that the evidence is no longer sufficient to claim current state.

Stale evidence may still be reported as last-known state, but any current-state claim must require new observation or explicit live verification.

Milestone 0 does not standardize production TTL values. Example timestamps exist only to validate behavior.

## 4. Status semantics

### PRESENT

Sufficient evidence says the subject exists.

### ABSENT

Sufficient and complete evidence says the subject does not exist.

Example: a successfully authorized, scoped Kubernetes GET returns `404 NotFound` for the exact resource.

`ABSENT` requires `observation_status=COMPLETE` in schema version 0.1.

### UNKNOWN

There is not enough evidence to determine existence.

This can mean that no observation has yet established the fact, or that the latest attempt failed.

### FAILED_TO_OBSERVE

An observation attempt was made but did not produce trustworthy subject state, for example because of timeout, authentication failure, authorization failure, or source unavailability.

In version 0.1:

```text
FAILED_TO_OBSERVE -> existence = UNKNOWN
```

A failed observation must never be interpreted as absence.

### PARTIAL

Only part of the requested scope or fields were observed successfully.

Facts that were successfully observed may be used, but missing data from the unobserved part must not be interpreted as absence.

### STALE

`STALE` is a freshness classification, not an existence or collection result.

A record can therefore be:

```text
PRESENT + COMPLETE + STALE
```

This means the last successful evidence said the resource was present, but that evidence has expired.

## 5. Declared and observed planes

Declared Git state and observed live state are represented as separate evidence envelopes.

```text
plane = declared
plane = observed
```

Declared Git evidence answers what reviewed configuration declares.

Observed Kubernetes evidence answers what the runtime API exposed during observation.

Neither plane overwrites the other. A later milestone may compare them and classify drift, but Milestone 0 only preserves enough identity and provenance to make that comparison possible.

## 6. Security exclusions

Evidence, snapshots, examples, tests, prompts, and AI context must exclude:

- authentication credential values;
- private cryptographic material;
- kubeconfig embedded credential material;
- Kubernetes Secret payload values;
- sensitive Terraform state payload values;
- complete sensitive connection strings;
- raw environment-variable values when they may carry credentials.

Operationally useful references may retain non-secret metadata such as a Secret object name, Secret type, and key names, but never the corresponding values.

The default collection rule is: if a field is not necessary for the operational question, do not collect it.

## 7. Minimum task-oriented AI context

AI receives compact normalized context, not raw Kubernetes objects.

The minimum context contains:

- task and scope;
- whether mutation is allowed;
- generation time;
- evidence-backed facts with declared/observed plane preserved;
- unknowns;
- observation failures;
- explicitly marked inferences;
- required live verification.

Every fact and inference references the evidence IDs that support it.

For Milestone 0, `mutation_allowed` is always `false`.

## 8. Deferred by design

The following are outside this contract:

- collector implementation;
- Kubernetes authentication;
- live API queries;
- CMDB entities and relationships;
- dependency graph;
- persistent database/storage model;
- history retention;
- drift engine;
- metrics/logs/traces;
- OpenTelemetry topology;
- backup assurance;
- Terraform/Ansible evidence models;
- UI/dashboard;
- automation execution.

## Acceptance for Milestone 0

Milestone 0 is implementable and testable when:

1. all provided example observation envelopes validate;
2. invalid combinations such as `ABSENT + FAILED_TO_OBSERVE` are rejected;
3. freshness can be deterministically derived from `expires_at`;
4. declared and observed examples preserve separate planes for the same subject;
5. the sample AI context validates and references evidence rather than embedding raw source output;
6. examples contain no credential or secret values.
