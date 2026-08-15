# Milestone 4 Kubernetes Event Correlation Live Test Gate — 2026-08-15

## Status

Accepted on `mgmt-automation`.

## Scope

Validate bounded recent Kubernetes Event observation and conservative correlation with the already accepted Prometheus/Alertmanager alert-attention projection.

## Accepted repository/runtime gate

```text
branch: feature/m4-kubernetes-event-correlation
implementation head tested: 0e656734eb53b8b3f5789313ed29b3d8a74c9121
pytest: 125 passed in 0.89s
observer service: status=0/SUCCESS
Git declared source: COMPLETE
Prometheus source: COMPLETE
Alertmanager source: COMPLETE
Kubernetes Event source: COMPLETE
mutation_allowed: false
```

Only acceptance-report/Handoff metadata and removal of temporary branch-only placeholders were changed after the tested implementation head. The runtime implementation tree itself was not altered by those metadata operations.

The systemd oneshot completed successfully and the existing Git declared-state observer remained `COMPLETE` at revision `5767e0a4c583d0a0e8c87b2e24c42eaeb822a3b4` with 27 normalized declarations.

## Accepted RBAC boundary

```text
list Events cluster-wide: yes
create Event: no
list Pods cluster-wide: no
list Secrets cluster-wide: no
create Deployment: no
```

This slice adds only read-only core/v1 Event access. It does not add Pod read access and does not add any mutation capability.

## Accepted Event source bounds

```text
window_seconds: 3600
max_events: 500
window_truncated: false
```

The first live run returned one current Event and therefore did not exercise truncation in production. The `PARTIAL` truncation behavior remains covered by tests.

## Current live Event evidence

```text
events_seen_from_api: 1
events_recent: 1
events_warning: 1
events_normal: 0
events_unknown_type: 0
```

The single recent Warning Event was:

```text
reason: ProbeWarning
subject: Pod/moodle/moodle-b49d869bd-flsr6
count: 758740
```

The large occurrence count is retained as Kubernetes-reported structured evidence. It is not interpreted as severity or root cause by this slice.

## Current live correlation

The current alert-attention projection contained 10 records in this run. This differs from the prior accepted Alertmanager run that observed 11 alerts; alert state is time-varying evidence, and the Event-correlation artifact correctly used the 10 attention records generated in the same current runtime cycle.

```text
alert attention records: 10
event correlation records: 10
cardinality match: true
attention_with_related_warning_events: 1
attention_without_direct_warning_match: 9
attention_event_correlation_unknown: 0
warning_events_recent: 1
warning_events_related_to_attention: 1
warning_events_without_attention_match: 0
```

The one match was:

```text
attention scope: Namespace/moodle
handling: INHIBITED
related Event: ProbeWarning on Pod/moodle/moodle-b49d869bd-flsr6
basis:
  NAMESPACE_SCOPE_MEMBERSHIP
  RECENT_KUBERNETES_WARNING_EVENT
```

This is intentionally namespace-level supporting context. The Pod name was not used to infer Deployment/StatefulSet/DaemonSet ownership.

Both current `Platform/k3s-main` attention records remained:

```text
NO_DIRECT_EVENT_MATCH
```

with zero related Events. Platform alerts are therefore not broadly associated with unrelated cluster Events.

## Sensitive/free-form exclusion

Accepted live guard:

```text
forbidden projected keys: none
raw URL markers: false
```

Persisted Event evidence excludes:

- `message` / `note`;
- deprecated source host / reporting instance;
- arbitrary annotations and labels;
- raw object UID;
- credentials, passwords, tokens, private keys, and Secret values.

Event reason is restricted to a bounded structural token; URL-like/free-form values are converted to `REDACTED_REASON`.

## Failure and bounded-window semantics

The accepted live run was `COMPLETE`, so its nine no-match records can safely be represented as `NO_DIRECT_EVENT_MATCH` for the modeled one-hour Event window.

If a future Event read fails, source state becomes `FAILED_TO_OBSERVE`. If more than 500 recent Events require truncation, source state becomes `PARTIAL`. In either case unsupported no-match correlation becomes `UNKNOWN` rather than a false negative.

## Acceptance conclusion

The slice is accepted because:

1. all repository tests passed;
2. prior Git/Kubernetes/Prometheus/Alertmanager evidence remained healthy;
3. Event access is read-only and Pod/Secret/mutation access remains denied;
4. Event source bounds are explicit;
5. free-form Event text and sensitive fields are excluded;
6. one real current Warning Event was retained as structured evidence;
7. correlation used an explicit namespace-membership basis;
8. Pod-name controller inference was not introduced;
9. platform alerts were not broadly correlated;
10. Event relations remain supporting context rather than root-cause claims;
11. `mutation_allowed=false` remains binding.

## Trust boundary

Kubernetes remains authoritative for Event records. Prometheus and Alertmanager remain authoritative for their respective signals. This slice adds bounded structured Event context and conservative relations only; it does not replace logging, infer Pod controller ownership, or claim root cause.
