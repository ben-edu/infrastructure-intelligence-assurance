from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

EXPECTED_WORKLOADS = (
    ("bookstack", "Deployment", "mariadb"),
    ("misp", "Deployment", "mariadb"),
    ("misp", "Deployment", "mariadb-v2"),
    ("moodle", "StatefulSet", "moodle-mariadb"),
)

BACKUP_TOKENS = (
    "mariadb-dump",
    "mariadb_dump",
    "mysqldump",
    "mariabackup",
    "xtrabackup",
    "mydumper",
    "mysqlpump",
    "mysql-backup",
    "mariadb-backup",
    "mysqlbackup",
)

BACKUP_TOOLS = (
    "mariadb-dump",
    "mysqldump",
    "mariabackup",
    "xtrabackup",
    "mydumper",
    "mysqlpump",
    "mysqlbackup",
)

CRON_DIRS = (
    Path("/etc/cron.d"),
    Path("/etc/cron.daily"),
    Path("/etc/cron.hourly"),
    Path("/etc/cron.weekly"),
    Path("/etc/cron.monthly"),
)

SAFE_NAME = re.compile(r"^[A-Za-z0-9_.:@+\-]{1,200}$")


def run_json(cmd: list[str]) -> tuple[int, Any | None, str | None]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
    except Exception as exc:
        return 127, None, type(exc).__name__
    if proc.returncode != 0:
        return proc.returncode, None, "COMMAND_FAILED"
    try:
        return 0, json.loads(proc.stdout), None
    except json.JSONDecodeError:
        return 1, None, "INVALID_JSON"


def run_text(cmd: list[str]) -> tuple[int, str, str | None]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
    except Exception as exc:
        return 127, "", type(exc).__name__
    if proc.returncode != 0:
        return proc.returncode, "", "COMMAND_FAILED"
    return 0, proc.stdout, None


