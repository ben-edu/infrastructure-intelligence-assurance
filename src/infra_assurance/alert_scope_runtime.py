from __future__ import annotations

import argparse
import json
from pathlib import Path

from .alert_scope_validation import validate_alert_attention_scopes
from .alertmanager_runtime_intelligence import render_alert_attention_markdown
from .io_utils import atomic_write_json, atomic_write_text
from .kubernetes_event_intelligence import (
    build_event_correlation,
    render_event_correlation_markdown,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate alert attention resource scope against same-cycle Kubernetes evidence "
            "and rebuild Event correlation without performing infrastructure queries."
        )
    )
    parser.add_argument("--attention", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--event-runtime", type=Path, required=True)
    parser.add_argument("--event-correlation-out", type=Path, required=True)
    parser.add_argument("--attention-summary-out", type=Path)
    parser.add_argument("--event-correlation-summary-out", type=Path)
    args = parser.parse_args()

    attention = _load(args.attention)
    snapshot = _load(args.snapshot)
    event_runtime = _load(args.event_runtime)

    corrected = validate_alert_attention_scopes(attention, snapshot)
    event_correlation = build_event_correlation(event_runtime, corrected)

    if corrected.get("source_status", {}).get("kubernetes_scope") != "COMPLETE":
        event_correlation.setdefault("source_status", {})["alert_attention"] = "PARTIAL"

    atomic_write_json(args.attention, corrected)
    atomic_write_json(args.event_correlation_out, event_correlation)

    if args.attention_summary_out:
        atomic_write_text(
            args.attention_summary_out,
            render_alert_attention_markdown(corrected),
        )
    if args.event_correlation_summary_out:
        atomic_write_text(
            args.event_correlation_summary_out,
            render_event_correlation_markdown(event_correlation),
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
