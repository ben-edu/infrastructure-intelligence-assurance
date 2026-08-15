from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .alertmanager_runtime_intelligence import (
    DEFAULT_ALERTMANAGER_NAMESPACE,
    DEFAULT_ALERTMANAGER_PORT,
    DEFAULT_ALERTMANAGER_SERVICE,
    build_alert_attention,
    build_alertmanager_runtime_intelligence,
    render_alert_attention_markdown,
    render_alertmanager_runtime_markdown,
)
from .change_context import build_change_context, render_change_context_markdown
from .drift import build_drift_report, load_declared_records, render_drift_markdown
from .history import DEFAULT_RETENTION, SnapshotHistoryStore, snapshot_id
from .io_utils import atomic_write_json, atomic_write_text
from .kubernetes_event_intelligence import (
    DEFAULT_MAX_EVENTS,
    DEFAULT_WINDOW_SECONDS,
    build_event_correlation,
    build_kubernetes_event_runtime,
    render_event_correlation_markdown,
    render_kubernetes_event_markdown,
)
from .kubernetes_inventory import collect_inventory
from .kubernetes_topology import build_kubernetes_topology, render_topology_markdown
from .operational_context import build_operational_context, render_operational_context_markdown
from .operational_inventory import (
    build_operational_inventory,
    render_operational_inventory_markdown,
)
from .prometheus_operator_coverage import (
    attach_observability_coverage,
    build_prometheus_operator_coverage,
    render_inventory_observability_markdown,
    render_observability_coverage_markdown,
)
from .prometheus_runtime_intelligence import (
    DEFAULT_PROMETHEUS_NAMESPACE,
    DEFAULT_PROMETHEUS_PORT,
    DEFAULT_PROMETHEUS_SERVICE,
    attach_prometheus_runtime,
    build_prometheus_runtime_intelligence,
    render_inventory_runtime_markdown,
    render_prometheus_runtime_markdown,
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
            "snapshot diff, Git-declared drift, compact change context, Prometheus Operator "
            "configuration coverage, Prometheus runtime target/alert intelligence, Alertmanager "
            "handling/correlation evidence, Kubernetes Event evidence/correlation, alert attention, "
            "and a workload-centric operational inventory projection."
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
    parser.add_argument("--observability-coverage-out", type=Path)
    parser.add_argument("--observability-coverage-summary-out", type=Path)
    parser.add_argument("--prometheus-runtime-out", type=Path)
    parser.add_argument("--prometheus-runtime-summary-out", type=Path)
    parser.add_argument(
        "--prometheus-namespace",
        default=os.environ.get("IIA_PROMETHEUS_NAMESPACE", DEFAULT_PROMETHEUS_NAMESPACE),
    )
    parser.add_argument(
        "--prometheus-service",
        default=os.environ.get("IIA_PROMETHEUS_SERVICE", DEFAULT_PROMETHEUS_SERVICE),
    )
    parser.add_argument(
        "--prometheus-port",
        type=int,
        default=int(os.environ.get("IIA_PROMETHEUS_PORT", str(DEFAULT_PROMETHEUS_PORT))),
    )
    parser.add_argument("--alertmanager-runtime-out", type=Path)
    parser.add_argument("--alertmanager-runtime-summary-out", type=Path)
    parser.add_argument("--alert-attention-out", type=Path)
    parser.add_argument("--alert-attention-summary-out", type=Path)
    parser.add_argument(
        "--alertmanager-namespace",
        default=os.environ.get("IIA_ALERTMANAGER_NAMESPACE", DEFAULT_ALERTMANAGER_NAMESPACE),
    )
    parser.add_argument(
        "--alertmanager-service",
        default=os.environ.get("IIA_ALERTMANAGER_SERVICE", DEFAULT_ALERTMANAGER_SERVICE),
    )
    parser.add_argument(
        "--alertmanager-port",
        type=int,
        default=int(os.environ.get("IIA_ALERTMANAGER_PORT", str(DEFAULT_ALERTMANAGER_PORT))),
    )
    parser.add_argument("--kubernetes-event-runtime-out", type=Path)
    parser.add_argument("--kubernetes-event-runtime-summary-out", type=Path)
    parser.add_argument("--event-correlation-out", type=Path)
    parser.add_argument("--event-correlation-summary-out", type=Path)
    parser.add_argument(
        "--event-window-seconds",
        type=int,
        default=int(os.environ.get("IIA_EVENT_WINDOW_SECONDS", str(DEFAULT_WINDOW_SECONDS))),
    )
    parser.add_argument(
        "--event-max-records",
        type=int,
        default=int(os.environ.get("IIA_EVENT_MAX_RECORDS", str(DEFAULT_MAX_EVENTS))),
    )
    parser.add_argument("--inventory-out", type=Path)
    parser.add_argument("--inventory-summary-out", type=Path)
    args = parser.parse_args()

    if not args.cluster_id:
        parser.error("--cluster-id or IIA_CLUSTER_ID is required")
    if args.history_retention < 2:
        parser.error("--history-retention must be at least 2")
    if args.prometheus_port < 1 or args.prometheus_port > 65535:
        parser.error("--prometheus-port must be between 1 and 65535")
    if args.alertmanager_port < 1 or args.alertmanager_port > 65535:
        parser.error("--alertmanager-port must be between 1 and 65535")
    if args.event_window_seconds < 60:
        parser.error("--event-window-seconds must be at least 60")
    if args.event_max_records < 1:
        parser.error("--event-max-records must be at least 1")

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
    observability_coverage = build_prometheus_operator_coverage(
        snapshot,
        topology,
        kubectl_context=args.kubectl_context,
    )
    prometheus_runtime = build_prometheus_runtime_intelligence(
        snapshot,
        topology,
        kubectl_context=args.kubectl_context,
        prometheus_namespace=args.prometheus_namespace,
        prometheus_service=args.prometheus_service,
        prometheus_port=args.prometheus_port,
    )
    alertmanager_runtime = build_alertmanager_runtime_intelligence(
        prometheus_runtime,
        kubectl_context=args.kubectl_context,
        alertmanager_namespace=args.alertmanager_namespace,
        alertmanager_service=args.alertmanager_service,
        alertmanager_port=args.alertmanager_port,
    )
    alert_attention = build_alert_attention(prometheus_runtime, alertmanager_runtime)
    kubernetes_event_runtime = build_kubernetes_event_runtime(
        cluster_id=args.cluster_id,
        kubectl_context=args.kubectl_context,
        window_seconds=args.event_window_seconds,
        max_events=args.event_max_records,
    )
    event_correlation = build_event_correlation(kubernetes_event_runtime, alert_attention)
    inventory = build_operational_inventory(
        snapshot,
        topology,
        diff,
        drift,
        declared_load,
    )
    inventory = attach_observability_coverage(inventory, observability_coverage)
    inventory = attach_prometheus_runtime(inventory, prometheus_runtime)

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
    if args.observability_coverage_out:
        atomic_write_json(args.observability_coverage_out, observability_coverage)
    if args.observability_coverage_summary_out:
        atomic_write_text(
            args.observability_coverage_summary_out,
            render_observability_coverage_markdown(observability_coverage),
        )
    if args.prometheus_runtime_out:
        atomic_write_json(args.prometheus_runtime_out, prometheus_runtime)
    if args.prometheus_runtime_summary_out:
        atomic_write_text(
            args.prometheus_runtime_summary_out,
            render_prometheus_runtime_markdown(prometheus_runtime),
        )
    if args.alertmanager_runtime_out:
        atomic_write_json(args.alertmanager_runtime_out, alertmanager_runtime)
    if args.alertmanager_runtime_summary_out:
        atomic_write_text(
            args.alertmanager_runtime_summary_out,
            render_alertmanager_runtime_markdown(alertmanager_runtime),
        )
    if args.alert_attention_out:
        atomic_write_json(args.alert_attention_out, alert_attention)
    if args.alert_attention_summary_out:
        atomic_write_text(
            args.alert_attention_summary_out,
            render_alert_attention_markdown(alert_attention),
        )
    if args.kubernetes_event_runtime_out:
        atomic_write_json(args.kubernetes_event_runtime_out, kubernetes_event_runtime)
    if args.kubernetes_event_runtime_summary_out:
        atomic_write_text(
            args.kubernetes_event_runtime_summary_out,
            render_kubernetes_event_markdown(kubernetes_event_runtime),
        )
    if args.event_correlation_out:
        atomic_write_json(args.event_correlation_out, event_correlation)
    if args.event_correlation_summary_out:
        atomic_write_text(
            args.event_correlation_summary_out,
            render_event_correlation_markdown(event_correlation),
        )
    if args.inventory_out:
        atomic_write_json(args.inventory_out, inventory)
    if args.inventory_summary_out:
        base_markdown = render_operational_inventory_markdown(inventory)
        with_coverage = render_inventory_observability_markdown(
            base_markdown,
            observability_coverage,
        )
        atomic_write_text(
            args.inventory_summary_out,
            render_inventory_runtime_markdown(with_coverage, prometheus_runtime),
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
