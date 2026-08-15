from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from .io_utils import atomic_write_json

OBSERVER_VERSION = "0.2.0"
SOURCE_STATUS_VERSION = "0.1"
DEFAULT_TTL_SECONDS = 900
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_KUSTOMIZE_TIMEOUT_SECONDS = 60
DEFAULT_MAX_MANIFEST_BYTES = 2 * 1024 * 1024

SUPPORTED_KINDS = {
    "Namespace",
    "Deployment",
    "StatefulSet",
    "DaemonSet",
    "Service",
    "Ingress",
    "PersistentVolumeClaim",
}
SKIPPED_SENSITIVE_KINDS = {"Secret", "ConfigMap"}
NAMESPACED_KINDS = SUPPORTED_KINDS - {"Namespace"}

Runner = Callable[..., subprocess.CompletedProcess[str]]

_DOCUMENT_SEPARATOR = re.compile(r"(?m)^[ \t]*---[ \t]*(?:#.*)?$")
_TOP_LEVEL_KIND = re.compile(r"(?m)^kind:[ \t]*[\"']?([A-Za-z0-9_.-]+)[\"']?[ \t]*(?:#.*)?$")


def _rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _api_group(api_version: str) -> str:
    return api_version.split("/", 1)[0] if "/" in api_version else ""


def _subject_key(subject: dict[str, Any]) -> tuple[Any, ...]:
    return (
        subject["system"],
        subject["cluster"],
        subject.get("api_group", ""),
        subject["kind"],
        subject.get("namespace"),
        subject["name"],
    )


def _split_documents(text: str) -> list[str]:
    return [part.strip() for part in _DOCUMENT_SEPARATOR.split(text) if part.strip()]


def _kind_from_text(document: str) -> str | None:
    match = _TOP_LEVEL_KIND.search(document)
    return match.group(1) if match else None


def _run(
    command: list[str],
    *,
    runner: Runner = subprocess.run,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess[str]:
    return runner(
        command,
        capture_output=True,
        text=True,
        input=input_text,
        timeout=timeout,
        check=False,
        env=env,
    )


def _local_kubectl_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("KUBECONFIG", None)
    env.pop("KUBERNETES_MASTER", None)
    env["KUBECTL_KUBERC"] = "false"
    return env


def _classify_git_failure(stderr: str) -> tuple[str, str]:
    lowered = stderr.lower()
    if "permission denied (publickey)" in lowered or "could not read from remote repository" in lowered:
        return "GIT_AUTH_FAILED", "Git source authentication failed."
    if "host key verification failed" in lowered:
        return "GIT_HOST_VERIFICATION_FAILED", "Git SSH host verification failed."
    if "could not resolve hostname" in lowered or "connection timed out" in lowered or "connection refused" in lowered:
        return "GIT_UNREACHABLE", "Git source could not be reached."
    return "GIT_FETCH_FAILED", "Git source refresh failed."


def _git_env(source: dict[str, Any]) -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_SSH_COMMAND"] = (
        "ssh -o BatchMode=yes -o IdentitiesOnly=yes "
        "-o StrictHostKeyChecking=yes "
        f"-o UserKnownHostsFile={source['known_hosts_file']} "
        f"-i {source['private_key_file']}"
    )
    return env


def _repo_path(state_dir: Path, source_id: str) -> Path:
    digest = hashlib.sha256(source_id.encode("utf-8")).hexdigest()[:12]
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", source_id).strip("-")[-64:]
    return state_dir / "repos" / f"{safe}-{digest}.git"


