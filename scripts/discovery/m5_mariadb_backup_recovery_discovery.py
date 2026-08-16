from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from infra_assurance.proxmox_ve_backup_evidence import build_getter_from_env
from infra_assurance.vm_last_successful_backup_integration import (
    build_vm_last_successful_backup_integration,
)

ENV_FILE = Path(
    "/home/ben/projects/afpa-infra-rebuild/mcp/proxmox/proxmox.env"
)
VM_SOURCE = Path("/tmp/vm-backup-assurance.json")
TASK_SOURCE = Path("/tmp/proxmox-ve-backup-task-results.json")

EXPECTED_HASHES = {
    VM_SOURCE: "14ccd7a082a6c901df6941e4c0540d24bd13ff96f29146a0e6ad689d4f824c1a",
    TASK_SOURCE: "18aaa4ad1a2dd260b4d0678e830f3c9267b2afaa1014b3563ec0e78a2b0135de",
}

DB_IMAGE_TOKENS = (
    "mariadb",
    "mysql",
    "percona",
)

BACKUP_SIGNAL_TOKENS = (
    "mariadb",
    "mysql",
    "percona",
    "backup",
    "dump",
    "xtrabackup",
    "mariabackup",
)


def _run(args: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(
        args,
        text=True,
        capture_output=True,
    )
    return result.returncode, result.stdout, result.stderr


def _run_required(args: list[str], label: str) -> str:
    rc, stdout, _ = _run(args)
    if rc != 0:
        print(f"{label}: FAILED_TO_OBSERVE rc={rc}")
        return ""
    return stdout


def _parse_owner_text(value: str) -> list[tuple[str, str]]:
    owners: list[tuple[str, str]] = []
    for item in value.split(","):
        item = item.strip()
        if not item or "=" not in item:
            continue
        kind, name = item.split("=", 1)
        if kind and name:
            owners.append((kind, name))
    return owners


def _contains_any(value: str, tokens: tuple[str, ...]) -> bool:
    lowered = value.lower()
    return any(token in lowered for token in tokens)


def _replicaset_parent_map() -> dict[tuple[str, str], tuple[str, str]]:
    output = _run_required(
        [
            "kubectl",
            "get",
            "replicasets",
            "-A",
            "-o",
            "jsonpath="
            "{range .items[*]}"
            "{.metadata.namespace}{\"\\t\"}"
            "{.metadata.name}{\"\\t\"}"
            "{range .metadata.ownerReferences[*]}"
            "{.kind}{\"=\"}{.name}{\",\"}"
            "{end}{\"\\n\"}"
            "{end}",
        ],
        "ReplicaSet projection",
    )

    result: dict[tuple[str, str], tuple[str, str]] = {}
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        owners = _parse_owner_text(parts[2])
        if owners:
            result[(parts[0], parts[1])] = owners[0]
    return result


def _pod_identities(
    rs_parent: dict[tuple[str, str], tuple[str, str]],
) -> list[dict[str, str]]:
    output = _run_required(
        [
            "kubectl",
            "get",
            "pods",
            "-A",
            "-o",
            "jsonpath="
            "{range .items[*]}"
            "{.metadata.namespace}{\"\\t\"}"
            "{.metadata.name}{\"\\t\"}"
            "{.status.phase}{\"\\t\"}"
            "{.spec.nodeName}{\"\\t\"}"
            "{range .metadata.ownerReferences[*]}"
            "{.kind}{\"=\"}{.name}{\",\"}"
            "{end}{\"\\n\"}"
            "{end}",
        ],
        "Pod identity projection",
    )

    pods: list[dict[str, str]] = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 5:
            continue

        owners = _parse_owner_text(parts[4])
        owner_kind = "UNKNOWN"
        owner_name = "UNKNOWN"

        if owners:
            owner_kind, owner_name = owners[0]
            if owner_kind == "ReplicaSet":
                parent = rs_parent.get((parts[0], owner_name))
                if parent:
                    owner_kind, owner_name = parent

        pods.append(
            {
                "namespace": parts[0],
                "pod": parts[1],
                "phase": parts[2],
                "node": parts[3],
                "owner_kind": owner_kind,
                "owner_name": owner_name,
            }
        )
    return pods


def _container_candidates(namespace: str, pod: str) -> list[dict[str, Any]]:
    containers = _run_required(
        [
            "kubectl",
            "get",
            "pod",
            pod,
            "-n",
            namespace,
            "-o",
            "jsonpath="
            "{range .spec.containers[*]}"
            "{.name}{\"\\t\"}"
            "{.image}{\"\\t\"}"
            "{range .volumeMounts[*]}{.name}{\",\"}{end}"
            "{\"\\n\"}"
            "{end}",
        ],
        f"Container projection {namespace}/{pod}",
    )

    volumes = _run_required(
        [
            "kubectl",
            "get",
            "pod",
            pod,
            "-n",
            namespace,
            "-o",
            "jsonpath="
            "{range .spec.volumes[*]}"
            "{.name}{\"\\t\"}"
            "{.persistentVolumeClaim.claimName}"
            "{\"\\n\"}"
            "{end}",
        ],
        f"PVC volume projection {namespace}/{pod}",
    )

    claims_by_volume: dict[str, str] = {}
    for line in volumes.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        if parts[1].strip():
            claims_by_volume[parts[0]] = parts[1].strip()

    candidates: list[dict[str, Any]] = []
    for line in containers.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue

        name = parts[0]
        image = parts[1]
        if not _contains_any(image, DB_IMAGE_TOKENS):
            continue

        mounts = []
        if len(parts) >= 3:
            mounts = [value for value in parts[2].split(",") if value]

        claims = sorted(
            {
                claims_by_volume[mount]
                for mount in mounts
                if mount in claims_by_volume
            }
        )

        candidates.append(
            {
                "container": name,
                "image": image,
                "claims": claims,
            }
        )

    return candidates


def _pvc_projection(namespace: str, claim: str) -> dict[str, str]:
    output = _run_required(
        [
            "kubectl",
            "get",
            "pvc",
            claim,
            "-n",
            namespace,
            "-o",
            "jsonpath="
            "{.status.phase}{\"\\t\"}"
            "{.spec.storageClassName}{\"\\t\"}"
            "{.spec.volumeName}{\"\\n\"}",
        ],
        f"PVC projection {namespace}/{claim}",
    ).strip()

    parts = output.split("\t")
    if len(parts) != 3:
        return {
            "phase": "FAILED_TO_OBSERVE",
            "storage_class": "UNKNOWN",
            "pv": "UNKNOWN",
        }

    return {
        "phase": parts[0] or "UNKNOWN",
        "storage_class": parts[1] or "UNKNOWN",
        "pv": parts[2] or "UNKNOWN",
    }


def _pv_storage_node(pv: str) -> str:
    if pv in ("", "UNKNOWN"):
        return "UNKNOWN"

    output = _run_required(
        [
            "kubectl",
            "get",
            "pv",
            pv,
            "-o",
            "go-template="
            "{{range .spec.nodeAffinity.required.nodeSelectorTerms}}"
            "{{range .matchExpressions}}"
            "{{if and (eq .key \"kubernetes.io/hostname\") "
            "(eq .operator \"In\")}}"
            "{{range .values}}{{.}}{{\"\\n\"}}{{end}}"
            "{{end}}"
            "{{end}}"
            "{{end}}",
        ],
        f"PV node affinity {pv}",
    )

    values = sorted({line.strip() for line in output.splitlines() if line.strip()})
    if len(values) == 1:
        return values[0]
    return "UNKNOWN"


def _discover_kubernetes_candidates() -> list[dict[str, Any]]:
    rs_parent = _replicaset_parent_map()
    pods = _pod_identities(rs_parent)
    rows: list[dict[str, Any]] = []

    for pod in pods:
        if pod["phase"] != "Running":
            continue

        candidates = _container_candidates(pod["namespace"], pod["pod"])
        for candidate in candidates:
            pvc_rows = []
            for claim in candidate["claims"]:
                pvc = _pvc_projection(pod["namespace"], claim)
                pvc["claim"] = claim
                pvc["storage_node"] = _pv_storage_node(pvc["pv"])
                pvc_rows.append(pvc)

            rows.append(
                {
                    **pod,
                    "container": candidate["container"],
                    "image": candidate["image"],
                    "pvcs": pvc_rows,
                }
            )

    return rows


def _workload_signal_rows(kind: str) -> list[dict[str, str]]:
    if kind == "cronjob":
        args = [
            "kubectl",
            "get",
            "cronjobs",
            "-A",
            "-o",
            "jsonpath="
            "{range .items[*]}"
            "{.metadata.namespace}{\"\\t\"}"
            "{.metadata.name}{\"\\t\"}"
            "{.spec.schedule}{\"\\t\"}"
            "{range .spec.jobTemplate.spec.template.spec.containers[*]}"
            "{.image}{\",\"}"
            "{end}{\"\\n\"}"
            "{end}",
        ]
    else:
        args = [
            "kubectl",
            "get",
            "jobs",
            "-A",
            "-o",
            "jsonpath="
            "{range .items[*]}"
            "{.metadata.namespace}{\"\\t\"}"
            "{.metadata.name}{\"\\t\"}"
            "{.status.succeeded}{\"\\t\"}"
            "{.status.failed}{\"\\t\"}"
            "{.status.completionTime}{\"\\t\"}"
            "{range .spec.template.spec.containers[*]}"
            "{.image}{\",\"}"
            "{end}{\"\\n\"}"
            "{end}",
        ]

    output = _run_required(args, f"{kind} safe projection")
    matches: list[dict[str, str]] = []

    for line in output.splitlines():
        parts = line.split("\t")
        joined = " ".join(parts)
        if not _contains_any(joined, BACKUP_SIGNAL_TOKENS):
            continue

        if kind == "cronjob" and len(parts) >= 4:
            matches.append(
                {
                    "namespace": parts[0],
                    "name": parts[1],
                    "schedule": parts[2],
                    "images": parts[3],
                }
            )
        elif kind == "job" and len(parts) >= 6:
            matches.append(
                {
                    "namespace": parts[0],
                    "name": parts[1],
                    "succeeded": parts[2] or "0",
                    "failed": parts[3] or "0",
                    "completion_time": parts[4] or "UNKNOWN",
                    "images": parts[5],
                }
            )

    return matches


def _local_mariadb_signals() -> None:
    print()
    print("===== MANAGEMENT HOST MARIADB SIGNALS =====")

    for unit in ("mariadb.service", "mysql.service"):
        rc, stdout, _ = _run(
            [
                "systemctl",
                "show",
                unit,
                "--no-pager",
                "-p",
                "LoadState",
                "-p",
                "ActiveState",
                "-p",
                "SubState",
            ]
        )
        if rc != 0:
            print(f"{unit}: FAILED_TO_OBSERVE")
            continue
        values = {}
        for line in stdout.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value
        print(
            f"{unit}: load={values.get('LoadState', 'UNKNOWN')} "
            f"active={values.get('ActiveState', 'UNKNOWN')} "
            f"sub={values.get('SubState', 'UNKNOWN')}"
        )

    for command in (
        "mariadb",
        "mysql",
        "mariadb-dump",
        "mysqldump",
        "mariadb-backup",
        "xtrabackup",
    ):
        print(f"tool_{command}: {'PRESENT' if shutil.which(command) else 'NOT_PRESENT'}")


def _verify_vm_sources() -> dict[Path, dict[str, Any]] | None:
    objects: dict[Path, dict[str, Any]] = {}
    print()
    print("===== ACCEPTED VM SOURCE VERIFICATION =====")

    for path, expected in EXPECTED_HASHES.items():
        if not path.exists():
            print(f"{path}: NOT_FOUND")
            return None
        try:
            raw = path.read_bytes()
            actual = hashlib.sha256(raw).hexdigest()
            payload = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            print(f"{path}: FAILED_TO_READ")
            return None

        matched = actual == expected
        print(f"{path}: hash_match={matched}")
        if not matched:
            return None
        objects[path] = payload

    return objects


def _pve_and_vm_recovery(rows: list[dict[str, Any]]) -> None:
    storage_nodes = sorted(
        {
            pvc["storage_node"]
            for row in rows
            for pvc in row["pvcs"]
            if pvc["storage_node"] not in ("", "UNKNOWN")
        }
    )

    print()
    print("===== BOUNDED PVE NODE MAPPING =====")
    print("storage_nodes_to_map:", len(storage_nodes))

    if not storage_nodes:
        print("pve_mapping_status: NOT_REQUIRED_OR_NOT_OBSERVABLE")
        return

    try:
        getter, trust = build_getter_from_env(
            ENV_FILE,
            allow_discovery_credential=True,
            allow_insecure_tls_discovery=True,
        )
    except Exception as exc:
        print("pve_mapping_status: FAILED_TO_OBSERVE")
        print("error_class:", type(exc).__name__)
        return

    status, data, error = getter(
        "/api2/json/cluster/resources",
        {"type": "vm"},
    )

    print("operation: GET /cluster/resources?type=vm")
    print("http_status:", status if status is not None else "NONE")
    print("runtime_credential_approved:", trust["runtime_credential_approved"])

    if status != 200 or not isinstance(data, list):
        print("pve_mapping_status: FAILED_TO_OBSERVE")
        print("error_class:", error or "UNKNOWN")
        return

    mapping: dict[str, dict[str, Any]] = {}
    for node_name in storage_nodes:
        matches = [
            item
            for item in data
            if isinstance(item, dict)
            and item.get("name") == node_name
        ]
        if len(matches) != 1:
            mapping[node_name] = {"status": "UNKNOWN"}
            continue

        item = matches[0]
        mapping[node_name] = {
            "status": "OBSERVED",
            "vmid": item.get("vmid"),
            "pve_node": item.get("node") or "UNKNOWN",
            "runtime_status": item.get("status") or "UNKNOWN",
        }

    sources = _verify_vm_sources()
    vm_assurance = None
    if sources is not None:
        try:
            vm_assurance = build_vm_last_successful_backup_integration(
                sources[VM_SOURCE],
                sources[TASK_SOURCE],
            )
        except Exception as exc:
            print("vm_assurance_derivation: FAILED")
            print("error_class:", type(exc).__name__)

    vm_index: dict[int, dict[str, Any]] = {}
    if isinstance(vm_assurance, dict):
        for asset in vm_assurance.get("assets", []):
            if not isinstance(asset, dict):
                continue
            vmid = asset.get("subject", {}).get("vmid")
            if isinstance(vmid, int) and not isinstance(vmid, bool):
                vm_index[vmid] = asset

    for node_name in storage_nodes:
        item = mapping[node_name]
        if item["status"] != "OBSERVED":
            print(f"{node_name}: mapping=UNKNOWN")
            continue

        vmid = item.get("vmid")
        vm_asset = vm_index.get(vmid) if isinstance(vmid, int) else None
        if vm_asset is None:
            print(
                f"{node_name}: vmid={vmid or 'UNKNOWN'} "
                "mapping=OBSERVED vm_backup=UNKNOWN"
            )
            continue

        assurance = vm_asset.get("assurance", {})
        print(
            f"{node_name}: vmid={vmid} mapping=OBSERVED "
            f"vm_backup={assurance.get('last_successful_backup_status', 'UNKNOWN')} "
            f"latest={assurance.get('last_successful_backup_at') or 'UNKNOWN'}"
        )


def main() -> int:
    print("===== MARIADB / MYSQL-COMPATIBLE BACKUP RECOVERY DISCOVERY =====")

    rc, context, _ = _run(["kubectl", "config", "current-context"])
    print()
    print("===== KUBERNETES CONTEXT =====")
    print("context:", context.strip() if rc == 0 else "FAILED_TO_OBSERVE")

    rows = _discover_kubernetes_candidates()

    print()
    print("===== KUBERNETES DB CANDIDATES =====")
    print("candidate_containers:", len(rows))

    for row in sorted(
        rows,
        key=lambda value: (
            value["namespace"],
            value["owner_kind"],
            value["owner_name"],
            value["container"],
        ),
    ):
        if row["pvcs"]:
            pvc_text = ";".join(
                f"{pvc['claim']}:{pvc['phase']}:"
                f"{pvc['storage_class']}:{pvc['storage_node']}"
                for pvc in row["pvcs"]
            )
        else:
            pvc_text = "NONE_OBSERVED"

        print(
            f"{row['namespace']}/{row['owner_kind']}/{row['owner_name']} "
            f"pod={row['pod']} node={row['node']} "
            f"container={row['container']} image={row['image']} "
            f"pvcs={pvc_text}"
        )

    cronjobs = _workload_signal_rows("cronjob")
    jobs = _workload_signal_rows("job")

    print()
    print("===== KUBERNETES BACKUP SIGNALS =====")
    print("matching_cronjobs:", len(cronjobs))
    for item in cronjobs:
        print(
            f"cronjob {item['namespace']}/{item['name']} "
            f"schedule={item['schedule']} images={item['images']}"
        )

    print("matching_jobs:", len(jobs))
    for item in jobs:
        print(
            f"job {item['namespace']}/{item['name']} "
            f"succeeded={item['succeeded']} failed={item['failed']} "
            f"completion={item['completion_time']} images={item['images']}"
        )

    _pve_and_vm_recovery(rows)
    _local_mariadb_signals()

    print()
    print("===== INTERPRETATION BOUNDARY =====")
    print(
        "A MariaDB/MySQL-compatible image identifies a database candidate, not a "
        "database-aware backup mechanism."
    )
    print(
        "PVC and VM recovery evidence are infrastructure context only and do not "
        "prove MariaDB-consistent backup or restore viability."
    )
    print(
        "CronJob/Job name or image matches are bounded signals only; absence is not "
        "UNPROTECTED, and Job success is not integrity or restore verification."
    )
    print(
        "Timestamp age is not classified as stale or an RPO violation without an "
        "accepted target."
    )

    print()
    print("===== TRUST BOUNDARY =====")
    print("No Kubernetes Secret values, environment values, commands, or args were read.")
    print("No PV backing paths or CSI handles were read.")
    print("No database connection, row read, dump read, backup, or restore was performed.")
    print("No raw PVE VM config, disk, network, or credential value was read or printed.")
    print("Only GET/read-only observations were used; no infrastructure mutation occurred.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
