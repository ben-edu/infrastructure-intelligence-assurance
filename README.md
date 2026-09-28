# Infrastructure Intelligence & Assurance Platform

Evidence-first infrastructure context and assurance platform.

## Current status

Milestones 0–4 are complete within their accepted scopes and live-validation boundaries.

Milestone 5 — Backup and Recovery Assurance is **not complete overall**. Its current authoritative read-only source-discovery phase is complete. Restore verification, integrity verification, retention effectiveness, accepted RPO/RTO evaluation, stronger physical failure-domain assurance, and application/database-consistent backup evidence remain explicitly `UNKNOWN` or deferred until stronger authoritative evidence or controlled mutation is available.

Milestone 6 — IaC Governance is **not complete overall**. Its current read-only governance phase is complete for the authoritative sources and safe observation paths currently available. Terraform apply outcome/full live-resource coverage/state authority and Ansible live managed-host coverage/execution outcomes/idempotence/configuration drift remain explicitly `UNKNOWN` until materially stronger evidence or authorized execution is available.

Milestone 7 — Operational Intelligence Layer is **complete within the accepted read-only scope**. The platform now has accepted operator-facing paths for attention, change/drift context, explicit unknown/stale/failed state, backup/recovery assurance gaps, incident-candidate grouping, task-scoped pre-change verification, post-change verification requirements, and a deterministic non-executable safest-next-action.

Milestone 8 — Reliability and Hardening is **complete within the accepted bounded scope**. The runtime baseline is evidence-backed, the one observed installed-module mismatch was reconciled, and the service now has an explicit four-minute start timeout. The final baseline is `COMPLETE`, with zero observation failures and zero selected `REQUIRES_CHANGE` items.

The initial delivery program is **complete within its accepted scope**. This does not promote the explicitly unresolved M5/M6 or M8 evidence gaps into completed capabilities. Further platform backup, restore testing, IaC execution assurance, external failure visibility, or broader runtime hardening is optional future scope requiring a new decision and its own evidence and authorization boundary.

For context-window-independent continuation, read:

```text
docs/PROJECT_CONTINUITY.md
HANDOFF.md
docs/reports/2026-09-28-m8-project-closure.md
```

Project Sources remain authoritative for durable goals, roadmap, architecture/trust principles, and operating rules. `HANDOFF.md` is the current execution checkpoint.

## Operator and AI-assisted deployment use

Use [`docs/OPERATOR_AND_AI_DEPLOYMENT_GUIDE.md`](docs/OPERATOR_AND_AI_DEPLOYMENT_GUIDE.md)
when preparing a new application, website, or service for K3s, Hestia, or the
hybrid platform. It defines the smallest useful AI context pack from current
assurance output, `ben-edu/infra-docs`, and the target project's own files.

The guide includes daily checks, the exact read-only K3s preflight command,
Hestia live-verification requirements, document-selection rules, a reusable AI
prompt, deployment stop conditions, and post-change verification. This
repository supplies evidence and planning context; Jenkins and the live
operator remain the deployment authorities.

## Current runtime model

```text
Private infrastructure Git
  -> normalized declared evidence + Git revision
                                  \
Kubernetes API                     \
  -> normalized observed evidence  \
  -> freshness / trust              -> declared-vs-observed drift
  -> topology / history / diff      -> compact change context
                                      -> workload operational inventory
Prometheus Operator config          -> configuration coverage
Prometheus HTTP API                 -> runtime target / alert evidence
Backup assurance evidence           -> compact backup/recovery assurance gaps
Incident candidate projection       -> grouped current signal candidates
                                      -> cross-domain operator attention
                                      -> task-scoped planning / AI consumption
```

The existing five-minute collector runs under the dedicated `infra-assurance` identity and produces the accepted cross-domain operator projection:

```text
scope: KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
mutation_allowed: False
```

At the accepted M8 gate, the installed runtime matched the repository (35/35
modules), the service unit matched the reviewed repository unit, and

```text
TimeoutStartSec=4min
```

was effective. The timeout reconciliation did not start or restart the service
and did not change the timer or infrastructure.

Installed ordering accepted at M7 closure:

```text
prometheus_rule_context_integration
< backup_assurance_foundation
< operator_attention_backup
< operator_attention_incident
```

Derived projections never replace their source evidence.

## Core operational artifacts

