from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

from infra_assurance import __version__
from infra_assurance.proxmox_ve_backup_evidence import build_getter_from_env
from infra_assurance.vm_last_successful_backup_integration import (
    build_vm_last_successful_backup_integration,
)

ROOT = Path(__file__).resolve().parents[2]

RELATIONSHIP_OUT = Path("/tmp/postgresql-infrastructure-relationship-evidence.json")
VM_V02_OUT = Path("/tmp/vm-backup-assurance-v0.2.json")
CONTEXT_OUT = Path("/tmp/postgresql-infrastructure-recovery-context.json")
CONTEXT_MD = Path("/tmp/postgresql-infrastructure-recovery-context.md")

VM_SOURCE = Path("/tmp/vm-backup-assurance.json")
TASK_SOURCE = Path("/tmp/proxmox-ve-backup-task-results.json")

EXPECTED_HASHES = {
    VM_SOURCE: "14ccd7a082a6c901df6941e4c0540d24bd13ff96f29146a0e6ad689d4f824c1a",
    TASK_SOURCE: "18aaa4ad1a2dd260b4d0678e830f3c9267b2afaa1014b3563ec0e78a2b0135de",
}

TARGETS = [
    ("drfarah-staging", "StatefulSet", "drfarah-staging-postgres"),
    ("fastapi-platform", "Deployment", "postgres"),
    ("fastapi-platform-dev", "Deployment", "postgres"),
    ("keycloak", "StatefulSet", "keycloak-postgresql"),
    ("openproject", "StatefulSet", "openproject-postgresql"),
    ("soria-academie", "StatefulSet", "academie-postgres"),
    ("soria-prospecting", "Deployment", "soria-postgres"),
    ("toilettage", "StatefulSet", "toilettage-postgres"),
]

EXPECTED_MAPPING = {
    ("drfarah-staging", "StatefulSet", "drfarah-staging-postgres"): ("k3s-worker-02", 108),
    ("fastapi-platform", "Deployment", "postgres"): ("k3s-worker-01", 107),
    ("fastapi-platform-dev", "Deployment", "postgres"): ("k3s-worker-01", 107),
    ("keycloak", "StatefulSet", "keycloak-postgresql"): ("k3s-master-01", 106),
    ("openproject", "StatefulSet", "openproject-postgresql"): ("k3s-worker-01", 107),
    ("soria-academie", "StatefulSet", "academie-postgres"): ("k3s-worker-02", 108),
    ("soria-prospecting", "Deployment", "soria-postgres"): ("k3s-worker-01", 107),
    ("toilettage", "StatefulSet", "toilettage-postgres"): ("k3s-worker-01", 107),
}

EXPECTED_TIMESTAMPS = {
    106: "2026-08-14T16:39:53Z",
    107: "2026-08-14T17:39:32Z",
    108: "2026-04-15T12:36:38Z",
}

PG_TOKENS = ("postgres", "postgresql", "timescale", "pgvector")


def stop(stage: str, detail: str, rc: int = 2) -> None:
    print()
    print("===== GATE REJECTED =====")
    print("stage:", stage)
    print("detail:", detail)
    print("No infrastructure mutation was performed by this gate.")
    raise SystemExit(rc)


def run_text(args: list[str], label: str) -> str:
    result = subprocess.run(args, text=True, capture_output=True)
    if result.returncode != 0:
        stop(label, f"FAILED_TO_OBSERVE rc={result.returncode}")
    return result.stdout


def parse_owner_text(value: str) -> list[tuple[str, str]]:
    owners: list[tuple[str, str]] = []
    for item in value.split(","):
        item = item.strip()
        if not item or "=" not in item:
            continue
        kind, name = item.split("=", 1)
        if kind and name:
            owners.append((kind, name))
    return owners


