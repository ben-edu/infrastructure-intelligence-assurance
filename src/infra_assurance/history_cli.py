from __future__ import annotations

import argparse
import json
from pathlib import Path

from .history import DEFAULT_RETENTION, SnapshotHistoryStore, history_status

DEFAULT_HISTORY_ROOT = Path("/var/lib/infra-assurance/history/kubernetes")


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect bounded Kubernetes evidence history.")
    parser.add_argument("--history-dir", type=Path, default=DEFAULT_HISTORY_ROOT)
    parser.add_argument("--retention", type=int, default=DEFAULT_RETENTION)
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("status", help="Show compact history status.")
    list_parser = subparsers.add_parser("list", help="List recent immutable snapshot metadata.")
    list_parser.add_argument("--limit", type=int, default=20)

    args = parser.parse_args()
    command = args.command or "status"

    if command == "status":
        print(json.dumps(history_status(args.history_dir, retention=args.retention), indent=2, sort_keys=True))
        return 0

    if command == "list":
        if args.limit < 1:
            parser.error("--limit must be positive")
        store = SnapshotHistoryStore(args.history_dir, retention=args.retention)
        index = store.read_index()
        print(json.dumps(index["snapshots"][-args.limit :], indent=2, sort_keys=True))
        return 0

    parser.error(f"unsupported command: {command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
