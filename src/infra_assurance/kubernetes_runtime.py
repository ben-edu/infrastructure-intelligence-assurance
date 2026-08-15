from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .change_context import build_change_context, render_change_context_markdown
from .drift import build_drift_report, load_declared_records, render_drift_markdown
from .history import DEFAULT_RETENTION, SnapshotHistoryStore, snapshot_id
from .io_utils import atomic_write_json, atomic_write_text
from .kubernetes_inventory import collect_inventory
from .kubernetes_topology import build_kubernetes_topology, render_topology_markdown
from .operational_context import build_operational_context, render_operational_context_markdown
from .operational_inventory import (
    build_operational_inventory,
    render_operational_inventory_markdown,
)
from .snapshot_diff import build_snapshot_diff, render_snapshot_diff_markdown

DEFAULT_HISTORY_DIR = Path("/var/lib/infra-assurance/history/kubernetes")
DEFAULT_DECLARED_DIR = Path("/var/lib/infra-assurance/declared/current")
DEFAULT_DECLARED_STATUS = Path("/var/lib/infra-assurance/declared/source-status.json")


def _seed_history_from_existing_latest(
    store: SnapshotHistoryStore,
    evidence_path: Path,
    *,
    cluster_id: str,
) -> None:
    existing_entry, _existing_snapshot = store.latest()
    if existing_entry is not None or not evidence_path.exists():
        return
    try:
        candidate = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if candidate.get("cluster_id") != cluster_id or not candidate.get("generated_at"):
        return
    store.append(candidate)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Collect Kubernetes evidence and emit current context, topology, bounded history, "
            "snapshot diff, Git-declared drift, compact change context, and a workload-centric "
            "operational inventory projection."
        )
    )
    parser.add_argument("--cluster-id", default=os.environ.get("IIA_CLUSTER_ID"))
    parser.add_argument(
        "--context", dest="kubectl_context", default=os.environ.get("IIA_KUBECTL_CONTEXT")
    )
    parser.add_argument("--evidence-out", type=Path, required=True)
    parser.add_argument("--context-out", type=Path, required=True)
    parser.add_argument("--summary-out", type=Path)
    parser.add_argument("--topology-out", type=Path)
    parser.add_argument("--topology-summary-out", type=Path)
    parser.add_argument("--history-dir", type=Path, default=DEFAULT_HISTORY_DIR)
    parser.add_argument(
        "--history-retention",
        type=int,
        default=int(os.environ.get("IIA_HISTORY_RETENTION", str(DEFAULT_RETENTION))),
    )
    parser.add_argument("--diff-out", type=Path)
    parser.add_argument("--diff-summary-out", type=Path)
    parser.add_argument("--declared-dir", type=Path, default=DEFAULT_DECLARED_DIR)
    parser.add_argument("--declared-status", type=Path, default=DEFAULT_DECLARED_STATUS)
    parser.add_argument("--drift-out", type=Path)
    parser.add_argument("--drift-summary-out", type=Path)
    parser.add_argument("--change-context-out", type=Path)
    parser.add_argument("--change-context-summary-out", type=Path)
    parser.add_argument("--inventory-out", type=Path)
    parser.add_argument("--inventory-summary-out", type=Path)
    args = parser.parse_args()

    if not args.cluster_id:
        parser.error("--cluster-id or IIA_CLUSTER_ID is required")
    if args.history_retention < 2:
        parser.error("--history-retention must be at least 2")

    store = SnapshotHistoryStore(args.history_dir, retention=args.history_retention)
    _seed_history_from_existing_latest(store, args.evidence_out, cluster_id=args.cluster_id)
    previous_entry, previous_snapshot = store.latest()

    snapshot = collect_inventory(
        cluster_id=args.cluster_id,
        kubectl_context=args.kubectl_context,
    )
    current_snapshot_id = snapshot_id(snapshot)

    context = build_operational_context(snapshot)
    topology = build_kubernetes_topology(snapshot)
    diff = build_snapshot_diff(
        previous_snapshot,
        snapshot,
        previous_snapshot_id=previous_entry["snapshot_id"] if previous_entry else None,
        current_snapshot_id=current_snapshot_id,
    )
    declared_load = load_declared_records(
        args.declared_dir,
        source_status_path=args.declared_status,
    )
    drift = build_drift_report(snapshot, declared_load)
    change_context = build_change_context(diff, drift)
    inventory = build_operational_inventory(
        snapshot,
        topology,
        diff,
        drift,
        declared_load,
    )

    store.append(snapshot)

    atomic_write_json(args.evidence_out, snapshot)
    atomic_write_json(args.context_out, context)

    if args.summary_out:
        atomic_write_text(args.summary_out, render_operational_context_markdown(snapshot, context))
    if args.topology_out:
        atomic_write_json(args.topology_out, topology)
    if args.topology_summary_out:
        atomic_write_text(args.topology_summary_out, render_topology_markdown(topology))
    if args.diff_out:
        atomic_write_json(args.diff_out, diff)
    if args.diff_summary_out:
        atomic_write_text(args.diff_summary_out, render_snapshot_diff_markdown(diff))
    if args.drift_out:
        atomic_write_json(args.drift_out, drift)
    if args.drift_summary_out:
        atomic_write_text(args.drift_summary_out, render_drift_markdown(drift))
    if args.change_context_out:
        atomic_write_json(args.change_context_out, change_context)
    if args.change_context_summary_out:
        atomic_write_text(args.change_context_summary_out, render_change_context_markdown(change_context))
    if args.inventory_out:
        atomic_write_json(args.inventory_out, inventory)
    if args.inventory_summary_out:
        atomic_write_text(args.inventory_summary_out, render_operational_inventory_markdown(inventory))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