def pod_container_projection(namespace: str, pod_name: str) -> list[dict[str, object]]:
    container_output = run_text(
        [
            "kubectl",
            "get",
            "pod",
            pod_name,
            "-n",
            namespace,
            "-o",
            "jsonpath={range .spec.containers[*]}{.name}{\"\\t\"}{.image}{\"\\t\"}"
            "{range .volumeMounts[*]}{.name}{\",\"}{end}{\"\\n\"}{end}",
        ],
        f"container projection {namespace}/{pod_name}",
    )
    volume_output = run_text(
        [
            "kubectl",
            "get",
            "pod",
            pod_name,
            "-n",
            namespace,
            "-o",
            "jsonpath={range .spec.volumes[*]}{.name}{\"\\t\"}"
            "{.persistentVolumeClaim.claimName}{\"\\n\"}{end}",
        ],
        f"PVC mount projection {namespace}/{pod_name}",
    )

    volume_claims: dict[str, str] = {}
    for line in volume_output.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        volume_name = parts[0]
        claim_name = parts[1].strip()
        if claim_name:
            volume_claims[volume_name] = claim_name

    candidates: list[dict[str, object]] = []
    for line in container_output.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        container_name = parts[0]
        image = parts[1]
        mounts = [
            value
            for value in (parts[2].split(",") if len(parts) >= 3 else [])
            if value
        ]
        if not any(token in image.lower() for token in PG_TOKENS):
            continue
        claims = sorted(
            {volume_claims[mount] for mount in mounts if mount in volume_claims}
        )
        if claims:
            candidates.append(
                {
                    "container_name": container_name,
                    "image": image,
                    "claims": claims,
                }
            )
    return candidates


def observe_pvc(namespace: str, claim_name: str) -> tuple[str, str, str]:
    output = run_text(
        [
            "kubectl",
            "get",
            "pvc",
            claim_name,
            "-n",
            namespace,
            "-o",
            "jsonpath={.status.phase}{\"\\t\"}{.spec.storageClassName}{\"\\t\"}"
            "{.spec.volumeName}{\"\\n\"}",
        ],
        f"PVC projection {namespace}/{claim_name}",
    ).rstrip("\n")
    parts = output.split("\t")
    if len(parts) != 3:
        stop("PVC projection", f"{namespace}/{claim_name} malformed safe projection")
    phase, storage_class, pv_name = parts
    if phase != "Bound":
        stop("PVC observation", f"{namespace}/{claim_name} phase={phase or 'UNKNOWN'}")
    if not storage_class or not pv_name:
        stop("PVC observation", f"{namespace}/{claim_name} missing storage identity")
    return phase, storage_class, pv_name


def observe_pv_storage_node(pv_name: str) -> str:
    # Go-template projects only hostname-affinity values. It does not output
    # local-path backing paths, CSI handles, annotations, or other PV data.
    template = (
        '{{range .spec.nodeAffinity.required.nodeSelectorTerms}}'
        '{{range .matchExpressions}}'
        '{{if eq .key "kubernetes.io/hostname"}}'
        '{{if eq .operator "In"}}'
        '{{range .values}}{{.}}{{"\\n"}}{{end}}'
        '{{end}}{{end}}{{end}}{{end}}'
    )
    output = run_text(
        ["kubectl", "get", "pv", pv_name, "-o", f"go-template={template}"],
        f"PV affinity projection {pv_name}",
    )
    nodes = sorted({line.strip() for line in output.splitlines() if line.strip()})
    if len(nodes) != 1:
        stop("PV node affinity", f"{pv_name} explicit hostname nodes={len(nodes)}")
    return nodes[0]


