from __future__ import annotations

import json
import os
import runpy
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

from infra_assurance import __version__
from infra_assurance.mariadb_infrastructure_recovery_context import (
    build_mariadb_infrastructure_recovery_context,
    render_mariadb_infrastructure_recovery_markdown,
)
from infra_assurance.proxmox_ve_backup_evidence import build_getter_from_env
from infra_assurance.vm_last_successful_backup_integration import (
    build_vm_last_successful_backup_integration,
)

ROOT = Path.cwd()
DISCOVERY_SCRIPT = ROOT / "scripts/discovery/m5_mariadb_backup_recovery_discovery.py"
SCHEMA = ROOT / "schemas/mariadb-infrastructure-recovery-context.schema.json"
RELATIONSHIP_OUT = Path("/tmp/mariadb-infrastructure-relationship-evidence.json")
VM_OUT = Path("/tmp/mariadb-vm-backup-assurance-v0.2.json")
CONTEXT_OUT = Path("/tmp/mariadb-infrastructure-recovery-context.json")
SUMMARY_OUT = Path("/tmp/mariadb-infrastructure-recovery-context.md")

EXPECTED_SUBJECTS = {
    ("bookstack", "Deployment", "mariadb"),
    ("misp", "Deployment", "mariadb"),
    ("misp", "Deployment", "mariadb-v2"),
    ("moodle", "StatefulSet", "moodle-mariadb"),
}

EXPECTED_SUMMARY = {
    "instances_total": 4,
    "persistence_observed": 3,
    "persistence_unknown": 1,
    "persistence_failed_to_observe": 0,
    "infrastructure_recovery_observed": 3,
    "infrastructure_recovery_unknown": 1,
    "infrastructure_recovery_failed_to_observe": 0,
    "underlying_vm_last_successful_backup_observed": 3,
    "mariadb_protection_unknown": 4,
    "mariadb_backup_mechanism_unknown": 4,
    "mariadb_backup_execution_unknown": 4,
    "mariadb_restore_verification_unknown": 4,
    "mariadb_integrity_verification_unknown": 4,
    "mariadb_rpo_unknown": 4,
    "mariadb_rto_unknown": 4,
    "unprotected_claims": 0,
    "backup_stale_claims": 0,
    "rpo_violation_claims": 0,
}

EXPECTED_VM_TIMESTAMPS = {
    106: "2026-08-14T16:39:53Z",
    108: "2026-04-15T12:36:38Z",
}


def stop(stage: str, detail: str, rc: int = 2) -> None:
    print()
    print("===== GATE REJECTED =====")
    print("stage:", stage)
    print("detail:", detail)
    print("No infrastructure mutation was performed by this gate.")
    raise SystemExit(rc)


def run_tests() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        text=True,
        capture_output=True,
    )
    if result.stdout:
        print(result.stdout.rstrip())
    if result.returncode != 0:
        stop("repository tests", f"pytest rc={result.returncode}")


def load_discovery_namespace() -> dict[str, Any]:
    if not DISCOVERY_SCRIPT.exists():
        stop("discovery script", "NOT_FOUND")
    return runpy.run_path(str(DISCOVERY_SCRIPT), run_name="m5_mariadb_discovery_lib")


