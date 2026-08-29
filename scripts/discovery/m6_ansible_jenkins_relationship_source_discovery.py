from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

INFRA_REPO = Path("/home/ben/projects/afpa-infra-rebuild")
MAX_SOURCE_BYTES = 512 * 1024
SAFE_SUFFIXES = {".groovy", ".jenkins", ".yml", ".yaml", ".sh", ".py", ".json"}
SAFE_BASENAMES = {"jenkinsfile"}
SENSITIVE_PARTS = {
    ".env",
    "group_vars",
    "host_vars",
    "vars",
    "secrets",
    "secret",
    "credentials",
    "credential",
    "vault",
    "private",
    ".terraform",
}
SENSITIVE_SUFFIXES = {".tfstate", ".tfvars", ".pem", ".key", ".p12", ".pfx"}

ANSIBLE_ENTRYPOINT_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9_-])ansible-playbook(?![A-Za-z0-9_-])", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z0-9_-])ansible-runner\s+run(?![A-Za-z0-9_-])", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z0-9_-])ansible-navigator\s+run(?![A-Za-z0-9_-])", re.IGNORECASE),
)
JENKINS_CONTEXT_PATTERNS = (
    re.compile(r"\bpipeline\s*\{", re.IGNORECASE),
    re.compile(r"\bstage\s*\(", re.IGNORECASE),
    re.compile(r"\bjenkins\b", re.IGNORECASE),
    re.compile(r"\bhudson\b", re.IGNORECASE),
)


def _safe_candidate_path(relative: str) -> bool:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        return False
    lowered_parts = {part.lower() for part in path.parts}
    if lowered_parts & SENSITIVE_PARTS:
        return False
    lowered_name = path.name.lower()
    if any(token in lowered_name for token in ("secret", "credential", "password", "token", "private-key", "private_key")):
        return False
    if path.suffix.lower() in SENSITIVE_SUFFIXES:
        return False
    return lowered_name in SAFE_BASENAMES or path.suffix.lower() in SAFE_SUFFIXES


def _jenkins_context(relative: str, text: str) -> bool:
    if Path(relative).name.lower() in SAFE_BASENAMES:
        return True
    return any(pattern.search(text) for pattern in JENKINS_CONTEXT_PATTERNS)


def _ansible_entrypoint_signal(text: str) -> bool:
    return any(pattern.search(text) for pattern in ANSIBLE_ENTRYPOINT_PATTERNS)


def _relationship_signal(relative: str, text: str) -> bool:
    return _jenkins_context(relative, text) and _ansible_entrypoint_signal(text)


def _tracked_files(repo: Path) -> tuple[str, list[str]]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "-z"],
            capture_output=True,
            timeout=20,
            check=False,
        )
    except Exception:
        return "FAILED_TO_OBSERVE", []
    if proc.returncode != 0:
        return "FAILED_TO_OBSERVE", []
    try:
        decoded = proc.stdout.decode("utf-8")
    except UnicodeDecodeError:
        return "FAILED_TO_OBSERVE", []
    return "COMPLETE", [item for item in decoded.split("\0") if item]


