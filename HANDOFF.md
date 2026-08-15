# Project Handoff

This is the compact continuation checkpoint for the Infrastructure Intelligence & Assurance Platform. Project Sources remain authoritative for durable goals, roadmap, trust principles, and operating rules.

## Resume protocol

1. Read Project Sources.
2. Read `HANDOFF.md` from `main`.
3. Check open PRs in `ben-edu/infrastructure-intelligence-assurance`.
4. If an active project PR has a newer `HANDOFF.md`, prefer that branch version for execution state.
5. Read only the ADR, milestone doc, and live-test report relevant to the active slice.
6. Prefer repository/live evidence over chat reconstruction.

## Stable checkpoint

- repository: `ben-edu/infrastructure-intelligence-assurance`
- stable branch: `main`
- current main HEAD after post-PR26 continuity merge: `cebdd9fdc96ea7104c409c048d2eaba2f58f2ffc`
- accepted PR #26 code merge: `d4170dd33731754021e3aea8ca46b84c0163fcf6`
- management host: `mgmt-automation`
- checkout: `~/projects/infrastructure-intelligence-assurance`
- cluster: `k3s-main`
- runtime user: `infra-assurance`
- oneshot: `infra-assurance-kubernetes.service`
- timer: every 5 minutes

Milestones 0–3 are live validated. Milestone 4 accepted/live-validated slices include Prometheus runtime, Alertmanager correlation, Kubernetes Events, incident candidates, bounded routing ownership, validated alert identity, routing integration, scope-aware drill-down, and bounded Prometheus rule context.

Known intentional drift remains:

```text
Ingress/validation/nginx-validation
Git:  k3s-master.soria-academie.fr
Live: k3s-master.behnam.fr
```

## Accepted baseline relevant to current work

Final accepted incident contract before the active slice:

```text
incident_candidates_version: 0.3
drilldown_policy.version: 0.1
drilldown_policy.mode: SCOPE_AWARE
mutation_allowed: false
```

Accepted live candidate set:

```text
SUPPRESSED Namespace/keycloak    alerts=2 related_workloads=2
SUPPRESSED Namespace/monitoring  alerts=5 related_workloads=9
SUPPRESSED Namespace/moodle      alerts=2 related_workloads=2 related_warning_events=1
ACTIVE     Platform/k3s-main     alerts=2 names=KubeCPUOvercommit,Watchdog related_workloads=0
```

The active Platform candidate currently retains:

```text
VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER
VERIFY_PLATFORM_SIGNAL_INPUTS  -> PROMETHEUS_KUBERNETES
```

PR #26 accepted rule source:

```text
prometheus_rule_context_version: 0.1
source.status: COMPLETE
mutation_allowed: false
active alert names: KubeCPUOvercommit, Watchdog
matched rule names: KubeCPUOvercommit, Watchdog
unmatched: none
rule records: 2
rule health OK: 2
rules FIRING: 2
expression_persisted: false
unknowns: none
errors: none
```

Accepted exact rule metadata:

```text
KubeCPUOvercommit | group=kubernetes-resources | state=FIRING | health=OK | duration=600s
Watchdog          | group=general.rules        | state=FIRING | health=OK | duration=0s
```

Rule metadata is observed Prometheus context, not current metric-input evidence or root-cause proof. `PROMETHEUS_RULE_INPUTS` remains required live verification.

## Active work — PR #28 Prometheus rule-context integration

- PR: `#28 Milestone 4 integrate Prometheus rule context into incident drill-down`
- branch: `feature/m4-prometheus-rule-integration`
- base main: `cebdd9fdc96ea7104c409c048d2eaba2f58f2ffc`
- package version: `0.18.0`
- status: Draft; pending repository and management-host live acceptance
- RBAC change: none
- infrastructure/telemetry query added: none
- Loki/OpenTelemetry added: none
- mutation: none

Runtime order becomes:

```text
kubernetes_runtime
routing_ownership
alert_scope_runtime
incident_runtime
routing_context_integration
scope_aware_drilldown
prometheus_rule_context
prometheus_rule_context_integration
```