def build_relationship(rows: list[dict[str, Any]], ns: dict[str, Any]) -> dict[str, Any]:
    observed_subjects = {
        (row["namespace"], row["owner_kind"], row["owner_name"])
        for row in rows
    }
    if observed_subjects != EXPECTED_SUBJECTS:
        stop(
            "MariaDB candidate scope",
            f"live subject set changed: observed={len(observed_subjects)} expected=4",
            rc=3,
        )

    persistent_nodes = sorted(
        {
            pvc["storage_node"]
            for row in rows
            for pvc in row["pvcs"]
            if pvc.get("phase") == "Bound"
            and pvc.get("storage_node") not in (None, "", "UNKNOWN")
        }
    )

    try:
        getter, trust = build_getter_from_env(
            ns["ENV_FILE"],
            allow_discovery_credential=True,
            allow_insecure_tls_discovery=True,
        )
    except Exception as exc:
        stop("PVE getter", type(exc).__name__)

    status, data, error = getter(
        "/api2/json/cluster/resources",
        {"type": "vm"},
    )
    print("PVE GET /cluster/resources?type=vm http_status:", status)
    print("runtime_credential_approved:", trust["runtime_credential_approved"])
    if status != 200 or not isinstance(data, list):
        stop("PVE node mapping", error or "FAILED_TO_OBSERVE")

    node_mapping: dict[str, dict[str, Any]] = {}
    for node_name in persistent_nodes:
        matches = [
            item
            for item in data
            if isinstance(item, dict) and item.get("name") == node_name
        ]
        if len(matches) != 1:
            node_mapping[node_name] = {"status": "UNKNOWN"}
            continue
        item = matches[0]
        vmid = item.get("vmid")
        if isinstance(vmid, bool) or not isinstance(vmid, int) or vmid < 1:
            node_mapping[node_name] = {"status": "UNKNOWN"}
            continue
        node_mapping[node_name] = {
            "status": "OBSERVED",
            "kubernetes_node": node_name,
            "pve_source_id": "pve-bm2",
            "pve_node": item.get("node") or "UNKNOWN",
            "vmid": vmid,
        }

    instances = []
    for row in sorted(
        rows,
        key=lambda value: (
            value["namespace"],
            value["owner_kind"],
            value["owner_name"],
        ),
    ):
        subject = {
            "system": "kubernetes",
            "cluster": "k3s-main",
            "database_engine": "MARIADB_COMPATIBLE",
            "namespace": row["namespace"],
            "workload_kind": row["owner_kind"],
            "workload_name": row["owner_name"],
            "container_name": row["container"],
            "image": row["image"],
        }

        persistence = {
            "status": "UNKNOWN",
            "pvc_name": None,
            "pvc_phase": None,
            "storage_class": None,
            "pv_name": None,
            "storage_node": None,
        }
        mapping = {
            "status": "UNKNOWN",
            "kubernetes_node": None,
            "pve_source_id": None,
            "pve_node": None,
            "vmid": None,
        }

        if len(row["pvcs"]) == 1:
            pvc = row["pvcs"][0]
            if (
                pvc.get("phase") == "Bound"
                and pvc.get("storage_class") not in (None, "", "UNKNOWN")
                and pvc.get("pv") not in (None, "", "UNKNOWN")
                and pvc.get("storage_node") not in (None, "", "UNKNOWN")
            ):
                persistence = {
                    "status": "OBSERVED",
                    "pvc_name": pvc["claim"],
                    "pvc_phase": pvc["phase"],
                    "storage_class": pvc["storage_class"],
                    "pv_name": pvc["pv"],
                    "storage_node": pvc["storage_node"],
                }
                mapped = node_mapping.get(pvc["storage_node"], {"status": "UNKNOWN"})
                if mapped.get("status") == "OBSERVED":
                    mapping = mapped

        instance_id = (
            "mariadb:kubernetes:k3s-main:"
            f"{row['namespace']}:{row['owner_kind']}:{row['owner_name']}"
        )
        instances.append(
            {
                "instance_id": instance_id,
                "subject": subject,
                "instance_observation_status": "OBSERVED",
                "persistence": persistence,
                "node_vm_mapping": mapping,
                "evidence_ids": [
                    "mariadb-kubernetes-safe-projection:2026-08-16",
                ],
            }
        )

    return {
        "mariadb_infrastructure_relationship_evidence_version": "0.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mutation_allowed": False,
        "cluster_id": "k3s-main",
        "source": {
            "type": "BOUNDED_KUBERNETES_PVE_RELATIONSHIP_OBSERVATION",
            "source_id": "m5-mariadb-live-gate",
            "status": "COMPLETE",
        },
        "instances": instances,
    }


