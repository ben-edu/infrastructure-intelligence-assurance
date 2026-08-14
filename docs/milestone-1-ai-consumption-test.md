# Milestone 1 — AI Consumption Test

## Goal

Answer the Milestone 1 acceptance question:

> Can an AI safely plan a hypothetical application deployment with fewer blind live queries while correctly identifying what still requires live verification?

## Test shape

The platform does not ask the AI to inspect all Kubernetes objects directly.

Instead, the flow is:

```text
Kubernetes API
  -> normalized evidence
  -> compact operational context
  -> topology projection
  -> task-scoped deployment preflight
  -> AI planning consumption
```

The preflight is deterministic and read-only. It evaluates a hypothetical deployment request against the latest evidence before any AI reasoning occurs.

## Hypothetical request

The repository includes:

```text
examples/requests/hypothetical-app-deployment.json
```

It intentionally uses non-production example identities and does not contain credentials or secret-bearing configuration.

## Runtime command

After refreshing/installing the branch on the management host:

```bash
sudo -u infra-assurance iia-k8s-preflight \
  --request /home/ben/projects/infrastructure-intelligence-assurance/examples/requests/hypothetical-app-deployment.json
```

Default output paths:

```text
/var/lib/infra-assurance/evidence/preflight.json
/var/lib/infra-assurance/evidence/preflight.md
```

## Acceptance criteria

The live test is accepted only if:

1. repository tests pass;
2. the observer snapshot has no unresolved collection failure for evidence required by the preflight;
3. the preflight does not claim resource availability from stale or failed collections;
4. current resource-name and exact Ingress-route conflicts are surfaced explicitly;
5. inferred or topology-ambiguous state remains distinguishable from facts;
6. uncollected concerns become selective `required_live_verification` checks;
7. `mutation_allowed` remains `false`;
8. the resulting artifact is compact enough for AI consumption without passing the entire raw snapshot.

## Expected learning

A successful test does not prove that the platform can safely execute a deployment. It proves that the evidence loop can support bounded planning and can identify the remaining live checks before an approval or execution system is introduced.

Milestone 2 can then add history, diffs, and declared-vs-observed drift to this same planning boundary.
