# Milestone 5 Management PostgreSQL Infrastructure Relationship Discovery — 2026-08-16

## Status

Accepted bounded read-only discovery.

## Scope

Determine whether the running PostgreSQL 15 instance on `mgmt-automation` can be related to an accepted infrastructure asset and existing VM recovery evidence without reading PostgreSQL data or exposing sensitive infrastructure configuration.

## Local host observation

```text
hostname: mgmt-automation
virtualization: kvm
postgresql@15-main.service: active/running
```

The first unprivileged discovery attempt could not read the local DMI UUID and found no exact PVE guest-name match. That attempt correctly retained the relationship as `UNKNOWN`.

## Bounded UUID retry

A root-only retry read the local DMI product UUID and compared it in memory with SMBIOS UUID values from the 12 bounded QEMU guests returned by the existing discovery-only PVE source.

Only GET requests were used.

Safe result:

```text
local_dmi_uuid_available: true
bounded_qemu_candidates: 12
config_probes: 12
config_complete: 12
explicit_smbios_uuid_candidates: 12
uuid_matches: 1
infrastructure_identity_status: OBSERVED
identity_basis: LOCAL_DMI_UUID_EQUALS_PVE_SMBIOS_UUID
candidate_guest: mgmt-automation-01
candidate_vmid: 109
candidate_pve_node: delfan
candidate_type: qemu
candidate_runtime_status: running
runtime_credential_approved: false
```

The UUID values themselves were not printed or persisted.

## Accepted VM recovery evidence correlation

The previously accepted source artifacts were byte-verified before derivation:

```text
/tmp/vm-backup-assurance.json
sha256 match: true

/tmp/proxmox-ve-backup-task-results.json
sha256 match: true
```

VMID `109` is present in accepted VM Backup Assurance v0.2:

```text
vm_last_successful_backup_status: OBSERVED
vm_last_successful_backup_at: 2026-04-13T10:36:41Z
strict_success_task_evidence: true
vm_protection_status: UNKNOWN
vm_restore_verification_status: UNKNOWN
vm_integrity_verification_status: UNKNOWN
vm_rpo_status: UNKNOWN
vm_rto_status: RTO_UNKNOWN
```

Therefore the accepted infrastructure relationship is:

```text
mgmt-automation PostgreSQL host
-> local DMI identity
-> PVE QEMU guest mgmt-automation-01
-> pve-bm2 / delfan / VMID 109
-> accepted STRICT_SUCCESS_TASK_MATCH VM last-successful-backup evidence
```

Result:

```text
local_postgresql_infrastructure_recovery_status: OBSERVED
```

## Trust interpretation

`OBSERVED` here is infrastructure recovery context only.

It does not establish:

```text
PostgreSQL-consistent backup
PostgreSQL backup mechanism
PostgreSQL backup execution/result
PostgreSQL backup artifact location
retention effectiveness
PostgreSQL restore verification
PostgreSQL integrity verification
RPO satisfaction
RTO satisfaction
```

The VM backup timestamp from 2026-04-13 is observed evidence only. It is not classified as `BACKUP_STALE` or `RPO_VIOLATION` because no accepted PostgreSQL freshness/RPO target exists.

## Safety boundary

The discovery did not:

- connect to PostgreSQL;
- read database rows or dump contents;
- read `.pgpass`, connection strings, Secret values, or credential values;
- print or persist DMI/SMBIOS UUID values;
- print or persist raw PVE VM config;
- print disk or network configuration;
- execute a backup or restore;
- mutate PostgreSQL, Kubernetes, PVE, systemd, credentials, or infrastructure.

The PVE credential remains discovery-only and `runtime_credential_approved=false`.

## Conclusion

The remaining management-host PostgreSQL infrastructure identity gap is closed at the infrastructure-recovery layer.

Database-aware PostgreSQL backup assurance remains unknown. The next new Milestone 5 source family is bounded MariaDB backup/recovery discovery.
