from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_INVENTORY = Path("/var/lib/infra-assurance/evidence/inventory.json")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _label(entity: dict[str, Any]) -> str:
    subject = entity["subject"]
    namespace = subject.get("namespace") or "-"
    return f"{subject['kind']}/{namespace}/{subject['name']}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Query the read-only workload operational inventory.")
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("summary")

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--namespace")
    list_parser.add_argument("--attention-only", action="store_true")
    list_parser.add_argument(
        "--observability-status",
        choices=("OPERATOR_MONITOR_MATCH", "NO_OPERATOR_MONITOR_MATCH", "UNKNOWN"),
    )
    list_parser.add_argument(
        "--runtime-state",
        choices=(
            "PROMETHEUS_TARGETS_UP",
            "PROMETHEUS_TARGET_DOWN",
            "ACTIVE_ALERT",
            "NO_RUNTIME_SIGNAL_MATCH",
            "UNKNOWN",
        ),
    )

    show_parser = subparsers.add_parser("show")
    show_parser.add_argument("--namespace", required=True)
    show_parser.add_argument("--kind", choices=("Deployment", "StatefulSet", "DaemonSet"), required=True)
    show_parser.add_argument("--name", required=True)

    args = parser.parse_args()
    try:
        inventory = _load(args.inventory)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "INVENTORY_UNAVAILABLE", "summary": str(exc)}, indent=2))
        return 2

    if args.command == "summary":
        print(
            json.dumps(
                {
                    "cluster_id": inventory["cluster_id"],
                    "generated_at": inventory["generated_at"],
                    "mutation_allowed": inventory["mutation_allowed"],
                    "observability_source_status": inventory.get("observability_source_status"),
                    "prometheus_runtime_source_status": inventory.get("prometheus_runtime_source_status"),
                    "summary": inventory["summary"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "list":
        entities = inventory.get("entities", [])
        for entity in entities:
            subject = entity["subject"]
            if args.namespace and subject.get("namespace") != args.namespace:
                continue
            if args.attention_only and not entity.get("attention"):
                continue
            observability = entity.get("observability", {})
            if args.observability_status and observability.get("status") != args.observability_status:
                continue
            runtime = entity.get("runtime_observability", {})
            if args.runtime_state and runtime.get("state") != args.runtime_state:
                continue
            declared = entity.get("declared", {})
            change = entity.get("recent_change", {})
            print(
                f"{_label(entity)} "
                f"declared={declared.get('coverage')} "
                f"comparison={declared.get('comparison')} "
                f"change={change.get('state')} "
                f"observability={observability.get('status')} "
                f"runtime={runtime.get('state')} "
                f"attention={len(entity.get('attention', []))}"
            )
        return 0

    matches = [
        entity
        for entity in inventory.get("entities", [])
        if entity["subject"].get("namespace") == args.namespace
        and entity["subject"].get("kind") == args.kind
        and entity["subject"].get("name") == args.name
    ]
    if not matches:
        print(
            json.dumps(
                {
                    "status": "NOT_FOUND",
                    "namespace": args.namespace,
                    "kind": args.kind,
                    "name": args.name,
                },
                indent=2,
            )
        )
        return 1

    print(json.dumps(matches[0], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
