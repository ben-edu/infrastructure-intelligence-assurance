# ADR 0001 — Separate Evidence Dimensions

## Status

Accepted for Milestone 0.

## Problem

Terms such as ABSENT, UNKNOWN, STALE, FAILED_TO_OBSERVE, and PARTIAL describe different properties of evidence. A single combined status enum would make important states ambiguous and could allow a failed observation to be mistaken for resource absence.

## Options

1. Use one large status enum containing all states.
2. Separate existence, observation quality, and freshness.

## Decision

Use three dimensions:

```text
existence:
  PRESENT | ABSENT | UNKNOWN

observation_status:
  COMPLETE | PARTIAL | FAILED_TO_OBSERVE

freshness:
  CURRENT | STALE
```

Freshness is derived from timestamps and is not stored in the observation envelope.

## Rationale

The model can represent operationally important combinations without conflation, including:

```text
PRESENT + COMPLETE + STALE
UNKNOWN + FAILED_TO_OBSERVE
PRESENT + PARTIAL + CURRENT
```

`ABSENT` is allowed only when the observation is complete.

## Rejected alternative

A single enum was rejected because it cannot cleanly express multiple simultaneous properties and encourages unsafe interpretation of observation failure.

## Consequences

Consumers must evaluate more than one field, but the meaning is explicit and testable.

## Revisit when

Revisit if the first Kubernetes vertical slice produces evidence that cannot be represented safely using these dimensions.
