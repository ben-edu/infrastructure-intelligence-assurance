from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

INFRA_REPO = Path("/home/ben/projects/afpa-infra-rebuild")
JENKINS_ROOT_CANDIDATES = (
    INFRA_REPO / "mcp" / "jenkins-readonly",
    INFRA_REPO / "mcp" / "jenkins",
)
CRON_DIRS = (
    Path("/etc/cron.d"),
    Path("/etc/cron.hourly"),
    Path("/etc/cron.daily"),
    Path("/etc/cron.weekly"),
    Path("/etc/cron.monthly"),
)
SAFE_NAME = re.compile(r"^[A-Za-z0-9_.:@+\-]{1,200}$")
ANSIBLE_NAME = re.compile(r"ansible", re.IGNORECASE)


def _safe_name(value: str) -> str | None:
    value = value.strip()
    return value if SAFE_NAME.fullmatch(value) else None


def _run_text(cmd: list[str]) -> tuple[str, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
    except Exception:
        return "FAILED_TO_OBSERVE", ""
    if proc.returncode != 0:
        return "FAILED_TO_OBSERVE", ""
    return "COMPLETE", proc.stdout


def inspect_jenkins_candidate_roots(roots: tuple[Path, ...] = JENKINS_ROOT_CANDIDATES) -> dict[str, Any]:
    """Inspect Jenkins candidate locations using filesystem metadata only.

    File contents are never opened. In particular, .env/token/password material is
    not read. The result intentionally exposes counts and coarse classifications only.
    """
    directories_observed = 0
    files_observed = 0
    env_like_files_observed = 0
    metadata_failures = 0

    for root in roots:
        try:
            if not root.is_dir():
                continue
            directories_observed += 1
            entries = list(root.iterdir())
        except OSError:
            metadata_failures += 1
            continue

        for entry in entries:
            try:
                if not entry.is_file():
                    continue
            except OSError:
                metadata_failures += 1
                continue
            files_observed += 1
            lowered = entry.name.lower()
            if lowered == ".env" or lowered.endswith(".env") or lowered.endswith(".env.example"):
                env_like_files_observed += 1

    if metadata_failures:
        status = "INCOMPLETE"
    elif directories_observed:
        status = "CONFIG_CANDIDATE_OBSERVED"
    else:
        status = "NONE_OBSERVED_IN_BOUNDED_PATHS"

    return {
        "status": status,
        "candidate_directories_observed": directories_observed,
        "candidate_files_observed": files_observed,
        "env_like_files_observed": env_like_files_observed,
        "metadata_failures": metadata_failures,
        "credential_values_inspected": False,
        "jenkins_api_invoked": False,
    }


def _ansible_units_from_unit_files(text: str) -> list[str]:
    units: list[str] = []
    for raw in text.splitlines():
        parts = raw.split()
        if not parts:
            continue
        unit = _safe_name(parts[0])
        if unit and ANSIBLE_NAME.search(unit):
            units.append(unit)
    return sorted(set(units))


def _ansible_timers_from_timer_list(text: str) -> list[str]:
    timers: list[str] = []
    for raw in text.splitlines():
        for token in raw.split():
            unit = _safe_name(token)
            if unit and unit.endswith(".timer") and ANSIBLE_NAME.search(unit):
                timers.append(unit)
    return sorted(set(timers))


def inspect_management_scheduler_metadata() -> dict[str, Any]:
    unit_status, unit_text = _run_text(["systemctl", "list-unit-files", "--no-legend", "--no-pager"])
    timer_status, timer_text = _run_text(["systemctl", "list-timers", "--all", "--no-legend", "--no-pager"])

    units = _ansible_units_from_unit_files(unit_text) if unit_status == "COMPLETE" else []
    timers = _ansible_timers_from_timer_list(timer_text) if timer_status == "COMPLETE" else []

    cron_names: list[str] = []
    cron_metadata_failures = 0
    for directory in CRON_DIRS:
        try:
            entries = list(directory.iterdir()) if directory.exists() else []
        except OSError:
            cron_metadata_failures += 1
            continue
        for entry in entries:
            name = _safe_name(entry.name)
            if name and ANSIBLE_NAME.search(name):
                cron_names.append(f"{directory.name}/{name}")

    if unit_status != "COMPLETE" or timer_status != "COMPLETE" or cron_metadata_failures:
        source_status = "INCOMPLETE"
    else:
        source_status = "COMPLETE"

    explicit_signals = sorted(set(units + timers + cron_names))
    return {
        "source_status": source_status,
        "unit_file_status": unit_status,
        "timer_status": timer_status,
        "ansible_unit_names": units,
        "ansible_timer_names": timers,
        "ansible_cron_names": sorted(set(cron_names)),
        "cron_metadata_failures": cron_metadata_failures,
        "explicit_scheduler_signal_count": len(explicit_signals),
    }


def choose_preferred_source(jenkins: dict[str, Any], scheduler: dict[str, Any]) -> str:
    if jenkins.get("status") == "CONFIG_CANDIDATE_OBSERVED":
        return "JENKINS_READ_ONLY_SOURCE_CANDIDATE"
    if scheduler.get("explicit_scheduler_signal_count", 0) > 0:
        return "MANAGEMENT_HOST_SCHEDULER_SOURCE_CANDIDATE"
    if jenkins.get("status") == "INCOMPLETE" or scheduler.get("source_status") == "INCOMPLETE":
        return "SOURCE_DISCOVERY_INCOMPLETE"
    return "NO_AUTHORITATIVE_OUTCOME_SOURCE_OBSERVED_IN_BOUNDED_DISCOVERY"


def discover() -> dict[str, Any]:
    jenkins = inspect_jenkins_candidate_roots()
    scheduler = inspect_management_scheduler_metadata()
    preferred = choose_preferred_source(jenkins, scheduler)
    return {
        "jenkins": jenkins,
        "scheduler": scheduler,
        "preferred_source_candidate": preferred,
        "execution_outcome_status": "UNKNOWN",
        "execution_success_status": "UNKNOWN",
        "idempotence_status": "UNKNOWN",
        "configuration_drift_status": "UNKNOWN",
        "successful_execution_claims": 0,
        "idempotence_claims": 0,
        "drift_claims": 0,
    }


def main() -> int:
    print("===== M6 ANSIBLE EXECUTION-OUTCOME SOURCE DISCOVERY =====")
    print()
    print("===== SAFETY =====")
    print("mutation_allowed: False")
    print("ansible_cli_invoked: False")
    print("ssh_connections_performed: False")
    print("jenkins_api_invoked: False")
    print("jenkins_credentials_inspected: False")
    print("jenkins_console_logs_inspected: False")
    print("scheduler_command_bodies_inspected: False")
    print("cron_contents_inspected: False")

    result = discover()
    jenkins = result["jenkins"]
    scheduler = result["scheduler"]

    print()
    print("===== JENKINS READ-ONLY SOURCE CAPABILITY =====")
    print("jenkins_source_candidate_status:", jenkins["status"])
    print("candidate_directories_observed:", jenkins["candidate_directories_observed"])
    print("candidate_files_observed:", jenkins["candidate_files_observed"])
    print("env_like_files_observed:", jenkins["env_like_files_observed"])
    print("metadata_failures:", jenkins["metadata_failures"])
    print("credential_values_inspected: False")
    print("jenkins_api_invoked: False")

    print()
    print("===== MANAGEMENT-HOST SCHEDULER METADATA =====")
    print("source_status:", scheduler["source_status"])
    print("unit_file_status:", scheduler["unit_file_status"])
    print("timer_status:", scheduler["timer_status"])
    print("ansible_unit_names:", ",".join(scheduler["ansible_unit_names"]) or "NONE_OBSERVED")
    print("ansible_timer_names:", ",".join(scheduler["ansible_timer_names"]) or "NONE_OBSERVED")
    print("ansible_cron_names:", ",".join(scheduler["ansible_cron_names"]) or "NONE_OBSERVED")
    print("cron_metadata_failures:", scheduler["cron_metadata_failures"])
    print("explicit_scheduler_signal_count:", scheduler["explicit_scheduler_signal_count"])

    print()
    print("===== SOURCE SELECTION =====")
    print("preferred_source_candidate:", result["preferred_source_candidate"])
    print("execution_outcome_status: UNKNOWN")
    print("execution_success_status: UNKNOWN")
    print("idempotence_status: UNKNOWN")
    print("configuration_drift_status: UNKNOWN")
    print("successful_execution_claims: 0")
    print("idempotence_claims: 0")
    print("drift_claims: 0")

    print()
    print("===== INTERPRETATION BOUNDARY =====")
    print("A Jenkins configuration candidate only indicates that a bounded read-only Jenkins integration location exists; it does not prove that Jenkins orchestrates Ansible or that any build ran.")
    print("Systemd/timer/cron name matches are scheduler metadata only. They do not establish command content, execution history, success, idempotence, host reachability, or drift.")
    print("NO_AUTHORITATIVE_OUTCOME_SOURCE_OBSERVED_IN_BOUNDED_DISCOVERY is bounded absence only and does not rule out manual or external execution sources.")

    print()
    print("===== TRUST BOUNDARY =====")
    print("Jenkins candidate files were inspected by filesystem metadata only; file contents and credential values were not read.")
    print("Only systemd unit/timer names and cron filenames with explicit Ansible naming were projected; unit bodies, timer command bodies, cron contents, journals, console logs, and raw commands were not read.")
    print("No Jenkins API, Ansible CLI, SSH connection, scheduler mutation, or infrastructure mutation was performed.")

    if jenkins["status"] == "INCOMPLETE" or scheduler["source_status"] == "INCOMPLETE":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
