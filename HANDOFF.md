# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, architecture/trust principles, and operating rules.

For context-window-independent continuation, read `docs/PROJECT_CONTINUITY.md`, then this file, then only reports/ADRs relevant to the active slice.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #79: d089fdd241fcf27437f96b36a6f112b38be49608
active branch: agent/m7-operator-attention-runtime-integration
package on accepted main: 0.27.0
Milestone 5 overall: NOT COMPLETE
Milestone 5 read-only source discovery: COMPLETE FOR CURRENT AUTHORITATIVE SOURCES
Milestone 6 overall: NOT COMPLETE
Milestone 6 current read-only governance phase: COMPLETE FOR CURRENT AUTHORITATIVE SOURCES AND SAFE OBSERVATION PATHS
Milestone 7: ACTIVE
infrastructure mutation allowed: false
repository mutation allowed: true
management host: mgmt-automation
```

## Accepted M7 baseline

Accepted report:

```text
docs/reports/2026-08-29-m7-operator-attention-summary-contract.md
```

Accepted validation:

```text
focused tests: 5 passed in 0.05s
full suite: 410 passed in 1.83s
live source status: COMPLETE
cluster: k3s-main
scope: KUBERNETES_EXISTING_EVIDENCE_ONLY
workloads_total: 68
workloads_with_attention: 3
attention_now_total: 2
recent_changes_total: 0
unknowns_total: 0
required_live_verification_total: 0
```

Accepted attention items:

```text
Service/monitoring/loki-headless
  code=SERVICE_SELECTOR_MULTIPLE_CONTROLLER_MATCHES
  severity=AMBIGUOUS

Ingress/validation/nginx-validation
  code=DECLARED_OBSERVED_DRIFT
  severity=DRIFT
```

Rejected/incomplete attempts preserved:

```text
interactive-user probe: FAILED_TO_OBSERVE / PermissionError
service-identity probe from /home/ben source tree: FAILED_TO_OBSERVE before code execution
```

Do not reuse either failed attempt as zero-attention or source-absence evidence.

The one-time root validation used for the accepted contract is not an accepted runtime design.

## Active slice — runtime integration into the existing five-minute collector

Goal:

```text
Generate operator-attention.json and operator-attention.md from the installed package during the existing collector run, under the existing infra-assurance identity.
```

Target artifacts:

```text
/var/lib/infra-assurance/evidence/operator-attention.json
/var/lib/infra-assurance/evidence/operator-attention.md
```

No new timer, service identity, datastore, infrastructure query, or source of truth is introduced.

### Prepared implementation

Modified module:

```text
src/infra_assurance/operator_attention.py
```

Added runtime behavior:

```text
python3 -m infra_assurance.operator_attention
  --inventory <inventory.json>
  --context <context.json>
  --change-context <change-context.json>
  --out <operator-attention.json>
  --summary-out <operator-attention.md>
```

The runtime writer:

```text
- loads only the three accepted derived artifacts;
- reuses the accepted projection contract;
- writes JSON and Markdown atomically using existing io_utils;
- performs no live infrastructure query;
- performs no remediation;
- preserves mutation_allowed=false in the artifact;
- rejects symlink/oversize/non-object source artifacts through the existing loader.
```

Modified service definition:

```text
systemd/infra-assurance-kubernetes.service
```

A new `ExecStartPost` invokes the installed module after the main Kubernetes runtime has produced `inventory.json`, `context.json`, and `change-context.json`.

The existing service boundary remains:

```text
User=infra-assurance
Group=infra-assurance
PYTHONPATH=/opt/infra-assurance/src
NoNewPrivileges=true
ProtectHome=true
ReadWritePaths includes /var/lib/infra-assurance/evidence
```

No root runtime execution is introduced.

Modified tests:

```text
tests/test_operator_attention.py
```

Tests now cover:

```text
accepted projection contract
unallowlisted-field exclusion
cluster mismatch fail-closed behavior
deduplication/truncation
safe JSON loader
runtime JSON/Markdown writer
systemd installed-module integration under infra-assurance
```

Expected focused test count on this branch: 7. Accept only actual runtime output.

## Mutation boundary

Repository changes for this slice are prepared and testable without infrastructure mutation.

Do NOT yet run `scripts/bootstrap-observer.sh`, copy files into `/opt`, modify `/etc/systemd/system`, reload systemd, or start the collector service. Those actions change the management-host runtime and require explicit user authorization before the live integration gate.

The existing collector remains unchanged on `mgmt-automation` until that authorization is given.

## Exact next step

On `mgmt-automation`, run only repository tests:

```bash
cd ~/projects/infrastructure-intelligence-assurance

git fetch origin

git switch --track origin/agent/m7-operator-attention-runtime-integration

python3 -m pytest -q \
  tests/test_operator_attention.py
```

Do not use strict interactive shell mode.

Acceptance for this gate:

```text
- focused tests pass;
- no live collector/systemd/bootstrap action is performed;
- no infrastructure or management-host runtime mutation is performed.
```

After focused tests pass, the next gate is a reviewed live deployment of only the runtime integration. That gate requires explicit authorization because it changes the installed collector code/service definition on `mgmt-automation`.

Prefer a narrow installation/deployment procedure over rerunning broad bootstrap behavior that could re-apply Kubernetes RBAC unnecessarily.

## Preserved M6 boundaries

```text
Terraform apply outcome: UNKNOWN
Terraform full live-resource coverage/state authority: UNKNOWN
Ansible live managed-host coverage: UNKNOWN
Ansible execution outcome/success/idempotence/configuration drift: UNKNOWN
```

Do not reopen weak M6 probes.

## Trust invariants

- infrastructure interaction remains read-only unless separately authorized;
- repository changes do not imply deployment authorization;
- runtime integration must remain under `infra-assurance`, not root;
- derived operator projections do not replace source evidence;
- stale/failed/unknown evidence remains explicit;
- bounded absence is not universal absence;
- no secret, credential, raw Terraform state, or raw Kubernetes Secret value enters the projection;
- no remediation is implied by an attention item;
- generated operational artifacts keep `mutation_allowed=false`.

## Continuity rule

At every accepted slice before merge:

1. create/update the accepted report when reusable evidence changed;
2. update `HANDOFF.md` with accepted SHA context, evidence, preserved unknowns, trust boundary, merge gate, and exact next step;
3. update roadmap/current-state/README only when milestone status, architecture, or user-facing project status materially changes;
4. ensure no temporary/debug/placeholder files remain;
5. run focused tests and a full repository suite when reusable implementation/contracts change materially;
6. inspect PR scope and mergeability and squash-merge when clean;
7. carry the new accepted `main` SHA into the next checkpoint.
