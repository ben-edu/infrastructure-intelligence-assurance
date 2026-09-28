# Operator and AI-Assisted Deployment Guide

## Purpose

This is the practical starting point for using the accepted
Infrastructure Intelligence & Assurance runtime when designing or deploying a
new application, website, or service on Behnam's infrastructure.

It combines three different sources without sending an AI a large undirected
dump:

1. **current operational evidence** from `infrastructure-intelligence-assurance`;
2. **reusable platform contracts** from `ben-edu/infra-docs`;
3. **the new project's own brief and relevant source files**.

The result is a compact context pack that helps an AI write code and deployment
configuration that fit the real infrastructure. It is still a planning and
implementation aid, not approval to deploy.

## Mental model

```text
infrastructure-intelligence-assurance
  -> what is observed now, what changed, what is unknown, what needs checking

infra-docs
  -> how this infrastructure expects Hestia/K3s/Jenkins/Harbor/Keycloak work

project repository
  -> what this specific application must do and the code being changed

AI assistant
  -> bounded architecture/code/deployment proposal using those three inputs

human + Jenkins/live operator
  -> review, staging execution, verification, and production approval
```

The assurance runtime does not contain an LLM and does not deploy applications.
It prepares trustworthy evidence for a human or external AI assistant.

## Platform boundary

The current installed runtime directly observes and summarizes the K3s-side
evidence boundary. It does not provide a Hestia-specific deployment preflight.

| Target | Current assistance |
| --- | --- |
| K3s application/API | Current evidence, inventory, drift/change context, operator attention, and task-scoped deployment preflight |
| Hestia static/PHP frontend | Shared platform attention only; use `infra-docs` plus fresh Hestia/DNS/HAProxy/TLS verification |
| Hybrid Hestia + K3s application | Run the K3s preflight for the API and use the Hestia checklist for the frontend |
| Keycloak | Load the Keycloak contract from `infra-docs`; current assurance evidence does not inspect realms, clients, roles, users, or login events |
| Other VMs | Use only evidence explicitly produced for that VM/backup source; do not treat the Kubernetes context as general VM coverage |

## The files an operator should know

Prefer the Markdown summaries for human/AI use. Use JSON only when a tool needs
an exact field or the summary identifies a specific drill-down.

| File | Use it when | Meaning |
| --- | --- | --- |
| `/var/lib/infra-assurance/evidence/operator-attention.md` | First file to read | Prioritized current attention, unknown/stale state, backup gaps, incidents, and required verification |
| `/var/lib/infra-assurance/evidence/preflight.md` | Before a K3s deployment | Task-scoped facts, conflicts, inferences, unknowns, required live checks, candidate plan, and safest next action |
| `/var/lib/infra-assurance/evidence/context.md` | More cluster context is needed | Compact current Kubernetes context with freshness/trust boundaries |
| `/var/lib/infra-assurance/evidence/inventory.md` | The AI needs workload/service/ingress/PVC relationships | Dynamic operational inventory for supported workload kinds |
| `/var/lib/infra-assurance/evidence/change-context.md` | Recent changes matter | Bounded recent-change context; zero does not mean no change exists universally |
| `/var/lib/infra-assurance/evidence/drift.md` | Git/live alignment matters | Valid declared-versus-observed differences only |
| `/var/lib/infra-assurance/evidence/incident-candidates.md` | Operator attention references an incident candidate | Grouped signals, not confirmed incidents or root causes |
| `/var/lib/infra-assurance/evidence/backup-assurance.md` | The change touches stateful data | Evidence-backed protection gaps and explicit unknowns, not proof of recovery |

Important semantics:

```text
DECLARED != OBSERVED
UNKNOWN != false
FAILED_TO_OBSERVE != negative evidence
incident candidate != confirmed incident or root cause
SUPPRESSED != RESOLVED
backup UNKNOWN != UNPROTECTED
recommendation != approval
```

## Three-minute operational check

Run this on `mgmt-automation` before asking an AI to plan infrastructure-aware
work:

```bash
systemctl is-enabled infra-assurance-kubernetes.timer
systemctl is-active infra-assurance-kubernetes.timer
systemctl show infra-assurance-kubernetes.service \
  --property=Result \
  --property=ExecMainStatus \
  --property=ExecMainStartTimestamp \
  --no-pager

sudo -u infra-assurance sed -n '1,260p' \
  /var/lib/infra-assurance/evidence/operator-attention.md
```

