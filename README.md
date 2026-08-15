# Infrastructure Intelligence & Assurance Platform

Evidence-first infrastructure context and assurance platform.

## Current status

Milestone 0 — Evidence Contract is complete.

Milestone 1 — Kubernetes evidence, topology, and read-only planning preflight is complete and live-validated.

Milestone 2 — bounded history, trust-aware diff, dedicated Git declared-state observation, and declared-vs-observed drift are complete and live-validated.

Milestone 3 — workload-centric operational inventory plus Prometheus Operator configuration coverage is complete and live-validated.

Milestone 4 now starts with authoritative Prometheus runtime target-health and active-alert evidence attached to the existing workload inventory without replacing Prometheus or Alertmanager.

The live loop runs on the management host every five minutes.

## Runtime model

```text
Private infrastructure Git
  -> dedicated read-only deploy key
  -> normalized declared evidence + Git revision
                                  \
Kubernetes API                     \
  -> dedicated read-only identity   \
  -> normalized observed evidence    -> declared-vs-observed drift
  -> freshness / trust              -> compact change context
  -> topology / history / diff      -> workload operational inventory
  -> Prometheus Operator config     -> configuration coverage
  -> Prometheus HTTP API            -> runtime target / alert evidence
                                      -> workload inventory enrichment
                                      -> planning / AI consumption
```