def discover(repo: Path = INFRA_REPO) -> dict[str, Any]:
    tracked_status, tracked = _tracked_files(repo)
    result: dict[str, Any] = {
        "source_mode": "GIT_TRACKED_SAFE_JENKINS_ANSIBLE_RELATIONSHIP_TEXT_ONLY",
        "source_status": tracked_status,
        "tracked_files_returned": len(tracked),
        "candidate_files_selected": 0,
        "candidate_files_scanned": 0,
        "excluded_or_unsafe_paths": 0,
        "read_or_decode_skips": 0,
        "oversize_skips": 0,
        "jenkins_context_files": 0,
        "ansible_entrypoint_signal_files": 0,
        "explicit_relationship_signal_files": 0,
        "relationship_source_status": "FAILED_TO_OBSERVE" if tracked_status != "COMPLETE" else "NONE_OBSERVED_IN_BOUNDED_SOURCE",
        "jenkins_api_invoked": False,
        "jenkins_console_logs_inspected": False,
        "jenkins_job_config_bodies_inspected": False,
        "jenkins_build_parameters_inspected": False,
        "ansible_cli_invoked": False,
        "ssh_connections_performed": False,
        "execution_outcome_status": "UNKNOWN",
        "execution_success_status": "UNKNOWN",
        "idempotence_status": "UNKNOWN",
        "configuration_drift_status": "UNKNOWN",
        "successful_execution_claims": 0,
        "idempotence_claims": 0,
        "drift_claims": 0,
    }
    if tracked_status != "COMPLETE":
        return result

    for relative in tracked:
        if not _safe_candidate_path(relative):
            result["excluded_or_unsafe_paths"] += 1
            continue
        result["candidate_files_selected"] += 1
        path = repo / relative
        try:
            size = path.stat().st_size
        except OSError:
            result["read_or_decode_skips"] += 1
            continue
        if size > MAX_SOURCE_BYTES:
            result["oversize_skips"] += 1
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            result["read_or_decode_skips"] += 1
            continue

        result["candidate_files_scanned"] += 1
        jenkins = _jenkins_context(relative, text)
        ansible = _ansible_entrypoint_signal(text)
        if jenkins:
            result["jenkins_context_files"] += 1
        if ansible:
            result["ansible_entrypoint_signal_files"] += 1
        if jenkins and ansible:
            result["explicit_relationship_signal_files"] += 1

    if result["read_or_decode_skips"] or result["oversize_skips"]:
        result["source_status"] = "INCOMPLETE"
        result["relationship_source_status"] = "SOURCE_INCOMPLETE"
    elif result["explicit_relationship_signal_files"]:
        result["relationship_source_status"] = "EXPLICIT_DECLARED_RELATIONSHIP_SIGNAL_OBSERVED"
    else:
        result["relationship_source_status"] = "NONE_OBSERVED_IN_BOUNDED_SOURCE"
    return result


def main() -> int:
    result = discover()

    print("===== M6 ANSIBLE-TO-JENKINS RELATIONSHIP SOURCE DISCOVERY =====")
    print()
    print("===== SAFETY =====")
    print("mutation_allowed: False")
    print("jenkins_api_invoked: False")
    print("jenkins_console_logs_inspected: False")
    print("jenkins_job_config_bodies_inspected: False")
    print("jenkins_build_parameters_inspected: False")
    print("ansible_cli_invoked: False")
    print("ssh_connections_performed: False")

    print()
    print("===== BOUNDED DECLARED RELATIONSHIP SOURCE =====")
    for key in (
        "source_mode",
        "source_status",
        "tracked_files_returned",
        "candidate_files_selected",
        "candidate_files_scanned",
        "excluded_or_unsafe_paths",
        "read_or_decode_skips",
        "oversize_skips",
        "jenkins_context_files",
        "ansible_entrypoint_signal_files",
        "explicit_relationship_signal_files",
        "relationship_source_status",
    ):
        print(f"{key}: {result[key]}")

    print()
    print("===== ANSIBLE OUTCOME BOUNDARY =====")
    print("execution_outcome_status: UNKNOWN")
    print("execution_success_status: UNKNOWN")
    print("idempotence_status: UNKNOWN")
    print("configuration_drift_status: UNKNOWN")
    print("successful_execution_claims: 0")
    print("idempotence_claims: 0")
    print("drift_claims: 0")

    print()
    print("===== INTERPRETATION BOUNDARY =====")
    print("A relationship signal requires explicit Jenkins context and an accepted Ansible execution entry point in the same bounded Git-tracked safe text file.")
    print("Generic words such as `ansible` or `jenkins` alone are not accepted relationship evidence.")
    print("NONE_OBSERVED_IN_BOUNDED_SOURCE is bounded declared-source absence only; it does not prove Jenkins cannot invoke Ansible through configuration, plugins, generated jobs, external repositories, or operator actions outside this source.")
    print("Even an explicit declared relationship signal would not by itself prove a particular Jenkins build executed Ansible or succeeded.")

    print()
    print("===== TRUST BOUNDARY =====")
    print("Only safe Git-tracked workflow/script-like text was inspected; sensitive path classes, Terraform state/tfvars, Ansible variable directories, credentials, tokens, private keys, and env files were excluded.")
    print("Raw source lines, Jenkins job names, build numbers, commands, arguments, inventory values, host targets, credentials, endpoints, console logs, job configuration bodies, build parameters, and Vault material were not printed or persisted.")
    print("No Jenkins API, Ansible CLI, SSH connection, or infrastructure mutation was performed.")

    if result["source_status"] != "COMPLETE":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