Expected interpretation:

- the **timer** should be enabled and active;
- the oneshot **service** may normally be inactive between runs;
- `Result=success` and a recent generated timestamp are positive evidence only
  for the completed collection;
- stale, partial, failed, or unknown evidence must remain explicit.

If collection failed or evidence needed for the task is stale, stop and verify
the source. Do not let an AI treat old output as current state.

## Step 1 — Create the project brief

Copy and fill `TEMPLATE_PROJECT.md` from `ben-edu/infra-docs`. Keep it in the
new project's repository as `PROJECT.md` or an equivalent durable control file.

At minimum decide:

- project purpose and phase-one scope;
- one stable slug;
- Hestia, K3s, or hybrid placement;
- production and staging domains;
- frontend/API/database/admin/email needs;
- GitHub repository and branch model;
- human production-approval authority.

Reference credential names only. Never put secret values in the brief, Git, an
AI prompt, or the assurance evidence.

## Step 2 — Select only the required `infra-docs`

Canonical repository: `ben-edu/infra-docs`.

Always provide these four small platform contracts:

```text
00_START_HERE.md
01_INFRA_BASELINE.md
02_DELIVERY_PLAYBOOK.md
06_GIT_WORKFLOW.md
```

Add a conditional document only when its layer is in scope:

| Project need | Add |
| --- | --- |
| API, database, Kubernetes objects, migrations, or seeding | `03_APP_BLUEPRINT.md` |
| Keycloak, JWT, roles, or admin SPA | `04_AUTH_AND_ADMIN.md` |
| Jenkins mutation, smoke-test data, SMTP, or email | `05_CI_AND_EMAIL.md` |

Do not attach all dated audits by default. Load one audit only when the current
task depends on that exact historical evidence or risk.

## Step 3A — Build the K3s preflight

From the current `infrastructure-intelligence-assurance` checkout on
`mgmt-automation`:

```bash
DEPLOYMENT_SLUG="replace-with-project-slug"
cp examples/requests/hypothetical-app-deployment.json \
  "/tmp/${DEPLOYMENT_SLUG}-deployment-request.json"
```

Edit only non-secret task facts in the copy:

- `cluster_id`;
- namespace;
- application/deployment/service/ingress names;
- image reference;
- replica count and ports;
- public host/path;
- PVC name, size, and declared storage class when applicable.

Then run the read-only preflight:

```bash
chmod 0644 "/tmp/${DEPLOYMENT_SLUG}-deployment-request.json"

sudo -u infra-assurance iia-k8s-preflight \
  --request "/tmp/${DEPLOYMENT_SLUG}-deployment-request.json"

sudo -u infra-assurance sed -n '1,320p' \
  /var/lib/infra-assurance/evidence/preflight.md
```

The request must contain no secrets. The explicit mode makes the temporary
file readable by the dedicated runtime identity even when the operator uses a
restrictive shell umask. Remove that single request file after the context pack
has been assembled.

The preflight output is accepted as planning input only when:

- the cluster/task scope matches;
- required input evidence is current enough for the decision;
- collection failures are not interpreted as absence;
- conflicts are resolved or carried explicitly into the plan;
- every `required_live_verification` is assigned before mutation;
- `mutation_allowed=false` remains understood as expected behavior.

The preflight does not prove that a deployment will succeed and does not grant
permission to execute it.

## Step 3B — Build the Hestia live-verification summary

There is currently no Hestia-specific assurance preflight. For a Hestia
frontend or PHP site, give the AI a short operator-verified summary covering:

```text
verification time
target Hestia host/account
production and staging domains
domain/docroot existence
docroot owner (expected: benweb for the documented shared contract)
staging docroot writable by the Jenkins SSH identity
DNS status
HAProxy route status
TLS status
current deployed commit/version when observable
presence of protected .env and .well-known paths
unknown or failed checks
```

Use `01_INFRA_BASELINE.md` and `02_DELIVERY_PLAYBOOK.md` as the contract. Do not
ask the AI to guess missing Hestia, DNS, HAProxy, TLS, credential, or ownership
facts.

For a hybrid site, include both the Hestia verification summary and the K3s
preflight.

## Step 4 — Assemble the compact AI context pack

Use this order:

```text
1. PROJECT.md                         project intent and decisions
2. operator-attention.md              current cross-domain attention
3. preflight.md                       K3s task evidence, if applicable
4. HESTIA_LIVE_VERIFICATION.md        fresh Hestia checks, if applicable
5. four canonical infra-docs files    platform contract
6. conditional infra-docs             only required layers
7. exact relevant project files       code/config being changed
```

