from __future__ import annotations

import re
import subprocess
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

SOURCE_REPO = Path("/home/ben/projects/afpa-infra-rebuild")
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TRACKED_FILES = 10000

_SAFE_PATH = re.compile(r"^[A-Za-z0-9_./+@:-]{1,500}$")
_SENSITIVE_PATH_TOKEN = re.compile(
    r"(?:^|[-_.])(secret|secrets|credential|credentials|password|passwd|private[-_]?key|token|vault[-_]?pass|terraform\.tfstate|tfstate)(?:$|[-_.])",
    re.IGNORECASE,
)

KNOWN_BASENAMES = {
    "Jenkinsfile",
    "Makefile",
    "Taskfile.yml",
    "Taskfile.yaml",
    ".gitlab-ci.yml",
    ".gitlab-ci.yaml",
}
SAFE_SUFFIXES = {".sh", ".bash", ".zsh", ".py", ".yml", ".yaml", ".groovy", ".mk"}

ENTRYPOINTS = (
    "ansible_playbook",
    "ansible_runner_run",
    "ansible_navigator_run",
)

_ENTRYPOINT_PATTERNS = {
    "ansible_playbook": re.compile(r"\bansible-playbook\b", re.IGNORECASE),
    "ansible_runner_run": re.compile(r"\bansible-runner\s+run\b", re.IGNORECASE),
    "ansible_navigator_run": re.compile(r"\bansible-navigator\s+run\b", re.IGNORECASE),
}

_GATE_RE = re.compile(
    r"\b(approval|approve|manual|input|confirmation|confirm)\b|\bwhen\s*:\s*manual\b",
    re.IGNORECASE,
)


def _run_git_ls_files(repo: Path) -> tuple[str, list[str]]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "ls-files"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except Exception:
        return "FAILED_TO_OBSERVE", []
    if proc.returncode != 0:
        return "FAILED_TO_OBSERVE", []
    rows = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if len(rows) > MAX_TRACKED_FILES:
        return "FAILED_TO_OBSERVE", []
    return "COMPLETE", rows


def _safe_candidate_path(value: str) -> str | None:
    if not _SAFE_PATH.fullmatch(value):
        return None
    try:
        path = PurePosixPath(value)
    except Exception:
        return None
    if path.is_absolute() or ".." in path.parts:
        return None

    lowered_parts = [part.lower() for part in path.parts]
    if ".terraform" in lowered_parts:
        return None
    if any(part in {"group_vars", "host_vars"} for part in lowered_parts):
        return None
    if any(_SENSITIVE_PATH_TOKEN.search(part) for part in path.parts):
        return None
    if path.name.lower() == ".env" or path.suffix.lower() == ".tfvars" or ".tfvars." in path.name.lower():
        return None

    if path.name in KNOWN_BASENAMES or path.suffix.lower() in SAFE_SUFFIXES:
        return path.as_posix()
    return None


def _active_lines(text: str) -> list[str]:
    """Return non-empty, non-full-line-comment lines for bounded lexical classification.

    Lines are retained only in memory and are never projected or persisted.
    This is intentionally not a shell/YAML/Groovy/Python parser.
    """
    active: list[str] = []
    in_block_comment = False
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if in_block_comment:
            if "*/" in stripped:
                in_block_comment = False
            continue
        if stripped.startswith("/*"):
            if "*/" not in stripped[2:]:
                in_block_comment = True
            continue
        if stripped.startswith(("#", "//", ";", "*")):
            continue
        active.append(raw)
    return active


def _classify_text(text: str) -> tuple[Counter[str], bool]:
    entrypoints: Counter[str] = Counter()
    gate_signal = False

    for line in _active_lines(text):
        for name, pattern in _ENTRYPOINT_PATTERNS.items():
            matches = list(pattern.finditer(line))
            if matches:
                entrypoints[name] += len(matches)
        if _GATE_RE.search(line):
            gate_signal = True

    return entrypoints, gate_signal


def discover(repo: Path = SOURCE_REPO) -> dict[str, Any]:
    source_status, tracked = _run_git_ls_files(repo)
    result: dict[str, Any] = {
        "source_status": source_status,
        "tracked_files_returned": len(tracked),
        "candidate_files_selected": 0,
        "candidate_files_scanned": 0,
        "excluded_or_noncandidate_paths": 0,
        "read_or_decode_skips": 0,
        "oversize_skips": 0,
        "files": [],
        "entrypoint_file_counts": Counter(),
        "entrypoint_signal_counts": Counter(),
        "files_with_gate_signal": 0,
    }
    if source_status != "COMPLETE":
        return result

    for raw_path in tracked:
        safe_path = _safe_candidate_path(raw_path)
        if safe_path is None:
            result["excluded_or_noncandidate_paths"] += 1
            continue

        result["candidate_files_selected"] += 1
        path = repo / safe_path
        try:
            size = path.stat().st_size
        except OSError:
            result["read_or_decode_skips"] += 1
            continue
        if size > MAX_FILE_BYTES:
            result["oversize_skips"] += 1
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            result["read_or_decode_skips"] += 1
            continue

        entrypoints, gate_signal = _classify_text(text)
        result["candidate_files_scanned"] += 1

        # Approval/gate vocabulary alone is not Ansible execution evidence.
        # Gate metadata is retained only for a file with an explicit accepted
        # Ansible execution entry point.
        if not entrypoints:
            continue

        names = sorted(entrypoints)
        for name, count in entrypoints.items():
            result["entrypoint_file_counts"][name] += 1
            result["entrypoint_signal_counts"][name] += count
        if gate_signal:
            result["files_with_gate_signal"] += 1

        result["files"].append(
            {
                "path": safe_path,
                "ansible_execution_entrypoints": names,
                "gate_signal": bool(gate_signal),
            }
        )

    if result["read_or_decode_skips"] or result["oversize_skips"]:
        result["source_status"] = "INCOMPLETE"
    result["files"].sort(key=lambda row: row["path"])
    return result