def safe_name(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if SAFE_NAME.fullmatch(value) else None


def backup_signal(text: str) -> bool:
    value = text.lower()
    if any(token in value for token in BACKUP_TOKENS):
        return True
    database_word = "mariadb" in value or "mysql" in value
    backup_word = "backup" in value or "dump" in value
    return database_word and backup_word


def pod_spec_for_workload(obj: dict[str, Any]) -> dict[str, Any]:
    return obj.get("spec", {}).get("template", {}).get("spec", {}) if isinstance(obj, dict) else {}


def workload_projection(obj: dict[str, Any]) -> dict[str, Any]:
    pod_spec = pod_spec_for_workload(obj)
    containers = pod_spec.get("containers", []) if isinstance(pod_spec, dict) else []
    init_containers = pod_spec.get("initContainers", []) if isinstance(pod_spec, dict) else []
    volumes = pod_spec.get("volumes", []) if isinstance(pod_spec, dict) else []

    backup_containers: list[str] = []
    backup_init: list[str] = []
    configmap_backup_signals: list[str] = []
    pvc_volume_count = 0
    secret_reference_count = 0

    def inspect_container(item: Any, target: list[str]) -> None:
        nonlocal secret_reference_count
        if not isinstance(item, dict):
            return
        name = safe_name(item.get("name")) or "UNKNOWN"
        image = item.get("image") if isinstance(item.get("image"), str) else ""
        if backup_signal(name) or backup_signal(image):
            safe_image = image.split("@", 1)[0] if len(image) <= 300 else "UNKNOWN"
            target.append(f"{name}:{safe_image or 'UNKNOWN'}")

        env = item.get("env", [])
        env_from = item.get("envFrom", [])
        for row in env if isinstance(env, list) else []:
            if isinstance(row, dict) and isinstance(row.get("valueFrom"), dict) and "secretKeyRef" in row["valueFrom"]:
                secret_reference_count += 1
        for row in env_from if isinstance(env_from, list) else []:
            if isinstance(row, dict) and "secretRef" in row:
                secret_reference_count += 1

    for item in containers if isinstance(containers, list) else []:
        inspect_container(item, backup_containers)
    for item in init_containers if isinstance(init_containers, list) else []:
        inspect_container(item, backup_init)

    for volume in volumes if isinstance(volumes, list) else []:
        if not isinstance(volume, dict):
            continue
        if "persistentVolumeClaim" in volume:
            pvc_volume_count += 1
        configmap = volume.get("configMap")
        if isinstance(configmap, dict):
            cm_name = safe_name(configmap.get("name"))
            if cm_name and backup_signal(cm_name):
                configmap_backup_signals.append(cm_name)
        if "secret" in volume:
            secret_reference_count += 1

    signals = backup_containers + backup_init + configmap_backup_signals
    return {
        "container_count": len(containers) if isinstance(containers, list) else 0,
        "init_container_count": len(init_containers) if isinstance(init_containers, list) else 0,
        "pvc_volume_count": pvc_volume_count,
        "secret_reference_count": secret_reference_count,
        "backup_container_signals": sorted(set(backup_containers)),
        "backup_init_signals": sorted(set(backup_init)),
        "backup_configmap_signals": sorted(set(configmap_backup_signals)),
        "database_backup_mechanism_status": "DECLARED_SIGNAL_OBSERVED" if signals else "DATABASE_BACKUP_MECHANISM_UNKNOWN",
    }


def cronjob_job_candidates() -> tuple[str, list[dict[str, Any]]]:
    rc, payload, _ = run_json(["kubectl", "get", "cronjobs,jobs", "-A", "-o", "json"])
    if rc != 0 or not isinstance(payload, dict):
        return "FAILED_TO_OBSERVE", []

    rows: list[dict[str, Any]] = []
    for item in payload.get("items", []):
        if not isinstance(item, dict):
            continue
        meta = item.get("metadata", {})
        namespace = safe_name(meta.get("namespace")) or "UNKNOWN"
        name = safe_name(meta.get("name")) or "UNKNOWN"
        kind = safe_name(item.get("kind")) or "UNKNOWN"
        if kind == "CronJob":
            pod_spec = item.get("spec", {}).get("jobTemplate", {}).get("spec", {}).get("template", {}).get("spec", {})
        else:
            pod_spec = item.get("spec", {}).get("template", {}).get("spec", {})
        containers = pod_spec.get("containers", []) if isinstance(pod_spec, dict) else []
        safe_images: list[str] = []
        signal = backup_signal(name)
        for container in containers if isinstance(containers, list) else []:
            if not isinstance(container, dict):
                continue
            cname = safe_name(container.get("name")) or "UNKNOWN"
            image = container.get("image") if isinstance(container.get("image"), str) else ""
            if backup_signal(cname) or backup_signal(image):
                signal = True
            if image and len(image) <= 300:
                safe_images.append(image.split("@", 1)[0])
        if signal:
            rows.append({"namespace": namespace, "kind": kind, "name": name, "images": sorted(set(safe_images))})

    rows.sort(key=lambda row: (row["namespace"], row["kind"], row["name"]))
    return "COMPLETE", rows


def management_host_metadata() -> dict[str, Any]:
    tools = {tool: (shutil.which(tool) is not None) for tool in BACKUP_TOOLS}

    rc, unit_text, _ = run_text(["systemctl", "list-unit-files", "--no-legend", "--no-pager"])
    unit_status = "COMPLETE" if rc == 0 else "FAILED_TO_OBSERVE"
    matching_units: list[str] = []
    instantiated_units: list[str] = []
    template_units: list[str] = []
    if rc == 0:
        for line in unit_text.splitlines():
            parts = line.split()
            unit = safe_name(parts[0]) if parts else None
            if not unit or not backup_signal(unit):
                continue
            matching_units.append(unit)
            if "@." in unit:
                template_units.append(unit)
            else:
                instantiated_units.append(unit)

    rc, timer_text, _ = run_text(["systemctl", "list-timers", "--all", "--no-legend", "--no-pager"])
    timer_status = "COMPLETE" if rc == 0 else "FAILED_TO_OBSERVE"
    active_matching_timers: list[str] = []
    if rc == 0:
        for line in timer_text.splitlines():
            for token in line.split():
                unit = safe_name(token)
                if unit and unit.endswith(".timer") and backup_signal(unit):
                    active_matching_timers.append(unit)

    cron_names: list[str] = []
    cron_observation_failures = 0
    for directory in CRON_DIRS:
        try:
            entries = list(directory.iterdir()) if directory.exists() else []
        except OSError:
            cron_observation_failures += 1
            continue
        for entry in entries:
            name = safe_name(entry.name)
            if name and backup_signal(name):
                cron_names.append(f"{directory.name}/{name}")

    configured_signals = sorted(set(instantiated_units + active_matching_timers + cron_names))
    return {
        "tools": tools,
        "unit_status": unit_status,
        "matching_units": sorted(set(matching_units)),
        "template_units": sorted(set(template_units)),
        "instantiated_units": sorted(set(instantiated_units)),
        "timer_status": timer_status,
        "active_matching_timers": sorted(set(active_matching_timers)),
        "cron_names": sorted(set(cron_names)),
        "cron_observation_failures": cron_observation_failures,
        "configured_mechanism_status": "DECLARED_SIGNAL_OBSERVED" if configured_signals else "DATABASE_BACKUP_MECHANISM_UNKNOWN",
    }


def main() -> int:
    print("===== MARIADB DATABASE-AWARE BACKUP SOURCE DISCOVERY =====")

    print("\n===== KUBERNETES ACCEPTED MARIADB CANDIDATES =====")
    workload_results: list[dict[str, Any]] = []
    for namespace, kind, name in EXPECTED_WORKLOADS:
        rc, obj, error = run_json(["kubectl", "get", kind.lower(), name, "-n", namespace, "-o", "json"])
        subject = f"{namespace}/{kind}/{name}"
        if rc != 0 or not isinstance(obj, dict):
            print(f"{subject} observation=FAILED_TO_OBSERVE error={error or 'UNKNOWN'}")
            workload_results.append({"subject": subject, "status": "FAILED_TO_OBSERVE"})
            continue

        projection = workload_projection(obj)
        workload_results.append({"subject": subject, "status": "OBSERVED", **projection})
        bc = ",".join(projection["backup_container_signals"]) or "NONE"
        bi = ",".join(projection["backup_init_signals"]) or "NONE"
        cm = ",".join(projection["backup_configmap_signals"]) or "NONE"
        print(
            f"{subject} observation=OBSERVED containers={projection['container_count']} "
            f"init_containers={projection['init_container_count']} pvc_volumes={projection['pvc_volume_count']} "
            f"secret_refs_present={projection['secret_reference_count']} backup_container_signals={bc} "
            f"backup_init_signals={bi} backup_configmap_signals={cm} "
            f"database_backup_mechanism={projection['database_backup_mechanism_status']}"
        )

    print("\n===== KUBERNETES MARIADB BACKUP JOB SIGNALS =====")
    job_status, job_rows = cronjob_job_candidates()
    print("cronjob_job_source_status:", job_status)
    print("matching_cronjobs_jobs:", len(job_rows))
    for row in job_rows:
        images = ",".join(row["images"]) or "NONE"
        print(f"{row['namespace']}/{row['kind']}/{row['name']} images={images}")

    print("\n===== MANAGEMENT HOST MARIADB BACKUP METADATA =====")
    host = management_host_metadata()
    for tool, present in host["tools"].items():
        print(f"tool_{tool}: {'PRESENT' if present else 'NOT_PRESENT'}")
    print("systemd_unit_source_status:", host["unit_status"])
    print("matching_systemd_units:", ",".join(host["matching_units"]) or "NONE")
    print("template_only_units:", ",".join(host["template_units"]) or "NONE")
    print("instantiated_matching_units:", ",".join(host["instantiated_units"]) or "NONE")
    print("systemd_timer_source_status:", host["timer_status"])
    print("active_matching_timers:", ",".join(host["active_matching_timers"]) or "NONE")
    print("matching_cron_filenames:", ",".join(host["cron_names"]) or "NONE")
    print("cron_directory_observation_failures:", host["cron_observation_failures"])
    print("management_host_database_backup_mechanism:", host["configured_mechanism_status"])

    observed = sum(row.get("status") == "OBSERVED" for row in workload_results)
    failed = sum(row.get("status") == "FAILED_TO_OBSERVE" for row in workload_results)
    declared = sum(row.get("database_backup_mechanism_status") == "DECLARED_SIGNAL_OBSERVED" for row in workload_results)
    unknown = sum(row.get("database_backup_mechanism_status") == "DATABASE_BACKUP_MECHANISM_UNKNOWN" for row in workload_results)

    print("\n===== SUMMARY =====")
    print("expected_kubernetes_mariadb_candidates:", len(EXPECTED_WORKLOADS))
    print("kubernetes_candidates_observed:", observed)
    print("kubernetes_candidates_failed_to_observe:", failed)
    print("kubernetes_candidates_with_declared_backup_signal:", declared)
    print("kubernetes_candidates_database_backup_mechanism_unknown:", unknown)
    print("matching_kubernetes_cronjobs_jobs:", len(job_rows))
    print("management_host_configured_backup_signal:", 1 if host["configured_mechanism_status"] == "DECLARED_SIGNAL_OBSERVED" else 0)
    print("backup_execution_success_claims: 0")
    print("backup_artifact_validity_claims: 0")
    print("retention_effectiveness_claims: 0")
    print("restore_verification_claims: 0")
    print("unprotected_claims: 0")
    print("rpo_violation_claims: 0")

    print("\n===== INTERPRETATION BOUNDARY =====")
    print("A backup-looking container/image, ConfigMap name, systemd unit, timer, cron filename, or installed tool is mechanism/source metadata only.")
    print("Tool presence alone is backup capability, not configured execution and not successful database-aware backup evidence.")
    print("Absence of a signal in this bounded safe projection is DATABASE_BACKUP_MECHANISM_UNKNOWN, not UNPROTECTED.")
    print("No database connection, dump inspection, backup-content inspection, retention-effectiveness, restore, RPO, or RTO inference is performed.")

    print("\n===== TRUST BOUNDARY =====")
    print("Kubernetes env values, Secret names/keys/values, command/args, raw ConfigMap contents, and raw workload objects were not printed.")
    print("Management-host cron contents, script contents, database rows, dumps, credentials, and connection strings were not read or printed.")
    print("Only read-only Kubernetes/system metadata and local executable presence were inspected.")
    print("No mutation was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