Do not include by default:

- raw evidence JSON;
- the complete assurance repository;
- all `infra-docs` audits;
- unrelated application source files;
- full logs or test histories;
- kubeconfig, `collector.env`, private keys, tokens, passwords, raw Kubernetes
  Secret values, Terraform state, real tfvars, `.env`, database dumps, or raw
  backup content.

If the AI needs more detail, add one specific artifact or source excerpt rather
than another repository-wide dump.

## Copy-paste prompt for the AI session

```text
You are helping design and implement <PROJECT> for Behnam's existing
infrastructure.

Deployment target: <K3s | Hestia | hybrid>.
Current task: <one bounded outcome>.

Use the attached inputs in this authority order:
1. PROJECT.md for project-specific intent and approved decisions.
2. Current operator-attention/preflight/live-verification files for observed
   runtime evidence and explicit unknowns.
3. Selected files from ben-edu/infra-docs for reusable platform contracts.
4. The project repository for current code and versioned configuration.

Rules:
- Distinguish DECLARED, OBSERVED, INFERENCE, UNKNOWN, STALE, PARTIAL, and
  FAILED_TO_OBSERVE.
- Do not invent infrastructure facts, credentials, domains, routes, capacity,
  backup protection, or successful execution.
- Never expose or request secret values in code, Git, or the response.
- Treat `mutation_allowed=false` as a hard planning boundary. When an input
  contains `safest_next_action`, treat it as recommended verification, not
  execution approval.
- Follow the infra-docs Git/Jenkins/staging/production contract.
- Use Hestia for the documented static/PHP layer and K3s for the documented
  containerized application/API layer unless the approved project brief says
  otherwise.
- Stop and list required live verification when evidence is missing or stale.
- Do not deploy to production without explicit human approval and exact green
  staging/commit evidence.

First return:
1. understood scope and deployment shape;
2. facts, conflicts, assumptions, unknowns, and required live checks;
3. proposed repository structure and files to change;
4. implementation and test plan;
5. staging deployment and verification plan;
6. production approval gate and rollback approach.

Do not execute a deployment in this first response.
```

After reviewing that plan, ask the AI to implement only the accepted bounded
slice in the project repository.

## Stop conditions before deployment

Stop instead of guessing when any of these applies:

- required current evidence is stale, partial, or failed;
- cluster/project scope does not match;
- a namespace, resource name, ingress host/path, domain, or shared database
  ownership conflict is unresolved;
- Hestia docroot ownership/writability is not verified;
- DNS, HAProxy, TLS, Keycloak redirect origins, or browser-to-API routing is
  unverified;
- a stateful change lacks authoritative backup and rollback evidence;
- Jenkins credentials/capabilities are assumed rather than verified;
- staging is not green on the exact commit;
- production approval has not been given.

## Post-deployment verification

Use the project-specific smoke tests and Jenkins exact-commit result as the
primary deployment evidence. After the next assurance collection cycle, inspect:

```bash
sudo -u infra-assurance sed -n '1,260p' \
  /var/lib/infra-assurance/evidence/change-context.md

sudo -u infra-assurance sed -n '1,260p' \
  /var/lib/infra-assurance/evidence/drift.md

sudo -u infra-assurance sed -n '1,260p' \
  /var/lib/infra-assurance/evidence/inventory.md

sudo -u infra-assurance sed -n '1,260p' \
  /var/lib/infra-assurance/evidence/operator-attention.md
```

Confirm expected workload/routing evidence and investigate new drift, failure,
staleness, incident candidates, or attention items. Absence from a bounded or
failed source is not proof that the deployment failed or that a resource does
not exist.

Record the deployed commit, staging/production result, live checks, unresolved
unknowns, and rollback reference in the project's own operations/handoff file.

## Quick decision card

```text
Normal daily look:
  operator-attention.md

Before K3s work:
  PROJECT.md + operator-attention.md + preflight.md
  + four canonical infra-docs + required conditional docs

Before Hestia work:
  PROJECT.md + operator-attention.md + Hestia live-verification summary
  + four canonical infra-docs + required conditional docs

Before hybrid work:
  combine both paths

For AI code generation:
  add only the exact relevant project files

For production:
  exact green staging commit + explicit human approval
```