def _ensure_bare_repo(
    source: dict[str, Any],
    *,
    state_dir: Path,
    runner: Runner,
) -> tuple[Path, str | None, dict[str, str] | None]:
    repo = _repo_path(state_dir, source["id"])
    repo.parent.mkdir(parents=True, exist_ok=True)
    env = _git_env(source)

    if not repo.exists():
        result = _run(["git", "init", "--bare", str(repo)], runner=runner, env=env)
        if result.returncode != 0:
            return repo, None, {
                "code": "GIT_INIT_FAILED",
                "summary": "Could not initialize the local bare Git cache.",
            }

    get_remote = _run(
        ["git", f"--git-dir={repo}", "remote", "get-url", "origin"],
        runner=runner,
        env=env,
    )
    if get_remote.returncode != 0:
        add_remote = _run(
            ["git", f"--git-dir={repo}", "remote", "add", "origin", source["repository"]],
            runner=runner,
            env=env,
        )
        if add_remote.returncode != 0:
            return repo, None, {
                "code": "GIT_REMOTE_CONFIG_FAILED",
                "summary": "Could not configure the declared-state Git remote.",
            }
    elif get_remote.stdout.strip() != source["repository"]:
        set_remote = _run(
            ["git", f"--git-dir={repo}", "remote", "set-url", "origin", source["repository"]],
            runner=runner,
            env=env,
        )
        if set_remote.returncode != 0:
            return repo, None, {
                "code": "GIT_REMOTE_CONFIG_FAILED",
                "summary": "Could not update the declared-state Git remote.",
            }

    branch = source.get("branch", "main")
    target_ref = f"refs/remotes/origin/{branch}"
    fetch = _run(
        [
            "git",
            f"--git-dir={repo}",
            "fetch",
            "--prune",
            "--depth=1",
            "origin",
            f"+refs/heads/{branch}:{target_ref}",
        ],
        runner=runner,
        env=env,
    )
    if fetch.returncode != 0:
        code, summary = _classify_git_failure(fetch.stderr)
        return repo, None, {"code": code, "summary": summary}

    revision = _run(
        ["git", f"--git-dir={repo}", "rev-parse", target_ref],
        runner=runner,
        env=env,
    )
    if revision.returncode != 0 or not revision.stdout.strip():
        return repo, None, {
            "code": "GIT_REVISION_UNAVAILABLE",
            "summary": "Git source revision could not be resolved.",
        }
    return repo, revision.stdout.strip(), None


def _read_manifest(
    repo: Path,
    revision: str,
    path: str,
    *,
    source: dict[str, Any],
    runner: Runner,
    max_bytes: int,
) -> tuple[str | None, dict[str, str] | None]:
    object_name = f"{revision}:{path}"
    size = _run(
        ["git", f"--git-dir={repo}", "cat-file", "-s", object_name],
        runner=runner,
        env=_git_env(source),
    )
    if size.returncode != 0:
        return None, {
            "code": "GIT_BLOB_READ_FAILED",
            "summary": f"Could not inspect declared manifest {path}.",
        }
    try:
        manifest_size = int(size.stdout.strip())
    except ValueError:
        return None, {
            "code": "GIT_BLOB_SIZE_INVALID",
            "summary": f"Could not determine declared manifest size for {path}.",
        }
    if manifest_size > max_bytes:
        return None, {
            "code": "DECLARED_MANIFEST_TOO_LARGE",
            "summary": f"Declared manifest {path} exceeds the safe normalization size limit.",
        }

    show = _run(
        ["git", f"--git-dir={repo}", "show", object_name],
        runner=runner,
        env=_git_env(source),
    )
    if show.returncode != 0:
        return None, {
            "code": "GIT_BLOB_READ_FAILED",
            "summary": f"Could not read declared manifest {path}.",
        }
    return show.stdout, None


def _parse_supported_document(
    document: str,
    *,
    runner: Runner,
) -> tuple[dict[str, Any] | None, dict[str, str] | None]:
    """Parse a built-in Kubernetes manifest locally without API discovery or kubeconfig."""
    result = _run(
        [
            "kubectl",
            "patch",
            "--local",
            "--type=merge",
            "--patch={}",
            "-f",
            "-",
            "-o",
            "json",
        ],
        runner=runner,
        env=_local_kubectl_env(),
        input_text=document,
    )
    if result.returncode != 0:
        return None, {
            "code": "DECLARED_MANIFEST_PARSE_FAILED",
            "summary": "A supported Kubernetes manifest could not be parsed locally.",
        }
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None, {
            "code": "DECLARED_MANIFEST_PARSE_FAILED",
            "summary": "A supported Kubernetes manifest produced invalid local parser output.",
        }
    if not isinstance(value, dict):
        return None, {
            "code": "DECLARED_MANIFEST_PARSE_FAILED",
            "summary": "A supported Kubernetes manifest did not normalize to one object.",
        }
    return value, None


def _string_map(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): str(item)
        for key, item in value.items()
        if isinstance(key, str) and isinstance(item, (str, int, float, bool))
    }


def _images(spec: dict[str, Any]) -> list[str]:
    return [
        container["image"]
        for container in spec.get("template", {}).get("spec", {}).get("containers", [])
        if isinstance(container, dict) and isinstance(container.get("image"), str)
    ]


