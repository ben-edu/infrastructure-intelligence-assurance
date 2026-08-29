from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "discovery" / "m6_terraform_runtime_artifact_source_discovery.py"
SPEC = importlib.util.spec_from_file_location("m6_terraform_runtime_artifact_source_discovery", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _make_roots(tmp_path: Path) -> dict[str, Path]:
    roots = {
        "bm1": tmp_path / "terraform" / "environments" / "bm1",
        "bm2": tmp_path / "terraform" / "environments" / "bm2",
    }
    for root in roots.values():
        root.mkdir(parents=True)
    return roots


def test_discovers_runtime_artifact_metadata_without_reading_contents(tmp_path, monkeypatch):
    roots = _make_roots(tmp_path)
    bm1 = roots["bm1"]
    (bm1 / ".terraform").mkdir()
    (bm1 / ".terraform" / "terraform.tfstate").write_text("sensitive-backend-data", encoding="utf-8")
    (bm1 / ".terraform" / "environment").write_text("private-workspace-name", encoding="utf-8")
    (bm1 / "terraform.tfstate").write_text("sensitive-state-data", encoding="utf-8")
    (bm1 / "terraform.tfstate.backup").write_text("sensitive-backup-data", encoding="utf-8")
    (bm1 / "terraform.tfstate.d" / "private-workspace").mkdir(parents=True)
    (bm1 / "deploy.tfplan").write_text("sensitive-plan-data", encoding="utf-8")

    def fail_read_text(*args, **kwargs):
        raise AssertionError("runtime artifact contents must not be read")

    monkeypatch.setattr(Path, "read_text", fail_read_text)
    result = MODULE.discover(roots)

    assert result["source_status"] == "COMPLETE"
    assert result["runtime_artifact_source_status"] == "RUNTIME_ARTIFACT_METADATA_OBSERVED"
    assert result["working_directories_observed"] == 1
    assert result["top_level_state_artifacts_observed"] == 1
    assert result["top_level_state_backup_artifacts_observed"] == 1
    assert result["workspace_state_directories_observed"] == 1
    assert result["workspace_directories_observed"] == 1
    assert result["backend_metadata_candidates_observed"] == 1
    assert result["workspace_selection_metadata_candidates_observed"] == 1
    assert result["saved_plan_artifact_candidates_observed"] == 1
    rendered = repr(result)
    assert "private-workspace" not in rendered
    assert "deploy.tfplan" not in rendered
    assert "sensitive-state-data" not in rendered


def test_complete_empty_roots_are_bounded_absence(tmp_path):
    roots = _make_roots(tmp_path)
    result = MODULE.discover(roots)

    assert result["source_status"] == "COMPLETE"
    assert result["runtime_artifact_source_status"] == "NONE_OBSERVED_IN_BOUNDED_ROOTS"
    assert result["root_directories_observed"] == 2
    assert result["state_backed_coverage_status"] == "UNKNOWN"
    assert result["drift_status"] == "UNKNOWN"
    assert result["destructive_change_status"] == "UNKNOWN"


def test_missing_expected_root_fails_closed(tmp_path):
    roots = _make_roots(tmp_path)
    roots["bm2"].rmdir()

    result = MODULE.discover(roots)

    assert result["source_status"] == "INCOMPLETE"
    assert result["runtime_artifact_source_status"] == "SOURCE_INCOMPLETE"
    assert result["root_directories_observed"] == 1


def test_relevant_symlink_fails_closed(tmp_path):
    roots = _make_roots(tmp_path)
    target = tmp_path / "outside-state"
    target.write_text("not-read", encoding="utf-8")
    (roots["bm1"] / "terraform.tfstate").symlink_to(target)

    result = MODULE.discover(roots)

    assert result["source_status"] == "INCOMPLETE"
    assert result["runtime_artifact_source_status"] == "SOURCE_INCOMPLETE"
    assert result["symlink_entries_skipped"] == 1
    assert result["top_level_state_artifacts_observed"] == 0