The new post-step reads only local:

```text
/var/lib/infra-assurance/evidence/incident-candidates.json
/var/lib/infra-assurance/evidence/prometheus-rule-context.json
```

Final contract if accepted:

```text
incident_candidates_version: 0.4
prometheus_rule_context_integration.version: 0.1
prometheus_rule_context_integration.mode: EXACT_COMPLETE_ONLY
mutation_allowed: false
```

### Promotion rule

An ACTIVE candidate receives `COMPLETE_EXACT_RULE_MATCH` only when:

1. incident input is v0.3 and rule-context input is v0.1;
2. cluster identity matches;
3. both mutation flags are false;
4. rule source is `COMPLETE`;
5. existing `candidate_id` joins exactly;
6. candidate alert names exactly equal candidate-context alert names;
7. unmatched alert names are empty;
8. every referenced rule ID exists;
9. matched rules cover the exact current candidate alert-name set.

No fuzzy matching is allowed.

### Safe projection

Attached rule context may contain only accepted rule identity/state metadata:

```text
rule_id
evidence_id
alertname
group_name
rule_type
state
health
duration_seconds
keep_firing_for_seconds
evaluation_time_seconds
last_evaluation
expression_persisted=false
```

PromQL/query, labels, annotations, file paths, embedded alerts, last-error text, raw payloads, URLs, credentials, tokens, and connection strings remain excluded.

### Recommendation refinement

For complete exact ACTIVE Platform context only:

```text
VERIFY_PLATFORM_SIGNAL_INPUTS -> PROMETHEUS_KUBERNETES
```

is replaced with:

```text
VERIFY_PROMETHEUS_RULE_INPUTS -> PROMETHEUS_RULE_INPUTS
```

Preserve:

```text
VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER
```

Partial/failed/missing/mismatched/unmatched rule context retains the generic `PROMETHEUS_KUBERNETES` target and records an explicit integration unknown. Suppressed candidates are not enriched.

Relevant files:

```text
src/infra_assurance/prometheus_rule_context_integration.py
schemas/incident-prometheus-rule-context-integration.schema.json
docs/decisions/0019-integrate-exact-prometheus-rule-context.md
docs/milestone-4-prometheus-rule-context-integration.md
docs/reports/2026-08-15-m4-prometheus-rule-context-integration-live-test-gate.md
```

## Exact next step

Run PR #28 repository/live gate on `mgmt-automation`:

1. confirm no RBAC diff;
2. confirm integration module has no query-capable client;
3. run full pytest;
4. if green, bootstrap observer;
5. confirm `prometheus_rule_context_integration` is final and exits `0/SUCCESS`;
6. validate incident v0.4 / integration v0.1 / `EXACT_COMPLETE_ONLY`;
7. verify active candidate exact rule context and safe projection;
8. if current rule context remains complete, verify `PROMETHEUS_RULE_INPUTS` replaces generic `PROMETHEUS_KUBERNETES` only on eligible Platform candidate;
9. verify Alertmanager current-condition check remains;
10. verify suppressed candidates are not enriched, recommendation summary matches final checks, and sensitive/raw URL guards remain clean.

Do not merge PR #28 before live acceptance.

## Trust invariants

- observation credentials remain separate from future control credentials;
- infrastructure interaction remains read-only;
- collector failure is explicit;
- stale is not current;
- unknown is not absent;
- inference is not fact;
- declared and observed state remain separate;
- specialized systems remain authoritative;
- no passwords, tokens, private keys, raw Kubernetes Secret values, sensitive Terraform state, or complete sensitive connection strings enter evidence/AI context;
- current generated operational artifacts keep `mutation_allowed=false`.

## Maintenance rule

Keep this file compact. Update it only for accepted/merged slices, active PR changes, material live-gate outcomes, important blockers/risks, exact next-step changes, or runtime identity changes needed for continuation. Do not append transcripts or raw command logs.