def _format_counts(counter: Counter[str]) -> str:
    values = [f"{name}={counter.get(name, 0)}" for name in ENTRYPOINTS if counter.get(name, 0)]
    return ",".join(values) if values else "NONE_OBSERVED"


def main() -> int:
    print("===== M6 ANSIBLE EXECUTION DECLARATION DISCOVERY =====")
    print()
    print("===== DECLARED EXECUTION SOURCE =====")
    print("repository_alias: afpa-infra-rebuild")
    print("source_mode: GIT_TRACKED_SAFE_WORKFLOW_SCRIPT_TEXT_ONLY")
    print("mutation_allowed: False")
    print("ansible_cli_invoked: False")
    print("ssh_connections_performed: False")
    print("jenkins_invoked: False")
    print("github_actions_invoked: False")
    print("runtime_facts_inspected: False")
    print("ansible_vault_contents_inspected: False")

    result = discover()
    print("source_status:", result["source_status"])
    print("tracked_files_returned:", result["tracked_files_returned"])
    print("candidate_files_selected:", result["candidate_files_selected"])
    print("candidate_files_scanned:", result["candidate_files_scanned"])
    print("read_or_decode_skips:", result["read_or_decode_skips"])
    print("oversize_skips:", result["oversize_skips"])

    if result["source_status"] != "COMPLETE":
        print("execution_declaration_status: FAILED_TO_OBSERVE")
        print("No Ansible execution-declaration conclusion is allowed.")
        print("No mutation was performed.")
        return 2

    print()
    print("===== SAFE ANSIBLE EXECUTION DECLARATION SIGNALS =====")
    if not result["files"]:
        print("ansible_execution_signal_files: NONE_OBSERVED")
    for row in result["files"]:
        entrypoints = ",".join(row["ansible_execution_entrypoints"])
        print(
            f"path={row['path']}"
            f" ansible_execution_entrypoints={entrypoints}"
            f" gate_signal={row['gate_signal']}"
        )

    print()
    print("===== SUMMARY =====")
    print("ansible_execution_signal_files:", len(result["files"]))
    print("entrypoint_file_counts:", _format_counts(result["entrypoint_file_counts"]))
    print("entrypoint_signal_counts:", _format_counts(result["entrypoint_signal_counts"]))
    print("files_with_gate_signal:", result["files_with_gate_signal"])

    for name in ENTRYPOINTS:
        count = result["entrypoint_file_counts"].get(name, 0)
        status = "DECLARATION_SIGNAL_OBSERVED" if count else "NONE_OBSERVED_IN_BOUNDED_SOURCE"
        print(f"{name}_declaration_status: {status}")

    print("execution_outcome_status: UNKNOWN")
    print("execution_success_status: UNKNOWN")
    print("idempotence_status: UNKNOWN")
    print("live_managed_host_coverage_status: UNKNOWN")
    print("configuration_drift_status: UNKNOWN")
    print("successful_execution_claims: 0")
    print("idempotence_claims: 0")
    print("drift_claims: 0")

    print()
    print("===== INTERPRETATION BOUNDARY =====")
    print("Accepted Ansible execution entry-point tokens in Git-tracked workflow/script text are declaration signals only, not evidence that any command executed or succeeded.")
    print("The generic `ansible` command and tooling such as ansible-lint are intentionally not classified as execution entry points in this slice.")
    print("Gate keywords are considered only inside files that also contain an accepted Ansible execution entry point; gate-only files are excluded from Ansible execution evidence.")
    print("NONE_OBSERVED_IN_BOUNDED_SOURCE is bounded negative evidence only, not proof that Ansible is never executed manually or from another source.")
    print("No execution result, host reachability, runtime fact, idempotence result, or drift result is inferred.")

    print()
    print("===== TRUST BOUNDARY =====")
    print("Only bounded Git-tracked workflow/script text files were read.")
    print("Raw command lines, command arguments, playbook arguments, inventory arguments, environment values, credentials, endpoints, host targets, and connection strings were not printed or persisted.")
    print("group_vars/host_vars, .env, secrets, credentials, private keys, Vault password material, tokens, and Terraform state/tfvars paths were excluded from this source selection where applicable.")
    print("Ansible, ansible-playbook, ansible-runner, ansible-navigator, Jenkins, GitHub Actions, and SSH were not invoked. No repository or infrastructure mutation was performed by the discovery.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
