from __future__ import annotations

import re
from pathlib import Path
from typing import Any

INFRA_REPO = Path("/home/ben/projects/afpa-infra-rebuild")
JENKINS_ROOT_CANDIDATES = (
    INFRA_REPO / "mcp" / "jenkins-readonly",
    INFRA_REPO / "mcp" / "jenkins",
)

MAX_SOURCE_BYTES = 512 * 1024
SOURCE_SUFFIXES = {".py", ".js", ".mjs", ".cjs", ".ts"}
SENSITIVE_NAME_RE = re.compile(
    r"(?:^|[-_.])(env|secret|secrets|credential|credentials|password|passwd|token|private[-_]?key)(?:$|[-_.])",
    re.IGNORECASE,
)
IDENTIFIER_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]{1,120}\b")

JOB_METADATA_IDENTIFIERS = {
    "list_jobs",
    "get_jobs",
    "list_jenkins_jobs",
    "job_info",
    "get_job",
    "job_status",
}
BUILD_METADATA_IDENTIFIERS = {
    "list_builds",
    "get_build",
    "get_build_info",
    "build_info",
    "build_status",
    "recent_builds",
    "last_build",
}
CONSOLE_IDENTIFIERS = {
    "consoletext",
    "console_output",
    "console_log",
    "get_console",
    "get_console_log",
}
CONFIG_BODY_IDENTIFIERS = {
    "config_xml",
    "get_config_xml",
    "job_config",
    "get_job_config",
}


def _is_sensitive_name(name: str) -> bool:
    lowered = name.lower()
    if lowered == ".env" or lowered.endswith(".env") or lowered.endswith(".env.example"):
        return True
    return bool(SENSITIVE_NAME_RE.search(name))


def _classify_identifiers(text: str) -> dict[str, bool]:
    identifiers = {token.lower() for token in IDENTIFIER_RE.findall(text)}
    return {
        "job_metadata_signal": bool(identifiers & JOB_METADATA_IDENTIFIERS),
        "build_metadata_signal": bool(identifiers & BUILD_METADATA_IDENTIFIERS),
        "console_capability_signal": bool(identifiers & CONSOLE_IDENTIFIERS),
        "config_body_capability_signal": bool(identifiers & CONFIG_BODY_IDENTIFIERS),
    }


def inspect_integration_source(
    roots: tuple[Path, ...] = JENKINS_ROOT_CANDIDATES,
) -> dict[str, Any]:
    roots_observed = 0
    files_seen = 0
    source_files_scanned = 0
    sensitive_files_excluded = 0
    unsupported_files_excluded = 0
    read_failures = 0
    oversize_skips = 0

    job_signal_files = 0
    build_signal_files = 0
    console_signal_files = 0
    config_body_signal_files = 0

    for root in roots:
        try:
            if not root.is_dir():
                continue
            roots_observed += 1
            entries = list(root.iterdir())
        except OSError:
            read_failures += 1
            continue

        for entry in entries:
            try:
                if not entry.is_file():
                    continue
            except OSError:
                read_failures += 1
                continue

            files_seen += 1
            if _is_sensitive_name(entry.name):
                sensitive_files_excluded += 1
                continue
            if entry.suffix.lower() not in SOURCE_SUFFIXES:
                unsupported_files_excluded += 1
                continue

            try:
                size = entry.stat().st_size
            except OSError:
                read_failures += 1
                continue
            if size > MAX_SOURCE_BYTES:
                oversize_skips += 1
                continue

            try:
                text = entry.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                read_failures += 1
                continue

            source_files_scanned += 1
            signals = _classify_identifiers(text)
            job_signal_files += int(signals["job_metadata_signal"])
            build_signal_files += int(signals["build_metadata_signal"])
            console_signal_files += int(signals["console_capability_signal"])
            config_body_signal_files += int(signals["config_body_capability_signal"])

    if read_failures or oversize_skips:
        source_status = "INCOMPLETE"
    elif not roots_observed:
        source_status = "NO_INTEGRATION_SOURCE_OBSERVED"
    else:
        source_status = "COMPLETE"

    if source_status == "INCOMPLETE":
        capability_status = "SOURCE_INCOMPLETE"
    elif source_status == "NO_INTEGRATION_SOURCE_OBSERVED":
        capability_status = "NO_INTEGRATION_SOURCE_OBSERVED"
    elif job_signal_files and build_signal_files:
        capability_status = "JOB_AND_BUILD_METADATA_CAPABILITY_SIGNAL_OBSERVED"
    elif job_signal_files or build_signal_files:
        capability_status = "PARTIAL_METADATA_CAPABILITY_SIGNAL_OBSERVED"
    else:
        capability_status = "NONE_OBSERVED_IN_BOUNDED_INTEGRATION_SOURCE"

    return {
        "source_status": source_status,
        "capability_status": capability_status,
        "roots_observed": roots_observed,
        "files_seen": files_seen,
        "source_files_scanned": source_files_scanned,
        "sensitive_files_excluded": sensitive_files_excluded,
        "unsupported_files_excluded": unsupported_files_excluded,
        "read_failures": read_failures,
        "oversize_skips": oversize_skips,
        "job_metadata_signal_files": job_signal_files,
        "build_metadata_signal_files": build_signal_files,
        "console_capability_signal_files": console_signal_files,
        "config_body_capability_signal_files": config_body_signal_files,
        "jenkins_api_invoked": False,
        "console_logs_inspected": False,
        "job_config_bodies_inspected": False,
        "credential_values_inspected": False,
        "environment_values_inspected": False,
    }


