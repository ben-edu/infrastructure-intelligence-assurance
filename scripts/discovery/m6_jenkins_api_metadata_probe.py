from __future__ import annotations

import base64
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

INFRA_REPO = Path("/home/ben/projects/afpa-infra-rebuild")
JENKINS_ROOT_CANDIDATES = (
    INFRA_REPO / "mcp" / "jenkins-readonly",
    INFRA_REPO / "mcp" / "jenkins",
)

APPROVED_ENV_KEYS = {
    "JENKINS_URL",
    "JENKINS_BASE_URL",
    "JENKINS_USER",
    "JENKINS_USERNAME",
    "JENKINS_API_USER",
    "JENKINS_TOKEN",
    "JENKINS_API_TOKEN",
    "JENKINS_PASSWORD",
}
URL_KEYS = ("JENKINS_URL", "JENKINS_BASE_URL")
USER_KEYS = ("JENKINS_USER", "JENKINS_USERNAME", "JENKINS_API_USER")
SECRET_KEYS = ("JENKINS_API_TOKEN", "JENKINS_TOKEN", "JENKINS_PASSWORD")
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
TIMEOUT_SECONDS = 10

SAFE_RESULT_CATEGORIES = {
    "SUCCESS",
    "FAILURE",
    "UNSTABLE",
    "ABORTED",
    "NOT_BUILT",
}


def _strip_env_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return value


def _read_approved_env_file(path: Path) -> dict[str, str]:
    """Read only explicitly approved Jenkins connection keys.

    Values remain process-local and are never returned by discovery output.
    """
    values: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return values

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if key not in APPROVED_ENV_KEYS:
            continue
        value = _strip_env_value(raw_value)
        if value:
            values[key] = value
    return values


