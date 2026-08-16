from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

from infra_assurance import __version__
from infra_assurance.backup_assurance_foundation import build_backup_assurance_foundation
from infra_assurance.pvc_infrastructure_recovery_context import (
    build_pvc_infrastructure_recovery_context,
)

ROOT = Path(__file__).resolve().parents[2]
DISCOVERY_PATH = ROOT / "scripts/discovery/m5_pvc_infrastructure_recovery_discovery.py"
KUBERNETES_EVIDENCE = Path("/var/lib/infra-assurance/evidence/kubernetes.json")
TOPOLOGY_EVIDENCE = Path("/var/lib/infra-assurance/evidence/topology.json")

FOUNDATION_OUT = Path("/tmp/pvc-backup-assurance-foundation.json")
RELATIONSHIP_OUT = Path("/tmp/pvc-infrastructure-relationship-evidence.json")
VM_ASSURANCE_OUT = Path("/tmp/vm-backup-assurance-v0.2.json")
CONTEXT_OUT = Path("/tmp/pvc-infrastructure-recovery-context.json")
CONTEXT_MD = Path("/tmp/pvc-infrastructure-recovery-context.md")

EXPECTED_VM_TIMESTAMPS = {
    106: "2026-08-14T16:39:53Z",
    107: "2026-08-14T17:39:32Z",
    108: "2026-04-15T12:36:38Z",
}

EXPECTED_SUMMARY = {
    "assets_total": 37,
    "direct_workload_reference_observed": 22,
    "direct_workload_reference_none_observed": 15,
    "infrastructure_recovery_observed": 37,
    "infrastructure_recovery_unknown": 0,
    "infrastructure_recovery_failed_to_observe": 0,
    "underlying_vm_last_successful_backup_observed": 37,
    "protection_unknown": 37,
    "backup_freshness_unknown": 37,
    "retention_effectiveness_unknown": 37,
    "failure_domain_unknown": 37,
    "integrity_verification_unknown": 37,
    "restore_verification_unknown": 37,
    "rpo_unknown": 37,
    "rto_unknown": 37,
    "unprotected_claims": 0,
    "backup_stale_claims": 0,
    "rpo_violation_claims": 0,
}


def stop(stage: str, detail: str, rc: int = 2) -> None:
    print()
    print("===== GATE REJECTED =====")
    print("stage:", stage)
    print("detail:", detail)
    print("No infrastructure mutation was performed by this gate.")
    raise SystemExit(rc)


