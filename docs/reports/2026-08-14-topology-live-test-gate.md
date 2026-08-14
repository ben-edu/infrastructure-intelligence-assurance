# Kubernetes Topology Live Test Gate — 2026-08-14

## Status

Accepted after management-host test and live-cluster verification.

## Test result

The repository-level test suite passed directly from the management-host checkout with:

```bash
python3 -m pytest -q
```

Observed result:

- 31 tests passed;
- no test collection errors;
- no import-path override or editable install was required.

The earlier `ModuleNotFoundError: No module named 'infra_assurance'` was confirmed to be a repository test-runner configuration issue. Adding `pythonpath = ["src"]` to pytest configuration corrected it.

## Live evidence result

The existing observer continued to produce a complete current Kubernetes snapshot:

- raw evidence records: 240;
- compact operational facts: 22;
- unknown observations: 0;
- observation failures: 0.

## Live topology result

The derived topology reported:

- total relationships: 121;
- Ingress -> Service observed references: 26;
- Service -> workload selector-match inferences: 77;
- workload -> PVC observed references: 18;
- topology issues: 1;
- issues requiring verification: 1.

The single unresolved issue was:

- `Service/monitoring/loki-headless` matched two observed workload controllers through its selector;
- classification: `AMBIGUOUS`;
- required verification: EndpointSlice and Pod ownership evidence before attributing traffic to one controller.

This ambiguity is accepted evidence behavior, not a topology failure. The projection correctly avoided converting selector ambiguity into a false ownership claim.

## Trust statement

No credential, kubeconfig content, Kubernetes Secret value, or other sensitive connection material is recorded in this report. Direct references remain distinguishable from selector-based inferences, and unresolved controller attribution remains explicitly ambiguous.

## Acceptance conclusion

PR #4 meets its acceptance gate. The topology projection is suitable for read-only operational reasoning and planning while remaining a derived projection rather than a replacement for source evidence.
