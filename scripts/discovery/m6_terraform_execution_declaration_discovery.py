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
    r"(?:^|[-_.])(secret|secrets|credential|credentials|password|passwd|private[-_]?key|token|terraform\.tfstate|tfstate)(?:$|[-_.])",
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

PHASES = ("init", "validate", "plan", "apply", "destroy", "refresh", "import")
_PHASE_RE = re.compile(
    r"\bterraform\s+(init|validate|plan|apply|destroy|refresh|import)\b",
    re.IGNORECASE,
)
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
    if any(_SENSITIVE_PATH_TOKEN.search(part) for part in path.parts):
        return None
    if path.suffix.lower() == ".tfvars" or ".tfvars." in path.name.lower():
        return None
    if path.name in KNOWN_BASENAMES or path.suffix.lower() in SAFE_SUFFIXES:
        return path.as_posix()
    return None


def _active_lines(text: str) -> list[str]:
    """Return non-empty, non-full-line-comment lines for token classification.

    Lines are retained only in memory. They are never returned from discovery or printed.
    This is intentionally a bounded lexical signal detector, not a shell/YAML/Groovy parser.
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
    phases: Counter[str] = Counter()
    gate_signal = False
    for line in _active_lines(text):
        for match in _PHASE_RE.finditer(line):
            phase = match.group(1).lower()
            if phase in PHASES:
                phases[phase] += 1
        if _GATE_RE.search(line):
            gate_signal = True
    return phases, gate_signal


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
        "phase_file_counts": Counter(),
        "phase_signal_counts": Counter(),
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

        phases, gate_signal = _classify_text(text)
        result["candidate_files_scanned"] += 1

        # Gate/approval vocabulary alone is not Terraform evidence. Gate metadata is
        # retained only when the same file also contains at least one explicit
        # Terraform phase token.
        if not phases:
            continue

        phase_names = sorted(phases)
        for phase, count in phases.items():
            result["phase_file_counts"][phase] += 1
            result["phase_signal_counts"][phase] += count
        if gate_signal:
            result["files_with_gate_signal"] += 1

        result["files"].append(
            {
                "path": safe_path,
                "terraform_phase_signals": phase_names,
                "gate_signal": bool(gate_signal),
            }
        )

    if result["read_or_decode_skips"] or result["oversize_skips"]:
        result["source_status"] = "INCOMPLETE"
    result["files"].sort(key=lambda row: row["path"])
    return result


def _format_phase_counts(counter: Counter[str]) -> str:
    values = [f"{phase}={counter.get(phase, 0)}" for phase in PHASES if counter.get(phase, 0)]
    return ",".join(values) if values else "NONE_OBSERVED"


def main() -> int:
    print("===== M6 TERRAFORM EXECUTION DECLARATION DISCOVERY =====")
    print()
    print("===== DECLARED EXECUTION SOURCE =====")
    print("repository_alias: afpa-infra-rebuild")
    print("source_mode: GIT_TRACKED_SAFE_WORKFLOW_SCRIPT_TEXT_ONLY")
    print("mutation_allowed: False")
    print("terraform_cli_invoked: False")
    print("jenkins_invoked: False")
    print("github_actions_invoked: False")
    print("provider_live_verification_performed: False")
    print("terraform_state_inspected: False")
    print("terraform_tfvars_inspected: False")

    result = discover()
    print("source_status:", result["source_status"])
    print("tracked_files_returned:", result["tracked_files_returned"])
    print("candidate_files_selected:", result["candidate_files_selected"])
    print("candidate_files_scanned:", result["candidate_files_scanned"])
    print("read_or_decode_skips:", result["read_or_decode_skips"])
    print("oversize_skips:", result["oversize_skips"])

    if result["source_status"] != "COMPLETE":
        print("execution_declaration_status: FAILED_TO_OBSERVE")
        print("No execution-declaration conclusion is allowed.")
        print("No mutation was performed.")
        return 2

    print()
    print("===== SAFE EXECUTION DECLARATION SIGNALS =====")
    if not result["files"]:
        print("terraform_execution_signal_files: NONE_OBSERVED")
    for row in result["files"]:
        phases = ",".join(row["terraform_phase_signals"])
        print(
            f"path={row['path']}"
            f" terraform_phase_signals={phases}"
            f" gate_signal={row['gate_signal']}"
        )

    print()
    print("===== SUMMARY =====")
    print("terraform_signal_files:", len(result["files"]))
    print("phase_file_counts:", _format_phase_counts(result["phase_file_counts"]))
    print("phase_signal_counts:", _format_phase_counts(result["phase_signal_counts"]))
    print("files_with_gate_signal:", result["files_with_gate_signal"])

    for phase in PHASES:
        count = result["phase_file_counts"].get(phase, 0)
        status = "DECLARATION_SIGNAL_OBSERVED" if count else "NONE_OBSERVED_IN_BOUNDED_SOURCE"
        print(f"{phase}_declaration_status: {status}")

    print("execution_outcome_status: UNKNOWN")
    print("plan_result_status: UNKNOWN")
    print("apply_result_status: UNKNOWN")
    print("drift_status: UNKNOWN")
    print("destructive_change_status: UNKNOWN")
    print("successful_execution_claims: 0")
    print("drift_claims: 0")
    print("destructive_change_claims: 0")

    print()
    print("===== INTERPRETATION BOUNDARY =====")
    print("Terraform phase tokens in Git-tracked workflow/script text are declared execution signals only, not evidence that any command executed or succeeded.")
    print("Gate keywords are considered only inside files that also contain an explicit Terraform phase token; they do not prove that a gate protects a particular apply step.")
    print("Gate-only files are excluded from Terraform execution evidence.")
    print("NONE_OBSERVED_IN_BOUNDED_SOURCE is bounded negative evidence only, not proof that the phase is never executed elsewhere.")
    print("No plan output, apply output, state, provider result, drift result, or destructive-change result is inferred.")

    print()
    print("===== TRUST BOUNDARY =====")
    print("Only bounded Git-tracked workflow/script text files were read.")
    print("Raw command lines, command arguments, environment values, credentials, endpoints, module/resource names, and connection strings were not printed or persisted.")
    print("Terraform state/state backups, real tfvars, .env files, secrets, credentials, private keys, certificates, and provider tokens/passwords were excluded.")
    print("Terraform, Jenkins, GitHub Actions, and provider APIs were not invoked. No repository or infrastructure mutation was performed by the discovery.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
