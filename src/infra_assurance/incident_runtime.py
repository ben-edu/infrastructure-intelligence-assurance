from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .incident_candidates import build_incident_candidates, render_incident_candidates_markdown
from .io_utils import atomic_write_json, atomic_write_text


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Required derived-evidence input is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Required derived-evidence input is invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"Required derived-evidence input is not a JSON object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build incident candidates and deterministic drill-down recommendations from already-generated "
            "current evidence artifacts. This command performs no infrastructure query and no mutation."
        )
    )
    parser.add_argument("--alert-attention", type=Path, required=True)
    parser.add_argument("--event-correlation", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--change-context", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--summary-out", type=Path)
    parser.add_argument("--max-related", type=int, default=20)
    args = parser.parse_args()

    if args.max_related < 1:
        parser.error("--max-related must be positive")

    artifact = build_incident_candidates(
        _load_json(args.alert_attention),
        _load_json(args.event_correlation),
        _load_json(args.inventory),
        _load_json(args.change_context),
        max_related=args.max_related,
    )
    atomic_write_json(args.out, artifact)
    if args.summary_out:
        atomic_write_text(args.summary_out, render_incident_candidates_markdown(artifact))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