def load_discovery_module():
    spec = importlib.util.spec_from_file_location("m5_pvc_discovery", DISCOVERY_PATH)
    if spec is None or spec.loader is None:
        stop("discovery module", "unable to load bounded discovery helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        stop(label, f"FAILED_TO_READ {type(exc).__name__}")
    if not isinstance(value, dict):
        stop(label, "expected JSON object")
    return value


def validate_schema(artifact: dict[str, Any], schema_path: Path, label: str) -> None:
    schema = load_json(schema_path, f"{label} schema")
    try:
        jsonschema.Draft202012Validator(
            schema,
            format_checker=jsonschema.FormatChecker(),
        ).validate(artifact)
    except jsonschema.ValidationError as exc:
        stop(label, f"schema validation failed: {exc.message}")


def canonical_pvc_key(subject: dict[str, Any]) -> tuple[str, str]:
    namespace = subject.get("namespace")
    name = subject.get("name")
    if not isinstance(namespace, str) or not namespace:
        stop("foundation subject", "PVC namespace missing")
    if not isinstance(name, str) or not name:
        stop("foundation subject", "PVC name missing")
    return namespace, name


def main() -> int:
    print("===== PVC INFRASTRUCTURE RECOVERY CONTEXT LIVE GATE =====")

    print()
    print("===== PACKAGE =====")
    print("package:", __version__)
    if __version__ != "0.27.0":
        stop("package", f"expected 0.27.0, got {__version__}")

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
        if tests.stderr:
            print(tests.stderr.rstrip())
        stop("repository tests", f"pytest rc={tests.returncode}")
    print("repository gate: PASS")

    discovery = load_discovery_module()

    print()
    print("===== FOUNDATION DERIVATION =====")
    snapshot = load_json(KUBERNETES_EVIDENCE, "Kubernetes evidence")
    topology = load_json(TOPOLOGY_EVIDENCE, "topology evidence")
    foundation = build_backup_assurance_foundation(
        snapshot,
        topology,
        now=datetime.now(timezone.utc),
    )
    validate_schema(
        foundation,
        ROOT / "schemas/backup-assurance-foundation.schema.json",
        "PVC foundation",
    )
    FOUNDATION_OUT.write_text(json.dumps(foundation, indent=2, sort_keys=True) + "\n")
    print("foundation schema: PASS")
    print("foundation_assets:", foundation["summary"]["assets_total"])
    if foundation["summary"]["assets_total"] != 37:
        stop(
            "foundation count",
            f"expected 37 PVC assets, got {foundation['summary']['assets_total']}",
            rc=3,
        )

    print()
    print("===== BOUNDED LIVE PVC RELATIONSHIP OBSERVATION =====")
    pvc_rows = discovery._pvc_rows()
    if pvc_rows is None:
        stop("live PVC observation", "FAILED_TO_OBSERVE")

    live_index = {(row["namespace"], row["name"]): row for row in pvc_rows}
    if len(live_index) != len(pvc_rows):
        stop("live PVC observation", "duplicate namespace/name identity")

    rs_parents = discovery._replicaset_parents()
    pod_refs = discovery._pod_pvc_references(rs_parents)

    relationship_assets: list[dict[str, Any]] = []
    storage_nodes: set[str] = set()

    for foundation_asset in foundation["assets"]:
        subject = deepcopy(foundation_asset["subject"])
        key = canonical_pvc_key(subject)
        row = live_index.get(key)

        if row is None:
            relationship_assets.append(
                {
                    "asset_id": foundation_asset["asset_id"],
                    "subject": subject,
                    "observation_status": "UNKNOWN",
                    "storage_relationship": {
                        "status": "UNKNOWN",
                        "pvc_phase": None,
                        "storage_class": None,
                        "pv_name": None,
                        "storage_node": None,
                    },
                    "workload_context": {
                        "status": "UNKNOWN",
                        "related_workloads": [],
                    },
                    "node_vm_mapping": {
                        "status": "UNKNOWN",
                        "kubernetes_node": None,
                        "pve_source_id": None,
                        "pve_node": None,
                        "vmid": None,
                    },
                    "evidence_ids": list(foundation_asset.get("evidence_ids", [])),
                }
            )
            continue

        storage_status, node = discovery._pv_storage_node(row["pv"])
        storage_observed = row["phase"] == "Bound" and storage_status == "OBSERVED"
        refs = pod_refs.get(key, [])

        if refs:
            workload_status = "DIRECT_CONTROLLER_REFERENCES_OBSERVED"
        else:
            workload_status = "NO_DIRECT_CONTROLLER_REFERENCE_OBSERVED"

        if storage_observed and node:
            storage_nodes.add(node)

        relationship_assets.append(
            {
                "asset_id": foundation_asset["asset_id"],
                "subject": subject,
                "observation_status": (
                    "FAILED_TO_OBSERVE"
                    if storage_status == "FAILED_TO_OBSERVE"
                    else "OBSERVED"
                ),
                "storage_relationship": {
                    "status": (
                        "OBSERVED"
                        if storage_observed
                        else (
                            "FAILED_TO_OBSERVE"
                            if storage_status == "FAILED_TO_OBSERVE"
                            else "UNKNOWN"
                        )
                    ),
                    "pvc_phase": row["phase"],
                    "storage_class": row["storage_class"],
                    "pv_name": row["pv"],
                    "storage_node": node,
                },
                "workload_context": {
                    "status": workload_status,
                    "related_workloads": refs,
                },
                "node_vm_mapping": {
                    "status": "UNKNOWN",
                    "kubernetes_node": node,
                    "pve_source_id": None,
                    "pve_node": None,
                    "vmid": None,
                },
                "evidence_ids": list(foundation_asset.get("evidence_ids", [])),
            }
        )

    if set(live_index) != {canonical_pvc_key(asset["subject"]) for asset in foundation["assets"]}:
        stop(
            "foundation/live identity comparison",
            "live PVC identity set differs from accepted foundation identity set",
            rc=3,
        )

    print("live_pvc_assets:", len(live_index))
    print("storage_nodes_to_map:", len(storage_nodes))

    print()
    print("===== BOUNDED PVE NODE MAPPING =====")
    try:
        getter, trust = discovery.build_getter_from_env(
            discovery.ENV_FILE,
            allow_discovery_credential=True,
            allow_insecure_tls_discovery=True,
        )
        status, data, error = getter(
            "/api2/json/cluster/resources",
            {"type": "vm"},
        )
    except Exception as exc:
        stop("PVE node mapping", f"FAILED_TO_OBSERVE {type(exc).__name__}")

    print("operation: GET /cluster/resources?type=vm")
    print("http_status:", status if status is not None else "NONE")
    print("runtime_credential_approved:", trust["runtime_credential_approved"])
    if status != 200 or not isinstance(data, list):
        stop("PVE node mapping", f"FAILED_TO_OBSERVE {error or 'UNKNOWN'}")

    mapping_by_node: dict[str, dict[str, Any]] = {}
    for node in sorted(storage_nodes):
        matches = [
            item
            for item in data
            if isinstance(item, dict) and item.get("name") == node
        ]
        if len(matches) != 1:
            mapping_by_node[node] = {"status": "UNKNOWN"}
            continue
        item = matches[0]
        vmid = item.get("vmid")
        if isinstance(vmid, bool) or not isinstance(vmid, int) or vmid < 1:
            mapping_by_node[node] = {"status": "UNKNOWN"}
            continue
        mapping_by_node[node] = {
            "status": "OBSERVED",
            "kubernetes_node": node,
            "pve_source_id": "pve-bm2",
            "pve_node": item.get("node") or "UNKNOWN",
            "vmid": vmid,
        }

    for item in relationship_assets:
        storage = item["storage_relationship"]
        node = storage.get("storage_node")
        if storage.get("status") != "OBSERVED" or not isinstance(node, str):
            continue
        mapping = mapping_by_node.get(node, {"status": "UNKNOWN"})
        if mapping.get("status") == "OBSERVED":
            item["node_vm_mapping"] = deepcopy(mapping)

    relationship_status = (
        "COMPLETE"
        if all(
            item["observation_status"] == "OBSERVED"
            and item["storage_relationship"]["status"] == "OBSERVED"
            and item["node_vm_mapping"]["status"] == "OBSERVED"
            for item in relationship_assets
        )
        else "PARTIAL"
    )

    relationship = {
        "pvc_infrastructure_relationship_evidence_version": "0.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mutation_allowed": False,
        "cluster_id": foundation["cluster_id"],
        "source": {
            "type": "BOUNDED_KUBERNETES_PVE_RELATIONSHIP_OBSERVATION",
            "source_id": "m5-pvc-live-gate",
            "status": relationship_status,
        },
        "assets": relationship_assets,
    }
    RELATIONSHIP_OUT.write_text(
        json.dumps(relationship, indent=2, sort_keys=True) + "\n"
    )

    print("relationship_source_status:", relationship_status)

    print()
    print("===== ACCEPTED VM SOURCE VERIFICATION =====")
    vm_assurance = discovery._accepted_vm_assurance()
    if not isinstance(vm_assurance, dict):
        stop("accepted VM assurance", "unable to derive accepted v0.2 artifact")
    validate_schema(
        vm_assurance,
        ROOT / "schemas/vm-last-successful-backup-integration.schema.json",
        "VM Backup Assurance v0.2",
    )
    VM_ASSURANCE_OUT.write_text(
        json.dumps(vm_assurance, indent=2, sort_keys=True) + "\n"
    )
    print("VM Backup Assurance v0.2 schema: PASS")

    print()
    print("===== DERIVED PVC CONTEXT =====")
    context = build_pvc_infrastructure_recovery_context(
        foundation,
        relationship,
        vm_assurance,
    )
    validate_schema(
        context,
        ROOT / "schemas/pvc-infrastructure-recovery-context.schema.json",
        "PVC infrastructure recovery context",
    )
    CONTEXT_OUT.write_text(json.dumps(context, indent=2, sort_keys=True) + "\n")

    from infra_assurance.pvc_infrastructure_recovery_context import (
        render_pvc_infrastructure_recovery_markdown,
    )

    CONTEXT_MD.write_text(
        render_pvc_infrastructure_recovery_markdown(context), encoding="utf-8"
    )
    print("schema: PASS")

    summary = context["summary"]
    for key in EXPECTED_SUMMARY:
        print(f"{key}: {summary[key]}")

    print()
    print("===== VM TIMESTAMP CHECK =====")
    timestamps_ok = True
    for asset in context["assets"]:
        recovery = asset["infrastructure_recovery"]
        vmid = recovery.get("vmid")
        latest = recovery.get("underlying_vm_last_successful_backup_at")
        if isinstance(vmid, int) and vmid in EXPECTED_VM_TIMESTAMPS:
            if latest != EXPECTED_VM_TIMESTAMPS[vmid]:
                timestamps_ok = False
    print("accepted_vm_timestamps_match:", timestamps_ok)

    summary_ok = all(summary.get(key) == value for key, value in EXPECTED_SUMMARY.items())
    print("acceptance_counters_match:", summary_ok)

    print()
    print("===== TRUST BOUNDARY =====")
    print(
        "OBSERVED PVC infrastructure recovery means PVC -> explicit storage node -> "
        "PVE VMID -> accepted strict VM last-successful-backup evidence only."
    )
    print(
        "It does not establish application-consistent or database-consistent backup, "
        "retention, restore verification, integrity, failure-domain independence, RPO, or RTO."
    )
    print(
        "No direct controller reference observed is bounded context only and is not an "
        "orphan or UNPROTECTED classification."
    )
    print(
        "No Kubernetes Secret values, env values, commands/args, PV backing paths, CSI "
        "handles, raw PVE VM config, application/database data, or backup contents were projected."
    )
    print("No infrastructure mutation was performed.")

    if relationship_status != "COMPLETE":
        stop(
            "relationship source",
            "live relationship source is not COMPLETE",
            rc=3,
        )
    if not timestamps_ok:
        stop(
            "accepted VM timestamp verification",
            "derived VM timestamps differ from accepted source expectation",
            rc=3,
        )
    if not summary_ok:
        stop(
            "acceptance counters",
            "derived counters differ from accepted bounded discovery",
            rc=3,
        )

    print()
    print("===== GATE PASS =====")
    print("PVC infrastructure recovery context v0.1 is ready for acceptance review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
