from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_systemd_runtime_emits_inventory_artifacts():
    text = (ROOT / "systemd" / "infra-assurance-kubernetes.service").read_text(
        encoding="utf-8"
    )
    assert "--inventory-out /var/lib/infra-assurance/evidence/inventory.json" in text
    assert "--inventory-summary-out /var/lib/infra-assurance/evidence/inventory.md" in text


def test_bootstrap_installs_inventory_cli():
    text = (ROOT / "scripts" / "bootstrap-observer.sh").read_text(encoding="utf-8")
    assert 'INVENTORY_BIN="/usr/local/bin/iia-inventory"' in text
    assert "infra_assurance.inventory_cli" in text
    assert "Inventory JSON:" in text
