# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, trust principles, and operating rules.

## Resume protocol

1. Read Project Sources.
2. Read `HANDOFF.md` from `main`.
3. Check open PRs in `ben-edu/infrastructure-intelligence-assurance`.
4. If an active project PR has a newer `HANDOFF.md`, prefer that branch version for execution state.
5. Read only the ADR, milestone doc, and report relevant to the active slice.
6. Prefer repository and live evidence over chat reconstruction.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #61: 945a16af33c2f6a708dd53181a9a00a5971b58be
active branch: agent/m6-terraform-declared-inventory
package on accepted main: 0.27.0
Milestone 5 overall: ACTIVE — NOT COMPLETE
Milestone 5 read-only source discovery: COMPLETE FOR CURRENT AUTHORITATIVE SOURCES
Milestone 6: ACTIVE
mutation_allowed: false
management host: mgmt-automation
```

## Milestone 5 boundary

Accepted closure report:

```text
docs/reports/2026-08-23-m5-read-only-discovery-closure.md
```

Do not create additional Milestone 5 probes merely to force preserved unknowns closed. Controlled restore/integrity work remains deferred until explicitly authorized.

## Active Milestone 6 slice — Terraform declared-state inventory

Goal: create the smallest safe structural inventory of Terraform configuration in the known infrastructure repository without reading Terraform state or invoking Terraform.

Bounded source:

```text
/home/ben/projects/afpa-infra-rebuild
Git-tracked .tf files only
```

Implementation:

```text
scripts/discovery/m6_terraform_declared_inventory.py
tests/test_terraform_declared_inventory.py
```

Safe projections:

```text
Terraform directory/root candidates (heuristic)
module-directory candidates (heuristic)
backend types only
provider types only
resource types and counts only
data-source types and counts only
module/variable/output block counts
cloud/workspaces block counts
```

Never project or print:

```text
resource instance names
variable names/defaults
output names/values
provider configuration values
backend configuration values
module source values
raw HCL lines
```

Explicitly excluded:

```text
terraform.tfstate and state backups
real tfvars
.env
secret/credential/private-key/certificate material
provider credentials/tokens/passwords
raw sensitive connection strings
```

The Terraform CLI must not be invoked. No init, plan, show, state, import, apply, destroy, refresh, or provider live call is allowed in this slice.

## Semantics

Configuration-derived Terraform resources are DECLARED state only.

```text
managed_resource_coverage_status: DECLARED_CONFIGURATION_ONLY
live_resource_coverage_status: UNKNOWN
```

`ROOT_CANDIDATE` and `MODULE_DIRECTORY` are structural heuristics, not authoritative workspace/stack identities.

Backend type is declaration metadata only. It does not establish backend reachability, workspace contents, state existence, or state freshness.

No drift or destructive-change claim may be made in this slice.

## Exact next step

On `mgmt-automation`:

1. run the focused safety/unit tests;
2. run the declared-state discovery;
3. accept only structural declarations and counts;
4. keep live/state-backed coverage `UNKNOWN`.

Commands:

```bash
python3 -m pytest -q tests/test_terraform_declared_inventory.py

PYTHONPATH=src python3 scripts/discovery/m6_terraform_declared_inventory.py
```

## Trust invariants

- infrastructure interaction remains read-only;
- declared state is not observed state;
- source artifacts and derived assurance remain separate;
- Terraform state and real tfvars do not enter evidence/AI context;
- provider/backend/module values are not projected;
- no drift or destructive-change result is inferred without appropriate evidence;
- unknowns are not forced closed without authoritative evidence;
- no secrets, credentials, private keys, raw sensitive configuration, or sensitive connection strings enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.