Current evidence and derived artifacts include:

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
/var/lib/infra-assurance/evidence/observability-coverage.json
/var/lib/infra-assurance/evidence/observability-coverage.md
/var/lib/infra-assurance/evidence/prometheus-runtime.json
/var/lib/infra-assurance/evidence/prometheus-runtime.md
/var/lib/infra-assurance/evidence/inventory.json
/var/lib/infra-assurance/evidence/inventory.md
/var/lib/infra-assurance/evidence/backup-assurance.json
/var/lib/infra-assurance/evidence/incident-candidates.json
/var/lib/infra-assurance/evidence/operator-attention.json
/var/lib/infra-assurance/evidence/operator-attention.md
/var/lib/infra-assurance/evidence/preflight.json
/var/lib/infra-assurance/evidence/preflight.md
```

Bounded Kubernetes history remains under:

```text
/var/lib/infra-assurance/history/kubernetes/index.json
/var/lib/infra-assurance/history/kubernetes/snapshots/*.json
```

Normalized Git declared state remains under:

```text
/var/lib/infra-assurance/declared/current/records.json
/var/lib/infra-assurance/declared/source-status.json
/var/lib/infra-assurance/git/repos/*.git
```

The current local JSON/Markdown/history storage is replaceable. Long-term lifecycle and platform-backup status remain explicitly unresolved future scope, not silently solved assumptions.

## M7 operator intelligence

The accepted operator layer can answer, within source/freshness boundaries:

- what needs attention now;
- what changed recently;
- what is unknown or stale;
- where declared/observed drift is represented;
- which backup/recovery conclusions remain unsupported or unknown;
- which current signals are grouped into incident candidates;
- what must be verified before a change;
- what the safest next verification/action is.

Important M7 trust semantics:

```text
incident candidate != confirmed incident
incident candidate != root cause
SUPPRESSED != RESOLVED
backup UNKNOWN != UNPROTECTED
restore verification UNKNOWN != recovery test overdue
recommendation != approval
```

The last accepted installed snapshot before M7 closure observed four incident candidates (`1 ACTIVE`, `3 SUPPRESSED`) with incident source coverage `PARTIAL`. These values are observed evidence, not fixed invariants.

## Planning preflight

The accepted base task-scoped deployment preflight remains read-only and separates:

```text
facts
conflicts
inferences
unknowns
required live verification
candidate plan
post-change verification
```

M7 added a repository adapter that enriches the existing preflight with accepted operator-attention context and emits a deterministic `safest_next_action` while keeping `mutation_allowed=false`.

The operator-aware adapter was validated against protected current evidence without deployment. Repository acceptance does not imply authorization to modify the installed management-host runtime.

## Workload operational inventory

The Dynamic Operational Inventory / CMDB projection covers currently observed:

```text
Deployment
StatefulSet
DaemonSet
```

Each workload entity combines traceable pointers and compact state from accepted evidence sources, including current observed state/freshness, safe replica and image fields, declared Git coverage, Service/Ingress/PVC relationships, recent changes, topology/drift attention, Prometheus Operator configuration coverage, and attributable runtime Prometheus signals.

Relationship inferences remain explicitly identified. For example, Service selector matching does not prove current EndpointSlice/Pod traffic flow.

## Trust rules

Always preserve:

```text
DECLARED state != OBSERVED state
NONE_OBSERVED_IN_BOUNDED_SOURCE != universal absence
FAILED_TO_OBSERVE != negative evidence
UNKNOWN != false
configuration declaration != execution outcome
infrastructure recovery != application/database-consistent backup
successful task/result != restore verification
incident candidate != confirmed incident/root cause
SUPPRESSED != RESOLVED
backup UNKNOWN != UNPROTECTED
recommendation != approval
```

A failed or stale current collection is never used to claim that a resource disappeared.

Git-declared and live-observed state remain separate evidence planes. A Git source failure, stale declaration, or cluster mismatch cannot become drift by inference.

Prometheus Operator configuration coverage is not promoted to scrape-health evidence. A failed Prometheus runtime query becomes `PARTIAL` or `FAILED_TO_OBSERVE`, never a false zero-target or zero-alert fact.

Raw Kubernetes Secret values are never collected. Sensitive Terraform state, passwords, tokens, private keys, complete sensitive connection strings, raw backup contents, and similar sensitive material must not enter persisted evidence or AI context.

`mutation_allowed` remains `false` unless an explicitly reviewed and authorized slice changes that boundary.

## M8 closure

M8 closed through three accepted slices:

1. a read-only runtime-hardening baseline;
2. exact reconciliation of the observed installed `__init__.py` mismatch;
3. an explicit four-minute service start timeout with bounded plan/apply/rollback tooling.

The final post-change baseline preserves four `UNKNOWN` categories: platform
evidence/history backup status, external failure visibility, historical overlap
and missed activations, and ACL/capability/MAC writability. An empty
`REQUIRES_CHANGE` list does not erase these unknowns or imply universal
hardening completeness.

There is no required next implementation slice. Any future expansion must begin
from a new scoped decision rather than reopening completed work by default.

## Validation

Repository regression suite at the accepted M8 timeout gate:

```text
483 passed in 5.94s
```

See `docs/reports/2026-09-28-m8-project-closure.md` for the complete closure
boundary, accepted evidence, preserved unknowns, risks, and deferred work.
