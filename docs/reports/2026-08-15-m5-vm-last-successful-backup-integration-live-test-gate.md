# Milestone 5 VM Last Successful Backup Integration Live Test Gate — 2026-08-15

## Status

Accepted after focused retry on 2026-08-16.

## Scope

Validate package `0.23.0` and `vm_backup_assurance_version=0.2` using accepted local artifacts only:

```text
/tmp/vm-backup-assurance.json
/tmp/proxmox-ve-backup-task-results.json
```

No Proxmox collector was rerun.

## Accepted repository gate

```text
package: 0.23.0
262 passed in 1.32s
RBAC changes: none
systemd changes: none
query/control/credential markers: none
```

## Accepted source contract

The authoritative PR #38 task-result identifier shape is:

```text
^pve-backup-task:[a-f0-9]{24}$
```

The first derived gate on 2026-08-16 was rejected because the new integration schema incorrectly expected a different ID shape. The generated evidence preserved the correct source ID; the defect was limited to the integration schema/test fixture.

The branch was corrected so source schema, integration schema, regression tests, and fixtures all use the accepted identifier contract.

Focused retry result:

```text
source pattern == integration pattern: true
task ID contract alignment: PASS
```

## Input immutability

Before and after derivation:

```text
VM source SHA256:
14ccd7a082a6c901df6941e4c0540d24bd13ff96f29146a0e6ad689d4f824c1a

PVE task source SHA256:
18aaa4ad1a2dd260b4d0678e830f3c9267b2afaa1014b3563ec0e78a2b0135de
```

Both source artifacts remained byte-identical.

## Output acceptance

```text
output schema: PASS
vm_backup_assurance_version: 0.2
mutation_allowed: false
mode: STRICT_CORRELATION_ONLY
source_status: COMPLETE
source_freshness: UNKNOWN
historical_completeness: NOT_ESTABLISHED
```

Observed VMIDs:

```text
100
101
106
107
108
109
```

Unknown VMIDs:

```text
102
103
104
105
110
9000
```

Current latest successful task completion times:

```text
100 -> 2026-05-08T06:15:18Z
101 -> 2026-05-08T10:38:50Z
106 -> 2026-08-14T16:39:53Z
107 -> 2026-08-14T17:39:32Z
108 -> 2026-04-15T12:36:38Z
109 -> 2026-04-13T10:36:41Z
```

Summary:

```text
assets_total: 12
last_successful_backup_observed: 6
last_successful_backup_unknown: 6
strict_success_correlations_consumed: 9
unmatched_recovery_points_in_returned_task_history: 3
unprotected_claims: 0
kubernetes_pvc_assets_modified: 0
```

## Trust boundary

Only accepted `STRICT_SUCCESS_TASK_MATCH` correlations establish `LAST_SUCCESSFUL_BACKUP=OBSERVED`.

The integration does not strengthen:

```text
protection_status
integrity_verification_status
restore_verification_status
failure_domain_status
scheduled_protection_status
rpo_status
rto_status
```

Historical task completeness remains unestablished. The three older unmatched recovery points remain history limitations, not failed-backup evidence.

## Safety acceptance

```text
sensitive/raw projection: none
raw URLs: none
credential access: none
network query: none
runtime wiring: none
infrastructure mutation: none
```

## Acceptance result

```text
PR #41 FOCUSED RETRY: PASS
```
