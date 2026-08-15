# ADR 0011 — Alertmanager Handling State and Conservative Correlation

## Status

Accepted for Milestone 4 implementation pending live validation.

## Context

The first Milestone 4 slice reads current Prometheus target health and alert evaluation state. Its accepted live run observed 21 active scrape targets and 11 firing Prometheus alerts. None of the 11 alerts could be safely attributed to a workload through the existing Service-to-controller inference path.

Alertmanager is the authoritative engine for grouping, routing, silencing, inhibition, and notification handling. The next useful slice is to determine how the current alerts are being handled without reading Alertmanager receiver configuration or inventing workload ownership.

Live discovery established the stable Service endpoint:

```text
namespace: monitoring
service: kube-prom-stack-alertmanager
port: 9093
```

Prometheus currently discovers one active Alertmanager endpoint at port 9093. The observed Pod IP is not used as platform configuration because it is runtime-ephemeral.

## Decision

Read only these Alertmanager API v2 resources through the Kubernetes API Service proxy:

```text
GET /api/v2/alerts?active=true&silenced=true&inhibited=true&unprocessed=true
GET /api/v2/silences?active=true&expired=false&pending=true
```

Persist two artifacts:

```text
/var/lib/infra-assurance/evidence/alertmanager-runtime.json
/var/lib/infra-assurance/evidence/alertmanager-runtime.md
/var/lib/infra-assurance/evidence/alert-attention.json
/var/lib/infra-assurance/evidence/alert-attention.md
```

`alertmanager-runtime` is the narrow normalized evidence source. `alert-attention` is a derived operator-facing projection that preserves alerts even when no workload owner can be proven.

## Exact Kubernetes authorization

Extend the existing namespaced observability proxy Role with only:

```text
resource: services/proxy
resourceName: kube-prom-stack-alertmanager:9093
verb: get
namespace: monitoring
```

The existing Prometheus proxy identity remains separately allowed in the same Role.

The observer must remain denied for:

- unqualified `kube-prom-stack-alertmanager` proxy access;
- `alertmanager-operated:9093` proxy access;
- Alertmanager proxy access in other namespaces;
- Secret listing;
- Kubernetes mutation.

The runtime is pinned to the reviewed tuple `monitoring/kube-prom-stack-alertmanager:9093`.

## Persisted Alertmanager alert fields

Keep only:

- generated Alertmanager alert ID based on the Alertmanager fingerprint;
- evidence ID and freshness timestamps;
- Alertmanager processing state: `ACTIVE | SUPPRESSED | UNPROCESSED | UNKNOWN`;
- handling state: `ACTIVE | SILENCED | INHIBITED | SILENCED_AND_INHIBITED | SUPPRESSED_OTHER | UNPROCESSED | UNKNOWN`;
- allowlisted labels: `alertname`, `severity`, `namespace`, `service`, `job`, `pod`, `container`, `node`;
- start/update/end timestamps;
- hashed silence references and suppression counts;
- conservative Prometheus correlation result.

Do not persist:

- free-form alert annotations;
- generator URLs;
- receiver names;
- receiver configuration;
- notification payloads;
- arbitrary labels such as `instance`;
- credentials or Secret values.

## Silence evidence

The silence API is used only to observe active/pending silence state.

Persist only:

- a hashed silence reference;
- evidence/freshness timestamps;
- `ACTIVE | PENDING | EXPIRED | UNKNOWN` state;
- start/end/update timestamps.

Do not persist silence matchers, comments, creator identity, or arbitrary annotations.

## Prometheus correlation

Alertmanager fingerprints and platform-generated Prometheus alert IDs are different identities and are not equated.

Correlation uses only the common allowlisted label projection:

```text
alertname
severity
namespace
service
job
pod
container
```

A correlation is accepted only when exactly one current normalized Prometheus alert has the same projection.

Results:

```text
MATCHED
UNRESOLVED
AMBIGUOUS
```

Zero matches remain `UNRESOLVED`. Multiple matches remain `AMBIGUOUS`. Neither case selects an alert by heuristic.

## Operational attention scope

A current Alertmanager alert remains first-class evidence even if workload attribution is unavailable.

Scope priority:

1. unique existing Prometheus-to-workload path -> `WORKLOAD`;
2. allowlisted `node` label -> `NODE`;
3. `namespace` + `service` labels -> `SERVICE`;
4. `namespace` label -> `NAMESPACE`;
5. otherwise -> `PLATFORM`.

A label-derived Service/Node/Namespace scope is an alert label scope, not proof of ownership or root cause.

## Failure semantics

Alert and silence reads are independent.

```text
both fail -> FAILED_TO_OBSERVE
one fails -> PARTIAL
successful reads with safely normalized records -> COMPLETE
```

A failed Alertmanager read never becomes a claim of zero alerts or zero silences.

Correlation and ownership gaps are explicit unknowns but do not downgrade a successful authoritative Alertmanager API observation.

## Consequences

Positive:

- current silencing/inhibition state becomes visible without replacing Alertmanager;
- platform/node/service alerts are retained instead of being dropped because they do not map to workloads;
- Prometheus and Alertmanager alert identities remain distinct;
- receiver secrets/configuration and free-form text stay outside evidence;
- the next incident-correlation slice can consume a compact alert-attention artifact.

Tradeoffs:

- the stable Kubernetes Service proxy is used rather than querying every Alertmanager peer directly;
- notification delivery success is not yet observed;
- receiver routing is intentionally not collected;
- label-based scope is not ownership proof;
- Alertmanager and Prometheus correlation may remain unresolved or ambiguous for some alerts.

## Deferred

- notification delivery evidence;
- receiver health;
- Loki correlation;
- OpenTelemetry correlation;
- Kubernetes event correlation;
- cross-source incident grouping/root-cause hypotheses.
