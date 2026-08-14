# Kubernetes Topology Live Test Gate — 2026-08-14

## Status

Pending rerun after test-runner path correction.

## Observed issue

The first live topology validation attempt reached the management host successfully and the observer bootstrap completed, but the repository-level pytest command failed during test collection because the project uses a `src/` layout and the pytest configuration did not add `src` to the import path.

Observed failure class:

- `ModuleNotFoundError: No module named 'infra_assurance'`

This was a test-runner configuration failure, not a Kubernetes observation failure and not evidence that the topology runtime failed.

## Correction

The repository pytest configuration now includes `pythonpath = ["src"]`, so `python3 -m pytest -q` is expected to work directly from the repository root without requiring an editable install or an external `PYTHONPATH` override.

## Acceptance requirement

PR #4 remains unmerged until:

1. repository tests pass from the management-host checkout with `python3 -m pytest -q`;
2. the existing observer runtime produces `topology.json` and `topology.md` successfully on the live cluster;
3. the resulting relationship counts and unresolved issues are reviewed without exposing credentials.