def main() -> int:
    print("===== M6 JENKINS READ-ONLY ANSIBLE OUTCOME CAPABILITY PROBE =====")
    print()
    print("===== SAFETY =====")
    print("mutation_allowed: False")
    print("jenkins_api_invoked: False")
    print("jenkins_console_logs_inspected: False")
    print("jenkins_job_config_bodies_inspected: False")
    print("jenkins_credentials_inspected: False")
    print("jenkins_environment_values_inspected: False")
    print("ansible_cli_invoked: False")
    print("ssh_connections_performed: False")

    result = inspect_integration_source()

    print()
    print("===== BOUNDED JENKINS INTEGRATION SOURCE =====")
    print("source_status:", result["source_status"])
    print("roots_observed:", result["roots_observed"])
    print("files_seen:", result["files_seen"])
    print("source_files_scanned:", result["source_files_scanned"])
    print("sensitive_files_excluded:", result["sensitive_files_excluded"])
    print("unsupported_files_excluded:", result["unsupported_files_excluded"])
    print("read_failures:", result["read_failures"])
    print("oversize_skips:", result["oversize_skips"])

    print()
    print("===== SAFE CAPABILITY SIGNALS =====")
    print("job_metadata_signal_files:", result["job_metadata_signal_files"])
    print("build_metadata_signal_files:", result["build_metadata_signal_files"])
    print("console_capability_signal_files:", result["console_capability_signal_files"])
    print("config_body_capability_signal_files:", result["config_body_capability_signal_files"])
    print("safe_metadata_capability_status:", result["capability_status"])

    print()
    print("===== OUTCOME BOUNDARY =====")
    print("execution_outcome_status: UNKNOWN")
    print("execution_success_status: UNKNOWN")
    print("idempotence_status: UNKNOWN")
    print("configuration_drift_status: UNKNOWN")
    print("successful_execution_claims: 0")
    print("idempotence_claims: 0")
    print("drift_claims: 0")

    print()
    print("===== INTERPRETATION BOUNDARY =====")
    print("Identifier-level signals in the bounded Jenkins integration source indicate only apparent integration capability; they do not prove that Jenkins currently exposes, invokes, or has used that capability.")
    print("Job/build metadata capability signals are not job/build outcome evidence.")
    print("Console/config capability signals, if observed, are recorded only to keep them explicitly outside the permitted evidence path; their contents are not accessed.")
    print("No execution success, Ansible orchestration, host reachability, idempotence, or drift result is inferred.")

    print()
    print("===== TRUST BOUNDARY =====")
    print("Only non-sensitive bounded integration source-code files were read for identifier classification.")
    print(".env and secret/credential/password/token/private-key-like files were excluded before content reads.")
    print("Raw source lines, URLs, endpoints, command arguments, environment values, credentials, console logs, job configuration bodies, build parameters, inventory arguments, and host targets were not printed or persisted.")
    print("No Jenkins API, Ansible CLI, SSH connection, or infrastructure mutation was performed.")

    if result["source_status"] == "INCOMPLETE":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