def _selector(spec: dict[str, Any]) -> dict[str, str]:
    return _string_map(spec.get("selector", {}).get("matchLabels", {}))


def _service_ports(spec: dict[str, Any]) -> list[dict[str, Any]]:
    ports: list[dict[str, Any]] = []
    for item in spec.get("ports", []):
        if not isinstance(item, dict) or "port" not in item:
            continue
        port: dict[str, Any] = {
            "protocol": item.get("protocol", "TCP"),
            "port": item["port"],
            "targetPort": item.get("targetPort", item["port"]),
        }
        for optional in ("name", "nodePort"):
            if optional in item:
                port[optional] = item[optional]
        ports.append(port)
    return ports


def _ingress_backends(spec: dict[str, Any]) -> list[dict[str, Any]]:
    backends: list[dict[str, Any]] = []
    default_service = spec.get("defaultBackend", {}).get("service", {})
    if isinstance(default_service, dict) and default_service.get("name"):
        port = default_service.get("port", {})
        backends.append(
            {
                "host": None,
                "path": None,
                "service": default_service["name"],
                "service_port": port.get("name", port.get("number")),
            }
        )

    for rule in spec.get("rules", []):
        if not isinstance(rule, dict):
            continue
        host = rule.get("host")
        for path in rule.get("http", {}).get("paths", []):
            if not isinstance(path, dict):
                continue
            service = path.get("backend", {}).get("service", {})
            if not isinstance(service, dict) or not service.get("name"):
                continue
            port = service.get("port", {})
            backends.append(
                {
                    "host": host,
                    "path": path.get("path"),
                    "service": service["name"],
                    "service_port": port.get("name", port.get("number")),
                }
            )
    return backends


def _normalize_object(
    value: dict[str, Any],
    *,
    cluster_id: str,
) -> tuple[dict[str, Any] | None, dict[str, str] | None]:
    kind = value.get("kind")
    api_version = value.get("apiVersion")
    metadata = value.get("metadata", {})
    if kind not in SUPPORTED_KINDS or not isinstance(api_version, str) or not isinstance(metadata, dict):
        return None, {
            "code": "DECLARED_OBJECT_UNSUPPORTED",
            "summary": "Parsed object is outside the supported declared evidence contract.",
        }
    name = metadata.get("name")
    if not isinstance(name, str) or not name:
        return None, {
            "code": "DECLARED_IDENTITY_INVALID",
            "summary": f"Declared {kind} is missing metadata.name.",
        }

    namespace = None if kind == "Namespace" else metadata.get("namespace", "default")
    if kind in NAMESPACED_KINDS and (not isinstance(namespace, str) or not namespace):
        return None, {
            "code": "DECLARED_IDENTITY_INVALID",
            "summary": f"Declared {kind}/{name} has an invalid namespace.",
        }

    spec = value.get("spec", {})
    if not isinstance(spec, dict):
        spec = {}
    data: dict[str, Any] = {}

    if kind in {"Deployment", "StatefulSet"}:
        data["desired_replicas"] = spec.get("replicas", 1)
        data["images"] = _images(spec)
        selector = _selector(spec)
        if selector:
            data["selector"] = selector
    elif kind == "DaemonSet":
        data["images"] = _images(spec)
        selector = _selector(spec)
        if selector:
            data["selector"] = selector
    elif kind == "Service":
        data["type"] = spec.get("type", "ClusterIP")
        selector = _string_map(spec.get("selector", {}))
        if selector:
            data["selector"] = selector
        ports = _service_ports(spec)
        if ports:
            data["ports"] = ports
    elif kind == "Ingress":
        if "ingressClassName" in spec:
            data["ingress_class_name"] = spec.get("ingressClassName")
        backends = _ingress_backends(spec)
        if backends:
            data["backends"] = backends
        tls_names = [
            item.get("secretName")
            for item in spec.get("tls", [])
            if isinstance(item, dict) and isinstance(item.get("secretName"), str)
        ]
        if tls_names:
            data["tls_secret_names"] = tls_names
    elif kind == "PersistentVolumeClaim":
        if "storageClassName" in spec:
            data["storage_class"] = spec.get("storageClassName")
        if "accessModes" in spec:
            data["access_modes"] = spec.get("accessModes", [])
        storage = spec.get("resources", {}).get("requests", {}).get("storage")
        if storage is not None:
            data["requested_storage"] = storage

    subject = {
        "system": "kubernetes",
        "cluster": cluster_id,
        "api_group": _api_group(api_version),
        "kind": kind,
        "namespace": namespace,
        "name": name,
    }
    return {"subject": subject, "data": data}, None