Current-state and task artifacts remain separate from immutable history.

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
/var/lib/infra-assurance/evidence/preflight.json
/var/lib/infra-assurance/evidence/preflight.md
```

Bounded Kubernetes history:

```text
/var/lib/infra-assurance/history/kubernetes/index.json
/var/lib/infra-assurance/history/kubernetes/snapshots/*.json
```

Normalized Git declared state:

```text
/var/lib/infra-assurance/declared/current/records.json
/var/lib/infra-assurance/declared/source-status.json
/var/lib/infra-assurance/git/repos/*.git
```

The default Kubernetes history retention is 288 snapshots, approximately 24 hours at the current five-minute cadence. This remains replaceable local storage, not a final long-term database decision.

## Workload operational inventory

The Dynamic Operational Inventory / CMDB projection covers currently observed:

```text
Deployment
StatefulSet
DaemonSet
```

Each workload entity combines traceable pointers and compact state from existing evidence sources:

- current observed state and freshness;
- safe replica/scheduling fields and image references;
- direct Git declared coverage and workload comparison where available;
- Service selector-match relationships;
- composed Ingress route candidates;
- direct PVC references;
- latest related snapshot changes;
- related topology ambiguity and drift attention;
- Prometheus Operator configuration coverage;
- current Prometheus runtime target and active-alert signals where attributable.

This inventory is derived state. Kubernetes, Git, Prometheus, history, drift, and topology artifacts remain the supporting source evidence.

A Service-to-workload relationship remains a selector-based inference. An Ingress route candidate composes an observed Ingress-to-Service reference with that inference and does not prove current Pod or EndpointSlice routing.

A workload missing from the configured Git scope is `OUTSIDE_DECLARED_SCOPE`, not automatically unmanaged or drifted. A namespace is not automatically treated as an application or ownership boundary.

## Prometheus Operator configuration coverage

Milestone 3 observes these Prometheus Operator resources read-only:

```text
Prometheus
ServiceMonitor
PodMonitor
```

For each workload, configuration coverage is classified as:

```text
OPERATOR_MONITOR_MATCH
NO_OPERATOR_MONITOR_MATCH
UNKNOWN
```

`OPERATOR_MONITOR_MATCH` is evidence of a selected Prometheus Operator configuration path. It is not runtime scrape-health evidence.

`NO_OPERATOR_MONITOR_MATCH` means only that no selected ServiceMonitor/PodMonitor path was derived inside the modeled scope. It does not prove the workload has no other monitoring path.

## Prometheus runtime intelligence

Milestone 4 begins with direct read-only Prometheus HTTP API evidence reached through the Kubernetes API Service proxy for:

```text
monitoring/kube-prom-stack-prometheus:9090
```

The runtime observer reads:

```text
/api/v1/targets?state=active
/api/v1/alerts
```

It stores only a narrow target and alert projection. Raw scrape URLs, discovered labels, arbitrary labels, alert annotations, metric series, credentials, and Secret values are not persisted.

Workload runtime signal states are:

```text
PROMETHEUS_TARGETS_UP
PROMETHEUS_TARGET_DOWN
ACTIVE_ALERT
NO_RUNTIME_SIGNAL_MATCH
UNKNOWN
```

These are signal states, not generic application-health conclusions.

`PROMETHEUS_TARGETS_UP` means matched Prometheus scrape targets reported `up` at observation time. It does not prove application correctness or end-user availability.

`NO_RUNTIME_SIGNAL_MATCH` means no target or active alert could be attributed through this modeled path. It does not prove absence of monitoring or alerts elsewhere.

Target and alert attribution through a Kubernetes Service retains:

```text
SERVICE_SELECTOR_MATCH_INFERENCE
```

The platform therefore does not claim direct live Pod ownership from Service-based attribution.

The additional Kubernetes permission is a namespaced `get` on `services/proxy` in `monitoring`; proxy access is not granted in other namespaces by this Role. Secret access and mutation remain denied.

## Git declared-state source

The first configured source is:

```text
github.com/ben-edu/api-cluster-infra
branch: main
cluster: k3s-main
```

The source mapping is explicit rather than a recursive YAML scan. BookStack and validation use configured direct manifest paths. FastAPI dev/prod use configured Kustomize targets rendered locally at the exact fetched revision. Helm values and example directories are outside the current declared-state contract.

Authentication uses a dedicated read-only SSH deploy key generated on the management host. The runtime does not reuse a personal SSH key or administrator GitHub credential.

Only these Kubernetes kinds can currently become declared evidence:

```text
Namespace
Deployment
StatefulSet
DaemonSet
Service
Ingress
PersistentVolumeClaim
```

`Secret`, `ConfigMap`, and unsupported kinds are not serialized into declared evidence. Raw environment values, Secret payloads, arbitrary ConfigMap payloads, credentials, and connection strings are not emitted.

A failed Git refresh does not make the previous declared bundle current. Drift becomes unknown until the source is observed successfully again.

## Trust rules

A failed or stale current Kubernetes collection is never used to claim that a resource disappeared.

Git-declared and live-observed state remain separate evidence planes. A Git source failure, stale declaration, or cluster mismatch cannot become drift by inference.

Observed resources outside the configured declared scope are not automatically classified as drift.

Prometheus Operator configuration coverage is not promoted to scrape-health evidence.

A failed Prometheus runtime query becomes `PARTIAL` or `FAILED_TO_OBSERVE` and never becomes a false zero-target or zero-alert fact.

Raw Kubernetes Secret values are never collected. The Kubernetes observer has no Secret access and no mutating verbs.

`mutation_allowed` remains `false`.

## Install or refresh on the management host

```bash
sudo CLUSTER_ID=k3s-main ./scripts/bootstrap-observer.sh
```

The five-minute collector refreshes Git declared evidence, Kubernetes evidence, Prometheus Operator configuration coverage, Prometheus runtime evidence, and the derived inventory projections.

## Query workload inventory

```bash
sudo -u infra-assurance iia-inventory summary
sudo -u infra-assurance iia-inventory list
sudo -u infra-assurance iia-inventory list --attention-only
sudo -u infra-assurance iia-inventory list --observability-status OPERATOR_MONITOR_MATCH
sudo -u infra-assurance iia-inventory list --runtime-state PROMETHEUS_TARGET_DOWN
sudo -u infra-assurance iia-inventory list --runtime-state ACTIVE_ALERT
sudo -u infra-assurance iia-inventory list --runtime-state PROMETHEUS_TARGETS_UP
sudo -u infra-assurance iia-inventory show \
  --namespace validation \
  --kind Deployment \
  --name nginx-validation
```

The inventory CLI reads the generated artifact only and performs no additional infrastructure query.

## Inspect Git source status

```bash
sudo -u infra-assurance iia-git-source status
sudo -u infra-assurance iia-git-source public-key
```

## Inspect history

```bash
sudo -u infra-assurance iia-k8s-history status
sudo -u infra-assurance iia-k8s-history list --limit 10
```

## Run the read-only planning preflight

```bash
sudo -u infra-assurance iia-k8s-preflight \
  --request /etc/infra-assurance/examples/hypothetical-app-deployment.json
```

## Validate locally

```bash
python3 -m pytest -q
```

See:

- `docs/decisions/0008-workload-centric-operational-inventory.md` for the workload inventory boundary;
- `docs/decisions/0009-prometheus-operator-coverage-is-not-scrape-health.md` for configuration coverage semantics;
- `docs/decisions/0010-prometheus-runtime-evidence-via-read-only-service-proxy.md` for runtime Prometheus access and trust boundaries;
- `docs/milestone-3-workload-operational-inventory.md` for the workload inventory slice;
- `docs/milestone-3-prometheus-operator-coverage.md` for configuration coverage;
- `docs/milestone-4-prometheus-runtime-intelligence.md` for the first runtime observability slice.
