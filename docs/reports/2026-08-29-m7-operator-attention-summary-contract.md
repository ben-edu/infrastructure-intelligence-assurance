# Milestone 7 — Operator Attention Summary Contract

Date: 2026-08-29
Status: ACCEPTED PENDING FULL-SUITE GATE
Mode: derived read-only projection over existing Kubernetes evidence artifacts

## Scope

This slice defines and validates the first Milestone 7 operator-facing projection. It reads only these already-generated artifacts:

```text
/var/lib/infra-assurance/evidence/inventory.json
/var/lib/infra-assurance/evidence/context.json
/var/lib/infra-assurance/evidence/change-context.json
```

No new infrastructure query, collector identity, datastore, or source of truth is introduced.

Projection scope:

```text
KUBERNETES_EXISTING_EVIDENCE_ONLY
```

The summary contract exposes four sections:

```text
attention_now
recent_changes
unknowns
required_live_verification
```

## Validation

Focused tests:

```text
5 passed in 0.05s
```

Two earlier live attempts failed closed and are not reusable as negative evidence.

Attempt 1, interactive user `ben`:

```text
source_status: FAILED_TO_OBSERVE
failure_category: PermissionError
discovery_rc=2
```

Attempt 2, `infra-assurance` service identity from the user-private repository path:

```text
python3: can't open file '/home/ben/projects/infrastructure-intelligence-assurance/scripts/discovery/m7_operator_attention_summary_probe.py': [Errno 13] Permission denied
discovery_rc=2
```

The first failure was an artifact-read permission boundary. The second was a repository-path traversal/execution packaging boundary. Neither is zero-attention or source-absence evidence.

Accepted validation used a one-time privileged read-only execution because the source tree and evidence artifacts are protected by different Unix access boundaries. The probe performs only bounded file reads and projections; this does not change the intended runtime identity.

Accepted live result:

```text
discovery_rc=0
source_status: COMPLETE
source_artifacts_loaded: 3
cluster_id: k3s-main
scope: KUBERNETES_EXISTING_EVIDENCE_ONLY
```

Accepted summary:

```text
workloads_total: 68
workloads_with_attention: 3
attention_now_total: 2
recent_changes_total: 0
unknowns_total: 0
required_live_verification_total: 0
```

Accepted attention items:

```text
1. source=topology code=SERVICE_SELECTOR_MULTIPLE_CONTROLLER_MATCHES severity=AMBIGUOUS subject=Service/monitoring/loki-headless
2. source=drift code=DECLARED_OBSERVED_DRIFT severity=DRIFT subject=Ingress/validation/nginx-validation
```

Truncation status:

```text
max_items_per_section: 20
attention_now_truncated: False
recent_changes_truncated: False
unknowns_truncated: False
required_live_verification_truncated: False
```

A repository-wide test suite remains required before merge because this slice adds reusable implementation and tests.

## Accepted interpretation

The operator projection successfully condensed the currently loaded existing evidence into two distinct current attention items while retaining the underlying workload-level summary count.

The `workloads_with_attention=3` count comes from the inventory summary. `attention_now_total=2` is the deduplicated operator-facing attention projection. These counts describe different layers and must not be forced to match.

Within the three successfully loaded artifacts:

```text
recent_changes: NONE_OBSERVED
unknown_or_stale: NONE_OBSERVED
required_live_verification: NONE_OBSERVED
```

These are bounded absence statements only. They do not prove universal absence outside the loaded artifacts or beyond the freshness/trust boundaries of those artifacts.

The two accepted attention items are evidence-routing signals, not remediation instructions:

- the Loki headless Service has an ambiguous selector relationship because multiple controller matches were derived;
- the validation Ingress has a declared-vs-observed drift classification in the loaded evidence.

No automatic action is authorized or implied.

## Safety and trust boundary

The probe reported:

```text
mutation_allowed: False
live_infrastructure_query_performed: False
source_artifacts_written: False
new_datastore_used: False
raw_source_artifacts_projected: False
secrets_or_credentials_projected: False
```

Only allowlisted summary fields and compact attention/change/unknown/verification metadata are projected.

Raw Kubernetes evidence values, arbitrary resource values, raw diagnostics, credentials, Secret values, Terraform state, and sensitive connection strings are not projected.

The one-time privileged validation is not an accepted runtime design. If this contract is integrated into the five-minute evidence loop, it must execute from the installed package/runtime path under the existing `infra-assurance` service identity without broadening permissions.

## Next smallest useful step

After the full repository suite passes and this slice is merged, prefer integrating this accepted contract into the existing five-minute artifact generation path before adding a dashboard or cross-domain inbox.

That integration should generate a derived `operator-attention.json` / `operator-attention.md` artifact from already-generated evidence, remain read-only, run as the existing `infra-assurance` identity, and preserve source failure/unknown semantics.