def _envelope(
    *,
    source: dict[str, Any],
    revision: str,
    source_ref: str,
    operation: str,
    document_index: int,
    normalized: dict[str, Any],
    now: datetime,
    ttl_seconds: int,
) -> dict[str, Any]:
    identity = json.dumps(normalized["subject"], sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(
        f"{source['id']}|{revision}|{source_ref}|{document_index}|{identity}".encode("utf-8")
    ).hexdigest()[:24]
    return {
        "schema_version": "0.1",
        "evidence_id": f"ev-git-{digest}",
        "plane": "declared",
        "subject": normalized["subject"],
        "existence": "PRESENT",
        "observation_status": "COMPLETE",
        "attempted_at": _rfc3339(now),
        "observed_at": _rfc3339(now),
        "expires_at": _rfc3339(now + timedelta(seconds=ttl_seconds)),
        "data": normalized["data"],
        "provenance": {
            "source_type": "git",
            "source_id": source["id"],
            "collector": "git-declared-observer",
            "collector_version": OBSERVER_VERSION,
            "operation": f"{operation} {source_ref}#document={document_index}",
            "revision": revision,
        },
        "errors": [],
    }


def _status(
    *,
    source: dict[str, Any],
    attempted_at: datetime,
    status: str,
    revision: str | None,
    normalized_records: int,
    skipped_documents: int,
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    current = status in {"COMPLETE", "PARTIAL"} and revision is not None
    return {
        "source_status_version": SOURCE_STATUS_VERSION,
        "source_id": source["id"],
        "attempted_at": _rfc3339(attempted_at),
        "status": status,
        "observed_at": _rfc3339(attempted_at) if current else None,
        "revision": revision if current else None,
        "normalized_records": normalized_records,
        "skipped_documents": skipped_documents,
        "errors": errors,
    }


def _safe_repo_relative(path: str) -> bool:
    candidate = Path(path)
    return bool(path) and not candidate.is_absolute() and ".." not in candidate.parts


def _add_documents(
    text: str,
    *,
    source_ref: str,
    operation: str,
    source: dict[str, Any],
    revision: str,
    runner: Runner,
    now: datetime,
    ttl_seconds: int,
    records_by_identity: dict[tuple[Any, ...], dict[str, Any]],
    duplicate_identities: set[tuple[Any, ...]],
    errors: list[dict[str, str]],
) -> int:
    skipped = 0
    for document_index, document in enumerate(_split_documents(text), start=1):
        kind = _kind_from_text(document)
        if not kind:
            skipped += 1
            continue
        if kind in SKIPPED_SENSITIVE_KINDS or kind not in SUPPORTED_KINDS:
            skipped += 1
            continue

        parsed, parse_error = _parse_supported_document(document, runner=runner)
        if parse_error or parsed is None:
            errors.append(
                {
                    "code": (parse_error or {}).get("code", "DECLARED_MANIFEST_PARSE_FAILED"),
                    "summary": f"Could not normalize supported declaration {source_ref} document {document_index}.",
                }
            )
            continue

        normalized, normalize_error = _normalize_object(parsed, cluster_id=source["cluster_id"])
        if normalize_error or normalized is None:
            errors.append(
                {
                    "code": (normalize_error or {}).get("code", "DECLARED_OBJECT_INVALID"),
                    "summary": f"Could not normalize declared object in {source_ref} document {document_index}.",
                }
            )
            continue

        record = _envelope(
            source=source,
            revision=revision,
            source_ref=source_ref,
            operation=operation,
            document_index=document_index,
            normalized=normalized,
            now=now,
            ttl_seconds=ttl_seconds,
        )
        identity = _subject_key(record["subject"])
        if identity in records_by_identity:
            duplicate_identities.add(identity)
            records_by_identity.pop(identity, None)
            errors.append(
                {
                    "code": "DUPLICATE_DECLARED_IDENTITY",
                    "summary": (
                        "Multiple configured declared targets resolve to the same Kubernetes identity: "
                        f"{record['subject']['kind']}/{record['subject'].get('namespace') or ''}/{record['subject']['name']}."
                    ),
                }
            )
            continue
        if identity in duplicate_identities:
            continue
        records_by_identity[identity] = record
    return skipped


def _create_worktree(
    repo: Path,
    revision: str,
    *,
    state_dir: Path,
    source: dict[str, Any],
    runner: Runner,
) -> tuple[Path | None, dict[str, str] | None]:
    root = state_dir / "worktrees"
    root.mkdir(parents=True, exist_ok=True)
    worktree = root / f"declared-{revision[:12]}-{uuid.uuid4().hex[:8]}"
    result = _run(
        [
            "git",
            f"--git-dir={repo}",
            "worktree",
            "add",
            "--detach",
            str(worktree),
            revision,
        ],
        runner=runner,
        env=_git_env(source),
    )
    if result.returncode != 0:
        return None, {
            "code": "GIT_WORKTREE_FAILED",
            "summary": "Could not materialize the declared Git revision for local rendering.",
        }
    return worktree, None


def _remove_worktree(
    repo: Path,
    worktree: Path,
    *,
    source: dict[str, Any],
    runner: Runner,
) -> None:
    _run(
        ["git", f"--git-dir={repo}", "worktree", "remove", "--force", str(worktree)],
        runner=runner,
        env=_git_env(source),
    )
    if worktree.exists():
        shutil.rmtree(worktree, ignore_errors=True)


def _render_kustomize_target(
    worktree: Path,
    target: str,
    *,
    runner: Runner,
) -> tuple[str | None, dict[str, str] | None]:
    if not _safe_repo_relative(target):
        return None, {
            "code": "KUSTOMIZE_TARGET_INVALID",
            "summary": f"Configured Kustomize target is not a safe repository-relative path: {target}.",
        }
    root = worktree.resolve()
    target_path = (worktree / target).resolve()
    try:
        target_path.relative_to(root)
    except ValueError:
        return None, {
            "code": "KUSTOMIZE_TARGET_INVALID",
            "summary": f"Configured Kustomize target escapes the materialized repository: {target}.",
        }
    if not target_path.is_dir():
        return None, {
            "code": "KUSTOMIZE_TARGET_MISSING",
            "summary": f"Configured Kustomize target is not present at the observed revision: {target}.",
        }

    result = _run(
        ["kubectl", "kustomize", str(target_path)],
        runner=runner,
        env=_local_kubectl_env(),
        timeout=DEFAULT_KUSTOMIZE_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        return None, {
            "code": "KUSTOMIZE_RENDER_FAILED",
            "summary": f"Could not render configured Kustomize target {target} locally.",
        }
    return result.stdout, None


def sync_source(
    source: dict[str, Any],
    *,
    state_dir: Path,
    declared_dir: Path,
    status_path: Path,
    runner: Runner = subprocess.run,
    now: datetime | None = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    max_manifest_bytes: int = DEFAULT_MAX_MANIFEST_BYTES,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    repo, revision, fetch_error = _ensure_bare_repo(source, state_dir=state_dir, runner=runner)
    if fetch_error or not revision:
        status = _status(
            source=source,
            attempted_at=now,
            status="FAILED_TO_OBSERVE",
            revision=None,
            normalized_records=0,
            skipped_documents=0,
            errors=[fetch_error or {"code": "GIT_FETCH_FAILED", "summary": "Git source refresh failed."}],
        )
        atomic_write_json(status_path, status)
        return status

    errors: list[dict[str, str]] = []
    skipped = 0
    records_by_identity: dict[tuple[Any, ...], dict[str, Any]] = {}
    duplicate_identities: set[tuple[Any, ...]] = set()

    for path in source.get("raw_manifest_paths", []):
        if not _safe_repo_relative(path):
            errors.append(
                {
                    "code": "DECLARED_PATH_INVALID",
                    "summary": f"Configured raw manifest path is not repository-relative: {path}.",
                }
            )
            continue
        text, read_error = _read_manifest(
            repo,
            revision,
            path,
            source=source,
            runner=runner,
            max_bytes=max_manifest_bytes,
        )
        if read_error or text is None:
            errors.append(read_error or {"code": "GIT_BLOB_READ_FAILED", "summary": f"Could not read {path}."})
            continue
        skipped += _add_documents(
            text,
            source_ref=path,
            operation="read",
            source=source,
            revision=revision,
            runner=runner,
            now=now,
            ttl_seconds=ttl_seconds,
            records_by_identity=records_by_identity,
            duplicate_identities=duplicate_identities,
            errors=errors,
        )

    targets = source.get("kustomize_targets", [])
    if targets:
        worktree, worktree_error = _create_worktree(
            repo,
            revision,
            state_dir=state_dir,
            source=source,
            runner=runner,
        )
        if worktree_error or worktree is None:
            errors.append(worktree_error or {"code": "GIT_WORKTREE_FAILED", "summary": "Could not materialize Git revision for Kustomize rendering."})
        else:
            try:
                for target in targets:
                    rendered, render_error = _render_kustomize_target(worktree, target, runner=runner)
                    if render_error or rendered is None:
                        errors.append(render_error or {"code": "KUSTOMIZE_RENDER_FAILED", "summary": f"Could not render {target}."})
                        continue
                    skipped += _add_documents(
                        rendered,
                        source_ref=target,
                        operation="render kustomize",
                        source=source,
                        revision=revision,
                        runner=runner,
                        now=now,
                        ttl_seconds=ttl_seconds,
                        records_by_identity=records_by_identity,
                        duplicate_identities=duplicate_identities,
                        errors=errors,
                    )
            finally:
                _remove_worktree(repo, worktree, source=source, runner=runner)

    records = sorted(
        records_by_identity.values(),
        key=lambda item: (
            item["subject"]["api_group"],
            item["subject"]["kind"],
            item["subject"].get("namespace") or "",
            item["subject"]["name"],
        ),
    )
    declared_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(
        declared_dir / "records.json",
        {
            "declared_bundle_version": "0.1",
            "source_id": source["id"],
            "revision": revision,
            "records": records,
        },
    )
    status = _status(
        source=source,
        attempted_at=now,
        status="PARTIAL" if errors else "COMPLETE",
        revision=revision,
        normalized_records=len(records),
        skipped_documents=skipped,
        errors=errors,
    )
    atomic_write_json(status_path, status)
    return status


def _validate_path_list(source: dict[str, Any], field: str) -> list[str]:
    value = source.get(field, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"git source config field {field} must be a list of repository-relative paths")
    invalid = [item for item in value if not _safe_repo_relative(item)]
    if invalid:
        raise ValueError(f"git source config field {field} contains unsafe paths")
    return value


def _load_config(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    sources = value.get("sources")
    if not isinstance(sources, list) or len(sources) != 1 or not isinstance(sources[0], dict):
        raise ValueError("git source config must contain exactly one source in this slice")
    source = sources[0]
    required = {
        "id",
        "repository",
        "branch",
        "cluster_id",
        "raw_manifest_paths",
        "kustomize_targets",
        "private_key_file",
        "public_key_file",
        "known_hosts_file",
    }
    missing = sorted(required - set(source))
    if missing:
        raise ValueError(f"git source config missing fields: {', '.join(missing)}")
    _validate_path_list(source, "raw_manifest_paths")
    _validate_path_list(source, "kustomize_targets")
    if not source["raw_manifest_paths"] and not source["kustomize_targets"]:
        raise ValueError("git source config must declare at least one raw manifest or Kustomize target")
    return source


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh normalized Git-declared Kubernetes evidence.")
    parser.add_argument("command", choices=("sync", "status", "public-key"))
    parser.add_argument("--config", type=Path, default=Path("/etc/infra-assurance/git-source.json"))
    parser.add_argument("--state-dir", type=Path, default=Path("/var/lib/infra-assurance/git"))
    parser.add_argument("--declared-dir", type=Path, default=Path("/var/lib/infra-assurance/declared/current"))
    parser.add_argument("--source-status", type=Path, default=Path("/var/lib/infra-assurance/declared/source-status.json"))
    args = parser.parse_args()

    try:
        source = _load_config(args.config)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "CONFIG_ERROR", "summary": str(exc)}, indent=2))
        return 2

    if args.command == "public-key":
        print(Path(source["public_key_file"]).read_text(encoding="utf-8").strip())
        return 0

    if args.command == "status":
        if not args.source_status.exists():
            print(json.dumps({"status": "DECLARED_STATE_UNAVAILABLE"}, indent=2))
            return 0
        print(args.source_status.read_text(encoding="utf-8").strip())
        return 0

    status = sync_source(
        source,
        state_dir=args.state_dir,
        declared_dir=args.declared_dir,
        status_path=args.source_status,
    )
    print(
        json.dumps(
            {
                "status": status["status"],
                "source_id": status["source_id"],
                "revision": status["revision"],
                "normalized_records": status["normalized_records"],
                "skipped_documents": status["skipped_documents"],
                "errors": status["errors"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
