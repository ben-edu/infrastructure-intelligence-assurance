# Milestone 6 — Jenkins API Metadata-Only Probe

Date: 2026-08-29

## Scope

This report records a bounded read-only Jenkins runtime metadata probe used to qualify Jenkins as a possible execution-outcome evidence source for Milestone 6.

The probe is intentionally restricted to a GET-only root Jenkins JSON API request with a narrow tree projection. It does not request console logs, job configuration bodies, build parameters, environment values, raw commands, inventory arguments, host targets, or Vault material.

## Validation

Focused tests after the connection-parser retry fix:

```text
5 passed in 0.06s
```

Successful live retry:

```text
discovery_rc=0
connection_config_status: CONNECTION_CONFIG_READY
env_files_observed: 1
env_files_read_for_approved_keys: 1
credential_material_loaded_locally: True
credential_values_projected: False
endpoint_value_projected: False
jenkins_api_invoked: True
api_observation_status: COMPLETE
```

A repository-wide test suite remains required before merge because this slice adds reusable discovery implementation and tests.

## First live attempt — failed observation

The first attempt returned:

```text
connection_config_status: CONNECTION_CONFIG_UNAVAILABLE
env_files_observed: 1
env_files_read_for_approved_keys: 0
credential_material_loaded_locally: False
jenkins_api_invoked: False
api_observation_status: NOT_ATTEMPTED
jobs_total: 0
discovery_rc=2
```

This is `FAILED_TO_OBSERVE / NOT_ATTEMPTED`, not negative Jenkins evidence. The `jobs_total: 0` from that attempt must not be interpreted as Jenkins having zero jobs.

The retry fix broadened safe Jenkins-scoped connection-key matching while remaining fail-closed: only explicit `JENKINS_` keys with URL/ENDPOINT, USER/USERNAME, or TOKEN/PASSWORD/API_KEY roles are accepted; generic connection variables are rejected; `export KEY=value` is supported; ambiguous role values stop the probe before any API call.

## Accepted Jenkins runtime metadata

Successful retry returned:

```text
jobs_total: 25
jobs_with_last_build_metadata: 11
ansible_name_signal_jobs: 0
ansible_name_signal_jobs_with_last_build_metadata: 0
last_build_result_counts: SUCCESS=11
ansible_name_signal_last_build_result_counts: NONE_OBSERVED
```

Interpretation:

- Jenkins runtime metadata was successfully observed from the bounded read-only source.
- Twenty-five Jenkins jobs were observed in the restricted root metadata projection.
- Eleven jobs exposed last-build metadata and all eleven reported Jenkins result category `SUCCESS`.
- No job name containing the weak in-memory token `ansible` was observed in this bounded root metadata projection.
- Job names and build numbers were not printed or persisted.

The absence of an `ansible` name token is weak bounded metadata absence only. It does not prove Jenkins does not orchestrate Ansible under another job name or through another relationship.

## Ansible outcome boundary

Preserve:

```text
execution_outcome_status: UNKNOWN
execution_success_status: UNKNOWN
idempotence_status: UNKNOWN
configuration_drift_status: UNKNOWN
successful_execution_claims: 0
idempotence_claims: 0
drift_claims: 0
```

Jenkins `SUCCESS` categories are Jenkins last-build metadata only. They must not be promoted to Ansible execution-success, reachability, idempotence, compliance, or drift claims without stronger authoritative relationship evidence.

## Trust boundary

The probe:

```text
mutation_allowed: False
http_method: GET_ONLY
jenkins_console_logs_inspected: False
jenkins_job_config_bodies_inspected: False
jenkins_build_parameters_inspected: False
credential_values_projected: False
endpoint_value_projected: False
ansible_cli_invoked: False
ssh_connections_performed: False
```

Only Jenkins-scoped connection material required for authentication was loaded process-locally. Credential values, endpoint value, key names, job names, and build numbers were not projected.

The only permitted runtime request was the root `/api/json` endpoint with restricted tree:

```text
jobs[name,color,lastBuild[number,result,timestamp,building]]
```

Console logs, `config.xml`, build parameters, environment values, raw commands, inventory arguments, host targets, and Vault material were not requested.

## Next smallest useful step

Do not infer an Ansible outcome from Jenkins runtime metadata alone.

After the repository-wide suite passes and this slice is merged, perform a bounded **Ansible-to-Jenkins relationship source discovery**. The goal is to determine whether any safe authoritative metadata source can relate an accepted Jenkins job/build to Ansible execution without reading console logs, job configuration bodies, build parameters, raw command bodies, credentials, or sensitive host/inventory data.

If no such safe relationship source exists, preserve Ansible execution outcome as `UNKNOWN` and stop widening this path merely to eliminate the unknown.