def _first_value(mapping: dict[str, str], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if value:
            return value
    return None


def _load_local_connection_material(
    roots: tuple[Path, ...] = JENKINS_ROOT_CANDIDATES,
) -> dict[str, Any]:
    merged: dict[str, str] = {
        key: value for key in APPROVED_ENV_KEYS if (value := os.environ.get(key))
    }
    env_files_observed = 0
    env_files_read = 0

    for root in roots:
        try:
            if not root.is_dir():
                continue
        except OSError:
            continue
        for name in (".env", "jenkins.env"):
            path = root / name
            try:
                if not path.is_file():
                    continue
            except OSError:
                continue
            env_files_observed += 1
            values = _read_approved_env_file(path)
            if values:
                env_files_read += 1
                for key, value in values.items():
                    merged.setdefault(key, value)

    base_url = _first_value(merged, URL_KEYS)
    username = _first_value(merged, USER_KEYS)
    secret = _first_value(merged, SECRET_KEYS)

    if not base_url:
        status = "CONNECTION_CONFIG_UNAVAILABLE"
    elif bool(username) != bool(secret):
        status = "CONNECTION_CONFIG_INCOMPLETE"
    else:
        status = "CONNECTION_CONFIG_READY"

    return {
        "status": status,
        "base_url": base_url,
        "username": username,
        "secret": secret,
        "env_files_observed": env_files_observed,
        "env_files_read_for_approved_keys": env_files_read,
        "credential_material_loaded_locally": bool(username and secret),
    }


def _metadata_url(base_url: str) -> str | None:
    try:
        parsed = urlsplit(base_url.strip())
    except Exception:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    if parsed.username is not None or parsed.password is not None:
        return None
    if parsed.query or parsed.fragment:
        return None

    base_path = parsed.path.rstrip("/")
    api_path = f"{base_path}/api/json" if base_path else "/api/json"
    tree = "jobs[name,color,lastBuild[number,result,timestamp,building]]"
    query = urlencode({"tree": tree})
    return urlunsplit((parsed.scheme, parsed.netloc, api_path, query, ""))


def _fetch_metadata_json(
    base_url: str,
    username: str | None,
    secret: str | None,
) -> tuple[str, dict[str, Any] | None]:
    endpoint = _metadata_url(base_url)
    if endpoint is None:
        return "INVALID_ENDPOINT_CONFIGURATION", None

    headers = {"Accept": "application/json", "User-Agent": "infra-assurance-readonly/1"}
    if username and secret:
        token = base64.b64encode(f"{username}:{secret}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {token}"

    request = Request(endpoint, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            content_length = response.headers.get("Content-Length")
            if content_length:
                try:
                    if int(content_length) > MAX_RESPONSE_BYTES:
                        return "RESPONSE_TOO_LARGE", None
                except ValueError:
                    pass
            payload = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError:
        return "HTTP_ERROR", None
    except URLError:
        return "CONNECTION_ERROR", None
    except Exception:
        return "FAILED_TO_OBSERVE", None

    if len(payload) > MAX_RESPONSE_BYTES:
        return "RESPONSE_TOO_LARGE", None
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return "INVALID_JSON", None
    if not isinstance(decoded, dict):
        return "INVALID_JSON_SHAPE", None
    return "COMPLETE", decoded


def _safe_result(build: dict[str, Any]) -> str:
    if build.get("building") is True:
        return "RUNNING"
    result = build.get("result")
    if isinstance(result, str) and result.upper() in SAFE_RESULT_CATEGORIES:
        return result.upper()
    return "UNKNOWN"


def _aggregate_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    jobs = payload.get("jobs")
    if not isinstance(jobs, list):
        jobs = []

    total_jobs = 0
    jobs_with_last_build = 0
    ansible_name_signal_jobs = 0
    ansible_name_signal_jobs_with_last_build = 0
    all_results: Counter[str] = Counter()
    ansible_signal_results: Counter[str] = Counter()

    for item in jobs:
        if not isinstance(item, dict):
            continue
        total_jobs += 1
        name = item.get("name") if isinstance(item.get("name"), str) else ""
        ansible_signal = "ansible" in name.lower()
        if ansible_signal:
            ansible_name_signal_jobs += 1

        build = item.get("lastBuild")
        if not isinstance(build, dict):
            continue
        jobs_with_last_build += 1
        category = _safe_result(build)
        all_results[category] += 1
        if ansible_signal:
            ansible_name_signal_jobs_with_last_build += 1
            ansible_signal_results[category] += 1

    return {
        "jobs_total": total_jobs,
        "jobs_with_last_build_metadata": jobs_with_last_build,
        "ansible_name_signal_jobs": ansible_name_signal_jobs,
        "ansible_name_signal_jobs_with_last_build_metadata": ansible_name_signal_jobs_with_last_build,
        "last_build_result_counts": dict(sorted(all_results.items())),
        "ansible_name_signal_last_build_result_counts": dict(sorted(ansible_signal_results.items())),
    }


def discover() -> dict[str, Any]:
    connection = _load_local_connection_material()
    result: dict[str, Any] = {
        "connection_config_status": connection["status"],
        "env_files_observed": connection["env_files_observed"],
        "env_files_read_for_approved_keys": connection["env_files_read_for_approved_keys"],
        "credential_material_loaded_locally": connection["credential_material_loaded_locally"],
        "credential_values_projected": False,
        "endpoint_value_projected": False,
        "jenkins_api_invoked": False,
        "api_observation_status": "NOT_ATTEMPTED",
        "jobs_total": 0,
        "jobs_with_last_build_metadata": 0,
        "ansible_name_signal_jobs": 0,
        "ansible_name_signal_jobs_with_last_build_metadata": 0,
        "last_build_result_counts": {},
        "ansible_name_signal_last_build_result_counts": {},
        "execution_outcome_status": "UNKNOWN",
        "execution_success_status": "UNKNOWN",
        "idempotence_status": "UNKNOWN",
        "configuration_drift_status": "UNKNOWN",
        "successful_execution_claims": 0,
        "idempotence_claims": 0,
        "drift_claims": 0,
    }

    if connection["status"] != "CONNECTION_CONFIG_READY" or not connection["base_url"]:
        return result

    result["jenkins_api_invoked"] = True
    status, payload = _fetch_metadata_json(
        connection["base_url"], connection["username"], connection["secret"]
    )
    result["api_observation_status"] = status
    if status != "COMPLETE" or payload is None:
        return result

    result.update(_aggregate_metadata(payload))
    return result


def _format_counts(values: dict[str, int]) -> str:
    if not values:
        return "NONE_OBSERVED"
    return ",".join(f"{key}={values[key]}" for key in sorted(values))


def main() -> int:
    print("===== M6 JENKINS API METADATA-ONLY PROBE =====")
    print()
    print("===== SAFETY =====")
    print("mutation_allowed: False")
    print("http_method: GET_ONLY")
    print("jenkins_console_logs_inspected: False")
    print("jenkins_job_config_bodies_inspected: False")
    print("jenkins_build_parameters_inspected: False")
    print("credential_values_projected: False")
    print("endpoint_value_projected: False")
    print("ansible_cli_invoked: False")
    print("ssh_connections_performed: False")

    result = discover()

    print()
    print("===== LOCAL CONNECTION MATERIAL =====")
    print("connection_config_status:", result["connection_config_status"])
    print("env_files_observed:", result["env_files_observed"])
    print("env_files_read_for_approved_keys:", result["env_files_read_for_approved_keys"])
    print("credential_material_loaded_locally:", result["credential_material_loaded_locally"])
    print("credential_values_projected: False")
    print("endpoint_value_projected: False")

    print()
    print("===== JENKINS RUNTIME METADATA =====")
    print("jenkins_api_invoked:", result["jenkins_api_invoked"])
    print("api_observation_status:", result["api_observation_status"])
    print("jobs_total:", result["jobs_total"])
    print("jobs_with_last_build_metadata:", result["jobs_with_last_build_metadata"])
    print("ansible_name_signal_jobs:", result["ansible_name_signal_jobs"])
    print(
        "ansible_name_signal_jobs_with_last_build_metadata:",
        result["ansible_name_signal_jobs_with_last_build_metadata"],
    )
    print("last_build_result_counts:", _format_counts(result["last_build_result_counts"]))
    print(
        "ansible_name_signal_last_build_result_counts:",
        _format_counts(result["ansible_name_signal_last_build_result_counts"]),
    )

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
    print("Observed Jenkins job/build metadata is Jenkins runtime evidence only. It is not automatically Ansible execution evidence.")
    print("An `ansible` token in an in-memory job name is only a weak metadata relationship signal; job names are not projected.")
    print("Build result categories describe Jenkins last-build metadata only and must not be promoted to Ansible success, idempotence, reachability, or drift claims without stronger relationship evidence.")
    print("If no Ansible-named job signal is observed, that is bounded job-name absence only and does not rule out Ansible execution under other job names.")

    print()
    print("===== TRUST BOUNDARY =====")
    print("Only approved Jenkins URL/user/token/password keys may be loaded locally for authentication; their values are never printed or persisted.")
    print("The only permitted Jenkins request is a metadata-only GET to the root JSON API with a restricted tree projection.")
    print("Job names may be inspected only in memory to count an `ansible` name signal; names and build numbers are not printed or persisted.")
    print("Console logs, config.xml, build parameters, raw commands, environment values, inventory arguments, host targets, and Vault material are not requested or projected.")
    print("No Ansible CLI, SSH connection, Jenkins mutation, or infrastructure mutation was performed.")

    if result["connection_config_status"] != "CONNECTION_CONFIG_READY":
        return 2
    if result["api_observation_status"] != "COMPLETE":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
