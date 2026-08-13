# Infrastructure Intelligence & Assurance Platform

This repository starts with **Milestone 0 — Evidence Contract**.

The milestone defines the smallest evidence and AI-context contract needed to support a later Kubernetes-only vertical slice. It does **not** collect from live infrastructure and does not choose a final CMDB, database, queue, UI, observability pipeline, or deployment architecture.

## Milestone 0 scope

- normalized observation envelope;
- provenance metadata;
- freshness and expiration semantics;
- explicit absence, unknown, stale, failed-observation, and partial-observation semantics;
- separation of declared Git state and observed live state;
- security exclusions;
- minimal task-oriented AI context;
- executable schema and semantic tests.

## Safety boundary

Milestone 0 is offline and read-only. No live infrastructure access is required.

Evidence, examples, tests, prompts, and AI context must exclude credential material, private cryptographic material, Kubernetes Secret payload values, sensitive Terraform state payloads, and complete sensitive connection strings.

## Validate the contract

```bash
python -m pip install -e '.[test]'
pytest
```

## Repository status

The contract is intentionally narrow. Collectors and runtime integrations are deferred until the evidence model has been validated.