def main() -> int:
    print("===== MARIADB INFRASTRUCTURE RECOVERY CONTEXT LIVE GATE =====")
    print()
    print("===== PACKAGE =====")
    print("package:", __version__)
    if __version__ != "0.26.0":
        stop("package", f"expected 0.26.0 got {__version__}")

    print()
    print("===== FULL REPOSITORY TESTS =====")
    run_tests()
    print("repository gate: PASS")

    ns = load_discovery_namespace()
    rows = ns["_discover_kubernetes_candidates"]()
    print()
    print("===== LIVE MARIADB CANDIDATES =====")
    print("candidate_containers:", len(rows))

    relationship = build_relationship(rows, ns)
    RELATIONSHIP_OUT.write_text(json.dumps(relationship, indent=2, sort_keys=True) + "\n")

    print()
    print("===== RELATIONSHIP SUMMARY =====")
    for item in relationship["instances"]:
        subject = item["subject"]
        persistence = item["persistence"]
        mapping = item["node_vm_mapping"]
        print(
            f"{subject['namespace']}/{subject['workload_kind']}/{subject['workload_name']}"
            f" persistence={persistence['status']}"
            f" pvc={persistence['pvc_name'] or 'UNKNOWN'}"
            f" storage_node={persistence['storage_node'] or 'UNKNOWN'}"
            f" vmid={mapping['vmid'] if mapping['vmid'] is not None else 'UNKNOWN'}"
        )

    sources = ns["_verify_vm_sources"]()
    if sources is None:
        stop("accepted VM sources", "verification failed")
    try:
        vm_assurance = build_vm_last_successful_backup_integration(
            sources[ns["VM_SOURCE"]],
            sources[ns["TASK_SOURCE"]],
        )
    except Exception as exc:
        stop("VM assurance derivation", type(exc).__name__)
    VM_OUT.write_text(json.dumps(vm_assurance, indent=2, sort_keys=True) + "\n")

    context = build_mariadb_infrastructure_recovery_context(
        relationship,
        vm_assurance,
    )
    schema = json.loads(SCHEMA.read_text())
    jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    ).validate(context)
    CONTEXT_OUT.write_text(json.dumps(context, indent=2, sort_keys=True) + "\n")
    SUMMARY_OUT.write_text(render_mariadb_infrastructure_recovery_markdown(context))

    print()
    print("===== DERIVED CONTEXT =====")
    print("schema: PASS")
    for key, value in context["summary"].items():
        print(f"{key}: {value}")

    print()
    print("===== INSTANCE CONTEXT =====")
    timestamps_ok = True
    for item in context["instances"]:
        subject = item["subject"]
        persistence = item["persistence"]
        recovery = item["infrastructure_recovery"]
        vmid = recovery["vmid"]
        latest = recovery["underlying_vm_last_successful_backup_at"]
        if vmid in EXPECTED_VM_TIMESTAMPS and latest != EXPECTED_VM_TIMESTAMPS[vmid]:
            timestamps_ok = False
        print(
            f"{subject['namespace']}/{subject['workload_kind']}/{subject['workload_name']}"
            f" persistence={persistence['status']}"
            f" infrastructure_recovery={recovery['relationship_status']}"
            f" vmid={vmid if vmid is not None else 'UNKNOWN'}"
            f" latest={latest or 'UNKNOWN'}"
            f" mariadb_protection={item['mariadb_assurance']['protection_status']}"
        )

    summary_ok = all(
        context["summary"].get(key) == expected
        for key, expected in EXPECTED_SUMMARY.items()
    )
    print("accepted_vm_timestamps_match:", timestamps_ok)
    print("acceptance_counters_match:", summary_ok)

    print()
    print("===== TRUST BOUNDARY =====")
    print(
        "OBSERVED infrastructure recovery means a persistent MariaDB-compatible workload "
        "was related to a PVE VM with accepted strict VM last-successful-backup evidence."
    )
    print(
        "It does not mean MariaDB-consistent backup, database restore verification, "
        "integrity, retention, RPO, or RTO assurance."
    )
    print(
        "The persistence-unknown misp/mariadb-v2 candidate is not classified UNPROTECTED."
    )
    print(
        "No Kubernetes Secret values, env values, commands/args, PV backing paths, CSI "
        "handles, database rows, dumps, raw PVE VM config, disks, networks, or credentials "
        "were projected."
    )
    print("No infrastructure mutation was performed.")

    if not timestamps_ok:
        stop("accepted VM timestamps", "live derivation differs from accepted VM evidence", rc=3)
    if not summary_ok:
        stop("acceptance counters", "live state differs from expected bounded discovery", rc=3)

    print()
    print("===== GATE PASS =====")
    print("MariaDB infrastructure recovery context v0.1 is ready for acceptance review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