def main() -> int:
    os.chdir(ROOT)

    print()
    print("===== PACKAGE =====")
    print("package:", __version__)
    if __version__ != "0.25.0":
        stop("package", f"expected 0.25.0, got {__version__}")

    print()
    print("===== FULL REPOSITORY TESTS =====")
    tests = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        text=True,
        capture_output=True,
    )
    if tests.stdout:
        print(tests.stdout.rstrip())
    if tests.returncode != 0:
        stop("repository tests", f"pytest rc={tests.returncode}")
    print("repository gate: PASS")

    print()
    print("===== KUBERNETES CONTEXT =====")
    context = run_text(
        ["kubectl", "config", "current-context"],
        "kubectl current-context",
    ).strip()
    print("kubectl context:", context)

    print()
    print("===== SAFE KUBERNETES RELATIONSHIP OBSERVATION =====")

    rs_output = run_text(
        [
            "kubectl",
            "get",
            "replicasets",
            "-A",
            "-o",
            "jsonpath={range .items[*]}{.metadata.namespace}{\"\\t\"}{.metadata.name}{\"\\t\"}"
            "{range .metadata.ownerReferences[*]}{.kind}{\"=\"}{.name}{\",\"}{end}{\"\\n\"}{end}",
        ],
        "ReplicaSet projection",
    )
    rs_parent: dict[tuple[str, str], tuple[str, str]] = {}
    for line in rs_output.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        owners = parse_owner_text(parts[2])
        if owners:
            rs_parent[(parts[0], parts[1])] = owners[0]

    pod_output = run_text(
        [
            "kubectl",
            "get",
            "pods",
            "-A",
            "-o",
            "jsonpath={range .items[*]}{.metadata.namespace}{\"\\t\"}{.metadata.name}{\"\\t\"}"
            "{.metadata.deletionTimestamp}{\"\\t\"}{.status.phase}{\"\\t\"}{.spec.nodeName}{\"\\t\"}"
            "{range .metadata.ownerReferences[*]}{.kind}{\"=\"}{.name}{\",\"}{end}{\"\\n\"}{end}",
        ],
        "Pod identity projection",
    )
    pods: list[dict[str, str]] = []
    for line in pod_output.splitlines():
        parts = line.split("\t")
        if len(parts) < 6:
            continue
        owners = parse_owner_text(parts[5])
        if not owners:
            continue
        owner_kind, owner_name = owners[0]
        if owner_kind == "ReplicaSet":
            parent = rs_parent.get((parts[0], owner_name))
            if parent:
                owner_kind, owner_name = parent
        pods.append(
            {
                "namespace": parts[0],
                "pod": parts[1],
                "deleting": parts[2],
                "phase": parts[3],
                "node": parts[4],
                "owner_kind": owner_kind,
                "owner_name": owner_name,
            }
        )

    rows: list[dict[str, object]] = []
    for namespace, workload_kind, workload_name in TARGETS:
        matching_pods = [
            pod
            for pod in pods
            if pod["namespace"] == namespace
            and pod["owner_kind"] == workload_kind
            and pod["owner_name"] == workload_name
            and pod["phase"] == "Running"
            and pod["deleting"] in ("", "<no value>")
        ]
        if len(matching_pods) != 1:
            stop(
                "PostgreSQL workload observation",
                f"{namespace}/{workload_kind}/{workload_name} active_pods={len(matching_pods)}",
            )
        pod = matching_pods[0]
        candidates = pod_container_projection(namespace, pod["pod"])
        if len(candidates) != 1:
            stop(
                "PostgreSQL container observation",
                f"{namespace}/{workload_name} persistent_postgresql_containers={len(candidates)}",
            )
        candidate = candidates[0]
        claims = candidate["claims"]
        if not isinstance(claims, list) or len(claims) != 1:
            stop(
                "PostgreSQL PVC relationship",
                f"{namespace}/{workload_name} mounted_pvc_count="
                f"{len(claims) if isinstance(claims, list) else 'UNKNOWN'}",
            )
        claim_name = str(claims[0])
        phase, storage_class, pv_name = observe_pvc(namespace, claim_name)
        storage_node = observe_pv_storage_node(pv_name)
        if pod["node"] != storage_node:
            stop(
                "Pod/PV node relationship",
                f"{namespace}/{workload_name} pod_node={pod['node']} storage_node={storage_node}",
            )
        rows.append(
            {
                "instance_id": (
                    f"postgresql:kubernetes:k3s-main:{namespace}:{workload_kind}:{workload_name}"
                ),
                "subject": {
                    "system": "kubernetes",
                    "cluster": "k3s-main",
                    "database_engine": "POSTGRESQL",
                    "namespace": namespace,
                    "workload_kind": workload_kind,
                    "workload_name": workload_name,
                    "container_name": candidate["container_name"],
                    "image": candidate["image"],
                },
                "instance_observation_status": "OBSERVED",
                "persistence": {
                    "status": "OBSERVED",
                    "pvc_name": claim_name,
                    "pvc_phase": phase,
                    "storage_class": storage_class,
                    "pv_name": pv_name,
                    "storage_node": storage_node,
                },
                "node_vm_mapping": {},
                "evidence_ids": [],
            }
        )

    print("PostgreSQL persistent workload relationships:", len(rows))

    print()
    print("===== BOUNDED PVE NODE -> VMID OBSERVATION =====")
    env_file = Path(
        "/home/ben/projects/afpa-infra-rebuild/mcp/proxmox/proxmox.env"
    )
    getter, trust = build_getter_from_env(
        env_file,
        allow_discovery_credential=True,
        allow_insecure_tls_discovery=True,
    )
    status, data, error = getter("/api2/json/cluster/resources", {"type": "vm"})
    if status != 200 or not isinstance(data, list):
        stop(
            "PVE guest observation",
            f"FAILED_TO_OBSERVE http_status={status} error_class={error or 'UNKNOWN'}",
        )

    required_nodes = sorted(
        {str(row["persistence"]["storage_node"]) for row in rows}  # type: ignore[index]
    )
    vm_by_name: dict[str, dict[str, object]] = {}
    for node_name in required_nodes:
        matches = [
            item
            for item in data
            if isinstance(item, dict) and item.get("name") == node_name
        ]
        if len(matches) != 1:
            stop(
                "PVE node-to-VM relationship",
                f"{node_name} matching_guests={len(matches)}",
            )
        item = matches[0]
        vmid = item.get("vmid")
        if isinstance(vmid, bool) or not isinstance(vmid, int) or vmid < 1:
            stop("PVE node-to-VM relationship", f"{node_name} VMID invalid")
        vm_by_name[node_name] = {
            "vmid": vmid,
            "pve_node": item.get("node") or "UNKNOWN",
        }

    print("PVE mapped Kubernetes nodes:", len(vm_by_name))
    print("runtime_credential_approved:", trust["runtime_credential_approved"])

    for row in rows:
        persistence = row["persistence"]
        if not isinstance(persistence, dict):
            stop("relationship assembly", "persistence projection is malformed")
        k8s_node = str(persistence["storage_node"])
        mapped = vm_by_name[k8s_node]
        row["node_vm_mapping"] = {
            "status": "OBSERVED",
            "kubernetes_node": k8s_node,
            "pve_source_id": "pve-bm2",
            "pve_node": mapped["pve_node"],
            "vmid": mapped["vmid"],
        }

    relationship = {
        "postgresql_infrastructure_relationship_evidence_version": "0.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mutation_allowed": False,
        "cluster_id": "k3s-main",
        "source": {
            "type": "BOUNDED_KUBERNETES_PVE_RELATIONSHIP_OBSERVATION",
            "source_id": "m5-postgresql-live-gate",
            "status": "COMPLETE",
        },
        "instances": rows,
    }
    RELATIONSHIP_OUT.write_text(
        json.dumps(relationship, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print()
    print("===== LIVE RELATIONSHIP SUMMARY =====")
    mapping_ok = True
    for row in sorted(
        rows,
        key=lambda value: (
            str(value["subject"]["namespace"]),  # type: ignore[index]
            str(value["subject"]["workload_name"]),  # type: ignore[index]
        ),
    ):
        subject = row["subject"]
        persistence = row["persistence"]
        mapping = row["node_vm_mapping"]
        if not all(isinstance(value, dict) for value in (subject, persistence, mapping)):
            stop("relationship summary", "relationship projection is malformed")
        key = (
            subject["namespace"],
            subject["workload_kind"],
            subject["workload_name"],
        )
        actual = (persistence["storage_node"], mapping["vmid"])
        expected = EXPECTED_MAPPING[key]  # type: ignore[index]
        if actual != expected:
            mapping_ok = False
        print(
            f"{subject['namespace']}/{subject['workload_kind']}/{subject['workload_name']}"
            f" pvc={persistence['pvc_name']}"
            f" node={persistence['storage_node']}"
            f" vmid={mapping['vmid']}"
            f" discovery_match={actual == expected}"
        )
    print("discovery_mapping_match:", mapping_ok)

    print()
    print("===== ACCEPTED VM SOURCE HASHES =====")
    source_objects: dict[Path, dict[str, object]] = {}
    for path, expected_hash in EXPECTED_HASHES.items():
        if not path.exists():
            stop("accepted VM source", f"{path} NOT_FOUND")
        raw = path.read_bytes()
        actual_hash = hashlib.sha256(raw).hexdigest()
        match = actual_hash == expected_hash
        print(f"{path}: hash_match={match}")
        if not match:
            stop("accepted VM source hash", f"{path} SHA256 mismatch")
        source_objects[path] = json.loads(raw.decode("utf-8"))

    print()
    print("===== DERIVE ACCEPTED VM ASSURANCE v0.2 =====")
    vm_v02 = build_vm_last_successful_backup_integration(
        source_objects[VM_SOURCE],
        source_objects[TASK_SOURCE],
    )
    vm_schema = json.loads(
        (
            ROOT
            / "schemas"
            / "vm-last-successful-backup-integration.schema.json"
        ).read_text(encoding="utf-8")
    )
    jsonschema.Draft202012Validator(
        vm_schema,
        format_checker=jsonschema.FormatChecker(),
    ).validate(vm_v02)
    VM_V02_OUT.write_text(
        json.dumps(vm_v02, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("VM Backup Assurance v0.2 schema: PASS")
    print("VM assets:", vm_v02["summary"]["assets_total"])
    print(
        "VM LAST_SUCCESSFUL_BACKUP observed:",
        vm_v02["summary"]["last_successful_backup_observed"],
    )

    print()
    print("===== DERIVE POSTGRESQL INFRASTRUCTURE CONTEXT =====")
    derive = subprocess.run(
        [
            sys.executable,
            "-m",
            "infra_assurance.postgresql_infrastructure_recovery_context",
            "--relationship-evidence",
            str(RELATIONSHIP_OUT),
            "--vm-assurance",
            str(VM_V02_OUT),
            "--out",
            str(CONTEXT_OUT),
            "--summary-out",
            str(CONTEXT_MD),
        ],
        text=True,
        capture_output=True,
        env=os.environ.copy(),
    )
    if derive.returncode != 0:
        detail = (
            derive.stderr.strip().splitlines()[-1]
            if derive.stderr.strip()
            else f"rc={derive.returncode}"
        )
        stop("PostgreSQL context derivation", detail)

    context_artifact = json.loads(CONTEXT_OUT.read_text(encoding="utf-8"))
    context_schema = json.loads(
        (
            ROOT
            / "schemas"
            / "postgresql-infrastructure-recovery-context.schema.json"
        ).read_text(encoding="utf-8")
    )
    jsonschema.Draft202012Validator(
        context_schema,
        format_checker=jsonschema.FormatChecker(),
    ).validate(context_artifact)
    print("PostgreSQL context schema: PASS")

    print()
    print("===== DERIVED CONTEXT =====")
    print(
        "version:",
        context_artifact["postgresql_infrastructure_recovery_context_version"],
    )
    print("mutation_allowed:", context_artifact["mutation_allowed"])

    summary = context_artifact["summary"]
    summary_keys = (
        "instances_total",
        "infrastructure_recovery_observed",
        "infrastructure_recovery_unknown",
        "infrastructure_recovery_failed_to_observe",
        "underlying_vm_last_successful_backup_observed",
        "postgresql_protection_unknown",
        "postgresql_backup_mechanism_unknown",
        "postgresql_backup_execution_unknown",
        "postgresql_restore_verification_unknown",
        "postgresql_integrity_verification_unknown",
        "postgresql_rpo_unknown",
        "postgresql_rto_unknown",
        "unprotected_claims",
        "backup_stale_claims",
        "rpo_violation_claims",
    )
    for key in summary_keys:
        print(f"{key}: {summary[key]}")

    print()
    print("===== INSTANCE CONTEXT =====")
    timestamps_ok = True
    for instance in sorted(
        context_artifact["instances"],
        key=lambda value: (
            value["subject"]["namespace"],
            value["subject"]["workload_name"],
        ),
    ):
        subject = instance["subject"]
        persistence = instance["persistence"]
        recovery = instance["infrastructure_recovery"]
        pg = instance["postgresql_assurance"]
        vmid = recovery["vmid"]
        latest = recovery["underlying_vm_last_successful_backup_at"]
        expected_latest = EXPECTED_TIMESTAMPS.get(vmid)
        if latest != expected_latest:
            timestamps_ok = False
        print(
            f"{subject['namespace']}/{subject['workload_kind']}/{subject['workload_name']}"
            f" pvc={persistence['pvc_name']}"
            f" node={recovery['kubernetes_node']}"
            f" vmid={vmid}"
            f" infrastructure_recovery={recovery['relationship_status']}"
            f" vm_backup={recovery['underlying_vm_last_successful_backup_status']}"
            f" latest={latest or 'UNKNOWN'}"
            f" postgresql_protection={pg['protection_status']}"
        )
    print("accepted_vm_timestamps_match:", timestamps_ok)

    expected_summary = {
        "instances_total": 8,
        "infrastructure_recovery_observed": 8,
        "infrastructure_recovery_unknown": 0,
        "infrastructure_recovery_failed_to_observe": 0,
        "underlying_vm_last_successful_backup_observed": 8,
        "postgresql_protection_unknown": 8,
        "postgresql_backup_mechanism_unknown": 8,
        "postgresql_backup_execution_unknown": 8,
        "postgresql_restore_verification_unknown": 8,
        "postgresql_integrity_verification_unknown": 8,
        "postgresql_rpo_unknown": 8,
        "postgresql_rto_unknown": 8,
        "unprotected_claims": 0,
        "backup_stale_claims": 0,
        "rpo_violation_claims": 0,
    }
    summary_ok = all(
        summary.get(key) == expected
        for key, expected in expected_summary.items()
    )
    print("acceptance_counters_match:", summary_ok)

    print()
    print("===== TRUST BOUNDARY =====")
    print(
        "OBSERVED infrastructure recovery means the workload/PVC/storage-node/PVE-VM "
        "chain and strict VM last-successful-backup evidence were observed."
    )
    print(
        "It does NOT mean PostgreSQL-consistent backup, PostgreSQL restore verification, "
        "database integrity verification, retention, RPO, or RTO assurance."
    )
    print(
        "The VMID 108 timestamp is not classified as BACKUP_STALE or RPO_VIOLATION."
    )
    print(
        "No Kubernetes Secret values, Pod env values, PV backing paths, CSI handles, "
        "VM config, database rows, dump contents, or credentials were projected."
    )
    print("No infrastructure mutation was performed.")

    if not mapping_ok:
        stop(
            "live relationship acceptance",
            "mapping differs from accepted discovery; review live evidence",
            rc=3,
        )
    if not timestamps_ok:
        stop(
            "accepted VM timestamp verification",
            "derived timestamps differ from accepted source expectation",
            rc=3,
        )
    if not summary_ok:
        stop(
            "acceptance counters",
            "derived counters differ from expected bounded gate",
            rc=3,
        )

    print()
    print("===== GATE PASS =====")
    print(
        "PostgreSQL infrastructure recovery context v0.1 is ready for acceptance review."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
