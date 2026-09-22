from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "reconcile-installed-runtime-module.py"
DEPLOY = ROOT / "scripts" / "deploy-operator-attention-runtime.sh"


def load_module():
    spec = importlib.util.spec_from_file_location("m8_runtime_reconciliation", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(tmp_path: Path):
    source = tmp_path / "repository" / "__init__.py"
    target = tmp_path / "installed" / "__init__.py"
    backup = tmp_path / "backups"
    source.parent.mkdir()
    target.parent.mkdir()
    source.write_text('__version__ = "0.27.0"\n', encoding="utf-8")
    target.write_text('__version__ = "0.26.0"\n', encoding="utf-8")
    source.chmod(0o644)
    target.chmod(0o644)
    return source, target, backup


def test_plan_is_read_only_and_projects_hashes_not_contents(tmp_path: Path):
    module = load_module()
    source, target, backup = fixture(tmp_path)
    inode = target.stat().st_ino

    result = module.observe(source, target)

    assert result["status"] == "CHANGE_REQUIRED"
    assert result["mutation_allowed"] is False
    assert result["mutation_performed"] is False
    assert result["source_contents_projected"] is False
    assert result["installed_contents_projected"] is False
    assert len(result["repository_sha256"]) == 64
    assert len(result["installed_sha256"]) == 64
    assert target.stat().st_ino == inode
    assert not backup.exists()


def test_apply_is_atomic_bounded_and_idempotent(tmp_path: Path):
    module = load_module()
    source, target, backup = fixture(tmp_path)
    original_inode = target.stat().st_ino
    original_hash = module._sha256(target)
    uid, gid = os.getuid(), os.getgid()

    result = module.apply_reconciliation(
        source, target, backup, uid=uid, gid=gid
    )

    assert result["status"] == "RECONCILED"
    assert result["mutation_allowed"] is True
    assert result["mutation_performed"] is True
    assert result["rollback_token"] == original_hash
    assert result["systemd_mutation_performed"] is False
    assert result["service_start_performed"] is False
    assert result["infrastructure_mutation_performed"] is False
    assert module._sha256(target) == module._sha256(source)
    assert target.stat().st_ino != original_inode
    assert target.stat().st_mode & 0o777 == 0o644
    rollback = backup / f"__init__.py.{original_hash}.bak"
    assert rollback.is_file()
    assert rollback.stat().st_mode & 0o777 == 0o600

    repeat = module.apply_reconciliation(
        source, target, backup, uid=uid, gid=gid
    )
    assert repeat["status"] == "ALREADY_RECONCILED"
    assert repeat["mutation_performed"] is False


def test_rollback_restores_exact_backup_and_preserves_new_state_backup(tmp_path: Path):
    module = load_module()
    source, target, backup = fixture(tmp_path)
    uid, gid = os.getuid(), os.getgid()
    original_hash = module._sha256(target)
    applied = module.apply_reconciliation(
        source, target, backup, uid=uid, gid=gid
    )
    reconciled_hash = module._sha256(target)

    result = module.rollback_reconciliation(
        target,
        backup,
        applied["rollback_token"],
        uid=uid,
        gid=gid,
    )

    assert result["status"] == "ROLLED_BACK"
    assert result["before_sha256"] == reconciled_hash
    assert result["after_sha256"] == original_hash
    assert module._sha256(target) == original_hash
    assert (backup / f"__init__.py.{reconciled_hash}.bak").is_file()


def test_apply_restores_original_if_post_install_verification_fails(
    tmp_path: Path, monkeypatch
):
    module = load_module()
    source, target, backup = fixture(tmp_path)
    uid, gid = os.getuid(), os.getgid()
    original = target.read_bytes()
    original_validation = module._validate_installed
    calls = 0

    def fail_verification(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise module.ReconciliationError("FORCED_VERIFICATION_FAILURE")
        return original_validation(*args, **kwargs)

    monkeypatch.setattr(module, "_validate_installed", fail_verification)
    with pytest.raises(module.ReconciliationError, match="FORCED_VERIFICATION_FAILURE"):
        module.apply_reconciliation(source, target, backup, uid=uid, gid=gid)
    assert target.read_bytes() == original


def test_symlink_target_is_rejected_without_mutation(tmp_path: Path):
    module = load_module()
    source, target, _backup = fixture(tmp_path)
    real_target = target.with_name("real.py")
    target.replace(real_target)
    target.symlink_to(real_target)

    with pytest.raises(module.ReconciliationError, match="INSTALLED_MODULE_NOT_REGULAR_FILE"):
        module.observe(source, target)
    assert real_target.read_text(encoding="utf-8") == '__version__ = "0.26.0"\n'


def test_corrupt_existing_rollback_backup_blocks_apply(tmp_path: Path):
    module = load_module()
    source, target, backup = fixture(tmp_path)
    uid, gid = os.getuid(), os.getgid()
    original = target.read_bytes()
    original_hash = module._sha256(target)
    backup.mkdir()
    (backup / f"__init__.py.{original_hash}.bak").write_text(
        "CORRUPT", encoding="utf-8"
    )

    with pytest.raises(module.ReconciliationError, match="ROLLBACK_BACKUP_HASH_MISMATCH"):
        module.apply_reconciliation(source, target, backup, uid=uid, gid=gid)
    assert target.read_bytes() == original


def test_reconciliation_scope_excludes_service_and_infrastructure_mutations():
    helper = SCRIPT.read_text(encoding="utf-8")

    assert 'MODULE = "__init__.py"' in helper
    assert "/opt/infra-assurance/src/infra_assurance" in helper
    assert "/var/lib/infra-assurance/runtime-reconciliation" in helper
    for forbidden in (
        "systemctl",
        "kubectl",
        "ansible-playbook",
        "terraform apply",
        "/etc/systemd",
    ):
        assert forbidden not in helper


def test_future_operator_runtime_deployments_include_package_metadata():
    helper = DEPLOY.read_text(encoding="utf-8")

    assert "MODULES=(\n  __init__.py\n" in helper
    assert "installs package metadata and the accepted operator-attention modules" in helper
