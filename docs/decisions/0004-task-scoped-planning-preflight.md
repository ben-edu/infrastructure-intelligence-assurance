# ADR 0004 — Use Task-Scoped Read-Only Planning Preflight Before AI Change Reasoning

## Status

Accepted for Milestone 1 implementation.

## Context

Milestone 1 now provides complete normalized Kubernetes evidence, compact operational context, and evidence-linked topology relationships. The remaining acceptance question is whether an AI can plan a hypothetical application deployment with fewer blind live queries while still identifying what must be verified before any future mutation.

Passing all raw evidence directly to an AI would be unnecessarily large and would make it easier to blur observed state, inferred relationships, stale evidence, and unknown state.

A free-form prompt is also not an adequate trust boundary for change planning.

## Decision

Add a deterministic, task-scoped planning preflight for a hypothetical Kubernetes application deployment.

The preflight consumes:

- `kubernetes.json` as source evidence;
- `context.json` as compact operational context;
- `topology.json` as a derived relationship projection;
- a strict deployment-request document containing only modeled, non-sensitive planning fields.

The first request model supports:

- target cluster and namespace;
- application identity;
- Deployment name, replica count, and image reference;
- optional Service ports;
- optional Ingress host/path;
- optional PVC name, requested size, and optional StorageClass name.

The request model intentionally does not accept environment-variable values, Secret payloads, ConfigMap payloads, credentials, connection strings, or arbitrary Kubernetes manifests.

The preflight output separates:

- evidence-backed facts;
- observed conflicts;
- inferences and operational attention;
- unknown or insufficient evidence;
- required live verification;
- a non-executable candidate plan;
- post-change verification requirements.

`mutation_allowed` is always `false` in Milestone 1.

## Readiness semantics

The first readiness classes are:

- `INSUFFICIENT_EVIDENCE` — required evidence is missing, stale, failed, mismatched, or otherwise cannot support current-state planning;
- `BLOCKED_BY_CURRENT_CONFLICT` — current complete evidence shows a conflicting resource name or exact Ingress route;
- `PLAN_WITH_LIVE_VERIFICATION` — no current blocking conflict is observed, but specific evidence gaps must still be verified before approval.

A failed or stale collection must never be used to claim that a requested resource name is available.

## Selective live verification

The preflight deliberately identifies checks that Milestone 1 cannot currently substantiate, including as applicable:

- image pullability and registry authentication path;
- scheduler feasibility and current capacity pressure;
- ResourceQuota and LimitRange policy;
- NetworkPolicy constraints;
- external DNS ownership/routing;
- StorageClass and provisioning capability;
- relevant topology ambiguity.

This is preferable to either pretending the state is known or issuing broad blind live queries.

## Consequences

- The AI receives a smaller task-oriented evidence pack rather than the full cluster snapshot.
- The platform can distinguish planning from execution.
- Current evidence can rule out some changes early through observed conflicts.
- Missing evidence remains explicit and actionable.
- The same preflight model can later be enriched with history, drift, observability, backup, IaC, and policy evidence without changing its trust principles.

## Deferred

This ADR does not authorize infrastructure mutation, generate kubectl apply commands, create manifests, integrate an external AI provider, or implement approval/execution workflows.
