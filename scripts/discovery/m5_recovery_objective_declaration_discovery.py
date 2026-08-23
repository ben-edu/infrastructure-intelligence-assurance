from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

INFRA_REPO = Path("/home/ben/projects/afpa-infra-rebuild")
MAX_FILE_BYTES = 512 * 1024

_ALLOWED_SUFFIXES = {
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".conf",
    ".tf",
    ".hcl",
    ".example",
    ".sample",
}

_DENY_COMPONENT_TOKENS = {
    ".env",
    "secret",
    "secrets",
    "credential",
    "credentials",
    "password",
    "passwords",
    "private",
    "privatekey",
    "private-key",
    "keys",
    "cert",
    "certs",
    "vault",
    "terraform.tfstate",
    "tfstate",
}

_RPO_TERM = re.compile(r"(?:\bRPO\b|recovery[ _-]*point[ _-]*objective)", re.IGNORECASE)
_RTO_TERM = re.compile(r"(?:\bRTO\b|recovery[ _-]*time[ _-]*objective)", re.IGNORECASE)
_SIMPLE_DURATION = re.compile(
    r"(?<![A-Za-z0-9])(?P<value>\d{1,5})\s*(?P<unit>seconds?|secs?|sec|s|minutes?|mins?|min|m|hours?|hrs?|hr|h|days?|d)(?![A-Za-z0-9])",
    re.IGNORECASE,
)
_ISO_DURATION = re.compile(
    r"(?<![A-Za-z0-9])P(?:(?P<days>\d{1,4})D)?(?:T(?:(?P<hours>\d{1,4})H)?(?:(?P<minutes>\d{1,4})M)?(?:(?P<seconds>\d{1,4})S)?)?(?![A-Za-z0-9])",
    re.IGNORECASE,
)
_SAFE_RELATIVE_PATH = re.compile(r"^[A-Za-z0-9_./@+\- ]{1,500}$")


def _run(cmd: list[str]) -> tuple[int, bytes, str | None]:
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=20, check=False)
    except Exception as exc:
        return 127, b"", type(exc).__name__
    return proc.returncode, proc.stdout, None if proc.returncode == 0 else "COMMAND_FAILED"


def _safe_repo_alias(repo: Path) -> str:
    name = repo.name.strip()
    return name if re.fullmatch(r"[A-Za-z0-9_.-]{1,120}", name) else "infra-repo"


def _component_denied(component: str) -> bool:
    lowered = component.lower()
    if lowered in _DENY_COMPONENT_TOKENS:
        return True
    return any(token in lowered for token in ("secret", "credential", "password", "private-key", "privatekey"))


def allowed_relative_path(relative: str) -> bool:
    if not relative or not _SAFE_RELATIVE_PATH.fullmatch(relative):
        return False
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        return False
    if any(_component_denied(part) for part in path.parts):
        return False

    lowered_name = path.name.lower()
    if lowered_name.endswith(".tfvars"):
        return False
    if ".tfstate" in lowered_name:
        return False
    if lowered_name.startswith(".env"):
        return False
    if lowered_name.endswith((".pem", ".key", ".p12", ".pfx", ".jks", ".kubeconfig")):
        return False

    suffixes = {suffix.lower() for suffix in path.suffixes}
    if suffixes & {".example", ".sample"}:
        return True
    return path.suffix.lower() in _ALLOWED_SUFFIXES


def _normalize_simple_duration(match: re.Match[str]) -> str:
    value = int(match.group("value"))
    unit = match.group("unit").lower()
    if unit in {"s", "sec", "secs", "second", "seconds"}:
        canonical = "s"
    elif unit in {"m", "min", "mins", "minute", "minutes"}:
        canonical = "m"
    elif unit in {"h", "hr", "hrs", "hour", "hours"}:
        canonical = "h"
    else:
        canonical = "d"
    return f"{value}{canonical}"


def _normalize_iso_duration(match: re.Match[str]) -> str | None:
    parts: list[str] = []
    for group, suffix in (("days", "d"), ("hours", "h"), ("minutes", "m"), ("seconds", "s")):
        value = match.group(group)
        if value is not None:
            parts.append(f"{int(value)}{suffix}")
    return "".join(parts) if parts else None


def _duration_near_term(line: str, term_match: re.Match[str]) -> str | None:
    start = max(0, term_match.start() - 24)
    end = min(len(line), term_match.end() + 96)
    window = line[start:end]

    simple = _SIMPLE_DURATION.search(window)
    if simple:
        return _normalize_simple_duration(simple)

    iso = _ISO_DURATION.search(window)
    if iso:
        return _normalize_iso_duration(iso)

    return None


