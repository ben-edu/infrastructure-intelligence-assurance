# Kubernetes Planning Preflight Live Test Gate — 2026-08-14

## Status

Pending rerun after request-example test-contract correction.

## Scope

Final Milestone 1 acceptance test for task-scoped AI planning consumption.

The test uses the installed read-only observer evidence and the repository's non-production hypothetical deployment request. It does not mutate Kubernetes resources.

## First management-host result

The first run reached the management host and executed the repository test suite. Result:

- 41 tests passed;
- 1 test failed;
- the failure was `test_example_keys_are_explicitly_allowlisted`;
- the unexpected field was `request_version` from the newly added planning request example.

The failure was a test-contract mismatch, not a Kubernetes observer, topology, credential, or preflight runtime failure. The legacy evidence/context example allowlist had been applied indiscriminately to the new task-request example contract.

Because the interactive command block enabled `set -euo pipefail`, the failed pytest command terminated the command sequence and the SSH terminal session stopped before bootstrap/preflight execution.

## Correction

The contracts are now tested separately:

- evidence/context examples continue to use the existing explicit key allowlist;
- `examples/requests/*.json` are excluded from that legacy allowlist;
- planning request examples are validated against `hypothetical-deployment-request.schema.json`, whose objects use `additionalProperties: false`;
- planning request examples are also passed through `validate_request()` so unsupported fields such as environment or Secret payload fields remain rejected.

The rerun must not enable shell-wide `set -e` in the interactive SSH session.

## Required acceptance evidence

1. `python3 -m pytest -q` passes from the management-host checkout.
2. The bootstrap refreshes the current observer snapshot and installs the durable `iia-k8s-preflight` CLI.
3. The preflight runs as the `infra-assurance` service user.
4. `preflight.json` and `preflight.md` are produced without credential or Secret payload exposure.
5. `mutation_allowed` remains `false`.
6. Readiness, facts, conflicts, inferences, unknowns, and required live verification are reviewed against the live cluster state.
7. The resulting task-scoped artifact is used for an AI planning consumption test rather than passing the complete raw Kubernetes snapshot to the AI.

## Hypothetical request

Installed path:

```text
/etc/infra-assurance/examples/hypothetical-app-deployment.json
```

The request is intentionally non-production and contains no environment-variable values, Secret payloads, credentials, or connection strings.

## Trust statement

A successful preflight does not authorize deployment execution. Milestone 1 remains read-only and the candidate plan is non-executable until later approval and execution controls exist.
