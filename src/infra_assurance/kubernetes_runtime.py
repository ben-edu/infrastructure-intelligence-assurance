from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .kubernetes_inventory import collect_inventory
from .operational_context import build_operational_context, render_operational_context_markdown


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect Kubernetes inventory and emit full evidence plus compact operational context."
    )
    parser.add_argument("--cluster-id", default=os.environ.get("IIA_CLUSTER_ID"))
    parser.add_argument("--context", dest="kubectl_context", default=os.environ.get("IIA_KUBECTL_CONTEXT"))
    parser.add_argument("--evidence-out", type=Path, required=True)
    parser.add_argument("--context-out", type=Path, required=True)
    parser.add_argument("--summary-out", type=Path)
    args = parser.parse_args()

    if not args.cluster_id:
        parser.error("--cluster-id or IIA_CLUSTER_ID is required")

    snapshot = collect_inventory(
        cluster_id=args.cluster_id,
        kubectl_context=args.kubectl_context,
    )
    context = build_operational_context(snapshot)

    args.evidence_out.parent.mkdir(parents=True, exist_ok=True)
    args.context_out.parent.mkdir(parents=True, exist_ok=True)
    args.evidence_out.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    args.context_out.write_text(
        json.dumps(context, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    if args.summary_out:
        args.summary_out.parent.mkdir(parents=True, exist_ok=True)
        args.summary_out.write_text(
            render_operational_context_markdown(snapshot, context), encoding="utf-8"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
