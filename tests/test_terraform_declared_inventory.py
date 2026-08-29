from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "discovery" / "m6_terraform_declared_inventory.py"


def load_module():
    spec = importlib.util.spec_from_file_location("m6_terraform_declared_inventory", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_safe_structural_projection_does_not_return_sensitive_hcl_values():
    module = load_module()
    text = r'''
terraform {
  backend "s3" {
    bucket = "private-backup-bucket"
    key    = "secret/state.tfstate"
  }
}
provider "ovh" {
  endpoint = "ovh-eu"
  token    = var.private_token
}
resource "ovh_cloud_project_instance" "private_instance_name" {
  name = "do-not-project-this-instance"
}
data "ovh_cloud_project_database_certificates" "private_data_name" {}
module "private_module_name" {
  source = "git::ssh://private.example.invalid/secret/module.git"
}
variable "private_token" {
  default = "SUPER_SECRET_VALUE"
}
output "private_output" {
  value = var.private_token
}
'''
    projected = module._parse_structure(text)
    rendered = repr(projected)

    assert projected["backend_types"] == ["s3"]
    assert projected["provider_types"] == ["ovh"]
    assert projected["resource_types"] == ["ovh_cloud_project_instance"]
    assert projected["data_source_types"] == ["ovh_cloud_project_database_certificates"]
    assert projected["resource_blocks"] == 1
    assert projected["module_blocks"] == 1
    assert projected["variable_blocks"] == 1
    assert projected["output_blocks"] == 1

    for forbidden in (
        "private-backup-bucket",
        "secret/state.tfstate",
        "private_instance_name",
        "do-not-project-this-instance",
        "private_data_name",
        "private_module_name",
        "private.example.invalid",
        "private_token",
        "SUPER_SECRET_VALUE",
        "private_output",
    ):
        assert forbidden not in rendered


def test_comments_do_not_create_fake_terraform_blocks():
    module = load_module()
    text = r'''
# resource "fake_one" "x" {}
// provider "fake-provider" {}
/*
backend "fake-backend" {}
resource "fake_two" "x" {}
*/
resource "real_type" "real_name" {
  description = "https://example.invalid/path#fragment // still string"
}
'''
    projected = module._parse_structure(text)
    assert projected["resource_types"] == ["real_type"]
    assert projected["resource_blocks"] == 1
    assert projected["provider_blocks"] == 0
    assert projected["backend_blocks"] == 0


def test_file_selection_is_git_tracked_tf_only_and_preserves_declared_only_boundary(tmp_path: Path):
    module = load_module()
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)

    (tmp_path / "main.tf").write_text(
        'provider "ovh" {}\nresource "ovh_cloud_project_instance" "vm" {}\n',
        encoding="utf-8",
    )
    (tmp_path / "terraform.tfvars").write_text('password = "DO_NOT_READ"\n', encoding="utf-8")
    (tmp_path / "terraform.tfstate").write_text('{"secret":"DO_NOT_READ_STATE"}\n', encoding="utf-8")
    (tmp_path / "untracked.tf").write_text('resource "should_not_appear" "x" {}\n', encoding="utf-8")
    (tmp_path / "modules").mkdir()
    (tmp_path / "modules" / "network.tf").write_text('resource "ovh_cloud_project_network_private" "n" {}\n', encoding="utf-8")

    subprocess.run(
        ["git", "-C", str(tmp_path), "add", "main.tf", "terraform.tfvars", "terraform.tfstate", "modules/network.tf"],
        check=True,
    )

    result = module.discover(tmp_path)

    assert result["source_status"] == "COMPLETE"
    assert result["tracked_tf_files_returned"] == 2
    assert result["tracked_tf_files_scanned"] == 2
    assert result["resource_blocks"] == 2
    assert result["resource_type_counts"]["ovh_cloud_project_instance"] == 1
    assert result["resource_type_counts"]["ovh_cloud_project_network_private"] == 1
    assert "should_not_appear" not in result["resource_type_counts"]
    assert result["directories"]["."]["classification"] == "ROOT_CANDIDATE"
    assert result["directories"]["modules"]["classification"] == "MODULE_DIRECTORY"


def test_script_cannot_invoke_terraform_or_promote_live_drift():
    source = SCRIPT.read_text(encoding="utf-8")
    assert '["terraform"' not in source
    assert "terraform apply" not in source.lower()
    assert "terraform destroy" not in source.lower()
    assert "managed_resource_coverage_status: DECLARED_CONFIGURATION_ONLY" in source
    assert "live_resource_coverage_status: UNKNOWN" in source
    assert "drift_claims: 0" in source
    assert "destructive_change_claims: 0" in source
    assert "mutation_allowed: False" in source
