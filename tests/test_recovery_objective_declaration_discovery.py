from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/discovery/m5_recovery_objective_declaration_discovery.py"


def load_module():
    spec = importlib.util.spec_from_file_location("m5_recovery_objective_discovery", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_extracts_only_safe_normalized_rpo_rto_targets_without_raw_line():
    module = load_module()
    text = """service_policy:\n  RPO: 24h\n  recovery time objective = 90 minutes\n"""

    findings = module.scan_text("policy/recovery.yaml", text)

    assert findings == [
        {
            "path": "policy/recovery.yaml",
            "line": 2,
            "objective": "RPO",
            "target": "24h",
            "classification": "EXPLICIT_TARGET_CANDIDATE",
        },
        {
            "path": "policy/recovery.yaml",
            "line": 3,
            "objective": "RTO",
            "target": "90m",
            "classification": "EXPLICIT_TARGET_CANDIDATE",
        },
    ]
    assert all("raw" not in row and "text" not in row and "content" not in row for row in findings)


def test_declaration_without_duration_remains_unaccepted_signal():
    module = load_module()
    findings = module.scan_text(
        "docs/recovery.md",
        "The production RPO must be formally approved before go-live.",
    )

    assert findings == [
        {
            "path": "docs/recovery.md",
            "line": 1,
            "objective": "RPO",
            "target": None,
            "classification": "DECLARATION_SIGNAL_WITHOUT_SAFE_TARGET",
        }
    ]


def test_sensitive_and_state_paths_are_excluded():
    module = load_module()

    denied = (
        ".env",
        "secrets/recovery.yaml",
        "credentials/rpo.json",
        "terraform.tfstate",
        "prod.tfvars",
        "keys/private.pem",
        "certs/backup.key",
    )
    for path in denied:
        assert module.allowed_relative_path(path) is False

    assert module.allowed_relative_path("terraform/recovery.tf") is True
    assert module.allowed_relative_path("policy/rpo.yaml") is True
    assert module.allowed_relative_path("examples/prod.tfvars.example") is True
