from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io_utils import atomic_write_json

HISTORY_VERSION = "0.1"
DEFAULT_RETENTION = 288


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def snapshot_id(snapshot: dict[str, Any]) -> str:
    generated_at = str(snapshot["generated_at"])
    stamp = (
        generated_at.replace("-", "")
        .replace(":", "")
        .replace(".", "")
        .replace("+00:00", "Z")
    )
    digest = hashlib.sha256(_canonical_bytes(snapshot)).hexdigest()[:12]
    return f"{stamp}-{digest}"


def _collection_failure_count(snapshot: dict[str, Any]) -> int:
    return sum(
        envelope.get("observation_status") == "FAILED_TO_OBSERVE"
        and envelope.get("subject", {}).get("kind", "").endswith("Collection")
        for envelope in snapshot.get("evidence", [])
    )


@dataclass(frozen=True)
class HistoryEntry:
    snapshot_id: str
    generated_at: str
    file: str
    evidence_count: int
    failed_collections: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "generated_at": self.generated_at,
            "file": self.file,
            "evidence_count": self.evidence_count,
            "failed_collections": self.failed_collections,
        }


class SnapshotHistoryStore:
    """Small replaceable file-backed history store for normalized evidence snapshots."""

    def __init__(self, root: Path, *, retention: int = DEFAULT_RETENTION) -> None:
        if retention < 2:
            raise ValueError("history retention must be at least 2 snapshots")
        self.root = root
        self.retention = retention
        self.snapshots_dir = root / "snapshots"
        self.index_path = root / "index.json"

    def _empty_index(self) -> dict[str, Any]:
        return {
            "history_version": HISTORY_VERSION,
            "retention": self.retention,
            "snapshots": [],
        }

    def read_index(self) -> dict[str, Any]:
        if not self.index_path.exists():
            return self._empty_index()
        value = json.loads(self.index_path.read_text(encoding="utf-8"))
        if value.get("history_version") != HISTORY_VERSION:
            raise ValueError("unsupported history index version")
        if not isinstance(value.get("snapshots"), list):
            raise ValueError("invalid history index")
        return value

    def _load_entry_snapshot(self, entry: dict[str, Any]) -> dict[str, Any]:
        path = self.root / entry["file"]
        return json.loads(path.read_text(encoding="utf-8"))

    def latest(self) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        index = self.read_index()
        if not index["snapshots"]:
            return None, None
        entry = index["snapshots"][-1]
        return entry, self._load_entry_snapshot(entry)

    def append(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        index = self.read_index()
        previous_entry = index["snapshots"][-1] if index["snapshots"] else None
        previous_snapshot = self._load_entry_snapshot(previous_entry) if previous_entry else None

        current_id = snapshot_id(snapshot)
        relative_file = f"snapshots/{current_id}.json"
        entry = HistoryEntry(
            snapshot_id=current_id,
            generated_at=snapshot["generated_at"],
            file=relative_file,
            evidence_count=len(snapshot.get("evidence", [])),
            failed_collections=_collection_failure_count(snapshot),
        ).as_dict()

        destination = self.root / relative_file
        if not destination.exists():
            atomic_write_json(destination, snapshot)

        entries = [item for item in index["snapshots"] if item["snapshot_id"] != current_id]
        entries.append(entry)
        entries.sort(key=lambda item: (item["generated_at"], item["snapshot_id"]))

        dropped = entries[:-self.retention] if len(entries) > self.retention else []
        retained = entries[-self.retention :]
        new_index = {
            "history_version": HISTORY_VERSION,
            "retention": self.retention,
            "snapshots": retained,
        }

        # Commit the new index before garbage-collecting files that it no longer references.
        # If the process dies after the atomic index replacement, leftover dropped snapshots are
        # harmless orphan files; if it dies before replacement, the old index still references
        # only existing files.
        atomic_write_json(self.index_path, new_index)
        for old in dropped:
            (self.root / old["file"]).unlink(missing_ok=True)

        return {
            "entry": entry,
            "previous_entry": previous_entry,
            "previous_snapshot": previous_snapshot,
            "retained_snapshots": len(retained),
        }


def history_status(root: Path, *, retention: int = DEFAULT_RETENTION) -> dict[str, Any]:
    store = SnapshotHistoryStore(root, retention=retention)
    index = store.read_index()
    snapshots = index["snapshots"]
    return {
        "history_version": HISTORY_VERSION,
        "retention": index.get("retention", retention),
        "snapshot_count": len(snapshots),
        "oldest": snapshots[0] if snapshots else None,
        "latest": snapshots[-1] if snapshots else None,
        "snapshots_with_collection_failures": sum(item.get("failed_collections", 0) > 0 for item in snapshots),
    }
