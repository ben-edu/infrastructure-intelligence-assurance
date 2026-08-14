from __future__ import annotations

from datetime import datetime
from typing import Any


def parse_rfc3339(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def freshness(envelope: dict[str, Any], now: datetime) -> str:
    """Derive CURRENT/STALE from a successful observation's expires_at value."""
    expires_at = envelope.get("expires_at")
    if expires_at is None:
        raise ValueError("freshness is undefined without expires_at")

    expiry = parse_rfc3339(expires_at)
    return "CURRENT" if now <= expiry else "STALE"
