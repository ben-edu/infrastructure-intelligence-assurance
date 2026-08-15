# Milestone 4 — Alertmanager Handling and Alert Attention

## Goal

Add current Alertmanager handling evidence to the existing Prometheus alert picture without replacing Alertmanager and without forcing every alert into a workload-centric model.

## Live source discovered before implementation

```text
Service/monitoring/kube-prom-stack-alertmanager
port: 9093
```

Prometheus reports one active Alertmanager endpoint at port 9093. Runtime Pod IPs are not used as durable configuration.

## Read-only API scope

```text
GET /api/v2/alerts
GET /api/v2/silences
```

The collector reads only through the exact Kubernetes Service proxy identity `kube-prom-stack-alertmanager:9093`.

## Outputs

```text
/var/lib/infra-assurance/evidence/alertmanager-runtime.json
/var/lib/infra-assurance/evidence/alertmanager-runtime.md
/var/lib/infra-assurance/evidence/alert-attention.json
/var/lib/infra-assurance/evidence/alert-attention.md
```

## Trust rules

- Alertmanager is authoritative for alert processing, silencing, and inhibition.
- Prometheus remains authoritative for alert evaluation state.
- Correlation is `MATCHED` only for one unique common allowlisted-label match.
- `UNRESOLVED` and `AMBIGUOUS` correlation never choose a candidate by heuristic.
- Workload scope is used only when an existing evidence-backed Prometheus-to-workload path is unique.
- Node/Service/Namespace scopes from labels remain label scope, not ownership/root-cause proof.
- Alertmanager receiver names/configuration, annotations, generator URLs, arbitrary labels, notification payloads, credentials, and Secret values are excluded.
- `mutation_allowed=false`.

## Acceptance intent

The live gate should answer:

1. Can the observer read only the intended Alertmanager Service proxy?
2. Are Alertmanager alert/silence reads current and explicit about failure?
3. Do current Prometheus alerts correlate uniquely where evidence supports it?
4. Are current silence/inhibition states visible without receiver/configuration exposure?
5. Do node/service/platform alerts remain visible even without workload attribution?
6. Are sensitive/free-form fields absent from persisted evidence?
7. Does existing Prometheus runtime evidence remain unchanged and independently trustworthy?

Real active, silenced, inhibited, unprocessed, unresolved, or ambiguous alerts are evidence and are not gate failures by themselves.