def scan_text(relative_path: str, text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for objective, pattern in (("RPO", _RPO_TERM), ("RTO", _RTO_TERM)):
            for term in pattern.finditer(line):
                target = _duration_near_term(line, term)
                findings.append(
                    {
                        "path": relative_path,
                        "line": line_number,
                        "objective": objective,
                        "target": target,
                        "classification": (
                            "EXPLICIT_TARGET_CANDIDATE"
                            if target is not None
                            else "DECLARATION_SIGNAL_WITHOUT_SAFE_TARGET"
                        ),
                    }
                )
    return findings


def tracked_files(repo: Path) -> tuple[str, list[str]]:
    if not repo.exists() or not repo.is_dir():
        return "FAILED_TO_OBSERVE", []

    rc, stdout, _ = _run(["git", "-C", str(repo), "ls-files", "-z"])
    if rc != 0:
        return "FAILED_TO_OBSERVE", []

    rows: list[str] = []
    for raw in stdout.split(b"\0"):
        if not raw:
            continue
        try:
            relative = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if allowed_relative_path(relative):
            rows.append(relative)
    return "COMPLETE", sorted(set(rows))


def scan_repo(repo: Path) -> tuple[str, list[dict[str, Any]], int, int]:
    status, files = tracked_files(repo)
    if status != "COMPLETE":
        return status, [], 0, 0

    scanned = 0
    skipped_read = 0
    findings: list[dict[str, Any]] = []

    for relative in files:
        full_path = repo / relative
        try:
            stat = full_path.stat()
            if stat.st_size > MAX_FILE_BYTES:
                continue
            raw = full_path.read_bytes()
            text = raw.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            skipped_read += 1
            continue

        scanned += 1
        findings.extend(scan_text(relative, text))

    findings.sort(key=lambda row: (row["path"], row["line"], row["objective"], str(row["target"])))
    return status, findings, scanned, skipped_read


def main() -> int:
    print("===== M5 RECOVERY OBJECTIVE DECLARATION DISCOVERY =====")
    print()
    print("===== DECLARED-STATE SOURCE =====")
    print("repository_alias:", _safe_repo_alias(INFRA_REPO))
    print("source_mode: GIT_TRACKED_TEXT_ONLY")
    print("mutation_allowed: False")

    status, findings, scanned_files, skipped_read = scan_repo(INFRA_REPO)
    print("source_status:", status)
    print("tracked_safe_text_files_scanned:", scanned_files)
    print("read_or_decode_skips:", skipped_read)

    if status != "COMPLETE":
        print()
        print("RPO_target_status: FAILED_TO_OBSERVE")
        print("RTO_target_status: FAILED_TO_OBSERVE")
        print("No RPO/RTO evaluation is allowed.")
        print("No mutation was performed.")
        return 0

    print()
    print("===== SAFE OBJECTIVE SIGNALS =====")
    if not findings:
        print("objective_signals: NONE_OBSERVED")
    else:
        for row in findings:
            target = row["target"] if row["target"] is not None else "UNKNOWN"
            print(
                f"path={row['path']} line={row['line']} objective={row['objective']} "
                f"classification={row['classification']} target={target}"
            )

    rpo_candidates = [row for row in findings if row["objective"] == "RPO" and row["target"]]
    rto_candidates = [row for row in findings if row["objective"] == "RTO" and row["target"]]
    rpo_signals = [row for row in findings if row["objective"] == "RPO"]
    rto_signals = [row for row in findings if row["objective"] == "RTO"]

    print()
    print("===== SUMMARY =====")
    print("rpo_declaration_signals:", len(rpo_signals))
    print("rpo_explicit_target_candidates:", len(rpo_candidates))
    print("rto_declaration_signals:", len(rto_signals))
    print("rto_explicit_target_candidates:", len(rto_candidates))
    print("rpo_compliance_claims: 0")
    print("rto_compliance_claims: 0")
    print("rpo_violation_claims: 0")

    print()
    print("===== INTERPRETATION BOUNDARY =====")
    print(
        "An EXPLICIT_TARGET_CANDIDATE is only a safe file-level declaration signal. "
        "It is not accepted as an authoritative asset/service RPO or RTO until scope, ownership, and source authority are validated."
    )
    print(
        "No backup timestamp, recovery point, task result, or restore duration is evaluated against a candidate target in this discovery."
    )
    print(
        "No signal in this bounded Git-tracked source means the RPO/RTO target remains UNKNOWN; it is not proof that no objective exists elsewhere."
    )

    print()
    print("===== TRUST BOUNDARY =====")
    print("Only Git-tracked bounded text files from the declared infrastructure repository were scanned.")
    print("Raw matching lines were not printed or persisted.")
    print(
        "Files/paths associated with env, secrets, credentials, passwords, private keys, certificates, Terraform state, and real tfvars were excluded."
    )
    print("No infrastructure, database, backup, or repository state was changed.")
    print("No mutation was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
