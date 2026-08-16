from __future__ import annotations

import hashlib
import json
import subprocess
from collections import defaultdict
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

ACCEPTED_FOUNDATION_PVC_COUNT = 37


def _run(args: list[str]) -> tuple[int, str]:
    result = subprocess.run(args, text=True, capture_output=True)
    return result.returncode, result.stdout


def _required(args: list[str], label: str) -> str | None:
    rc, stdout = _run(args)
    if rc != 0:
        print(f"{label}: FAILED_TO_OBSERVE rc={rc}")
        return None
    return stdout


def _parse_owners(raw: str) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for item in raw.split(","):
        item = item.strip()
        if not item or "=" not in item:
            continue
        kind, name = item.split("=", 1)
        if kind and name:
            result.append((kind, name))
    return result


def _replicaset_parents() -> dict[tuple[str, str], tuple[str, str]]:
    output = _required(
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
    if output is None:
        return {}

    parents: dict[tuple[str, str], tuple[str, str]] = {}
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        owners = _parse_owners(parts[2])
        if owners:
            parents[(parts[0], parts[1])] = owners[0]
    return parents


def _pod_pvc_references(
    rs_parents: dict[tuple[str, str], tuple[str, str]],
) -> dict[tuple[str, str], list[str]]:
    output = _required(
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
            "{end}{\"\\t\"}"
            "{range .spec.volumes[*]}"
            "{.persistentVolumeClaim.claimName}{\",\"}"
            "{end}{\"\\n\"}"
            "{end}",
        ],
        "Pod/PVC safe projection",
    )
    if output is None:
        return {}

    references: dict[tuple[str, str], list[str]] = defaultdict(list)

    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 6:
            continue

        namespace, pod, phase, _node, raw_owners, raw_claims = parts[:6]
        if phase not in {"Running", "Pending"}:
            continue

        owner_kind = "Pod"
        owner_name = pod
        owners = _parse_owners(raw_owners)
        if owners:
            owner_kind, owner_name = owners[0]
            if owner_kind == "ReplicaSet":
                parent = rs_parents.get((namespace, owner_name))
                if parent:
                    owner_kind, owner_name = parent

        label = f"{owner_kind}/{owner_name}"
        claims = sorted({value for value in raw_claims.split(",") if value})
        for claim in claims:
            key = (namespace, claim)
            if label not in references[key]:
                references[key].append(label)

    for values in references.values():
        values.sort()
    return dict(references)


def _pvc_rows() -> list[dict[str, str]] | None:
    output = _required(
        [
            "kubectl",
            "get",
            "pvc",
            "-A",
            "-o",
            "jsonpath="
            "{range .items[*]}"
            "{.metadata.namespace}{\"\\t\"}"
            "{.metadata.name}{\"\\t\"}"
            "{.status.phase}{\"\\t\"}"
            "{.spec.storageClassName}{\"\\t\"}"
            "{.spec.volumeName}{\"\\n\"}"
            "{end}",
        ],
        "PVC safe projection",
    )
    if output is None:
        return None

    rows: list[dict[str, str]] = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        rows.append(
            {
                "namespace": parts[0],
                "name": parts[1],
                "phase": parts[2] or "UNKNOWN",
                "storage_class": parts[3] or "UNKNOWN",
                "pv": parts[4] or "UNKNOWN",
            }
        )
    return sorted(rows, key=lambda row: (row["namespace"], row["name"]))


def _pv_storage_node(pv: str) -> tuple[str, str | None]:
    if not pv or pv == "UNKNOWN":
        return "UNKNOWN", None

    output = _required(
        [
            "kubectl",
            "get",
            "pv",
            pv,
            "-o",
            "go-template="
            "{{range .spec.nodeAffinity.required.nodeSelectorTerms}}"
            "{{range .matchExpressions}}"
            "{{if and (eq .key \"kubernetes.io/hostname\") (eq .operator \"In\")}}"
            "{{range .values}}{{.}}{{\"\\n\"}}{{end}}"
            "{{end}}"
            "{{end}}"
            "{{end}}",
        ],
        "PV node-affinity projection",
    )
    if output is None:
        return "FAILED_TO_OBSERVE", None

    nodes = sorted({line.strip() for line in output.splitlines() if line.strip()})
    if len(nodes) == 1:
        return "OBSERVED", nodes[0]
    return "UNKNOWN", None


def _accepted_vm_assurance() -> dict[str, Any] | None:
    payloads: dict[Path, dict[str, Any]] = {}

    print()
    print("===== ACCEPTED VM SOURCE VERIFICATION =====")

    for path, expected in EXPECTED_HASHES.items():
        if not path.exists():
            print(f"{path}: NOT_FOUND")
            return None
        try:
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            payload = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            print(f"{path}: FAILED_TO_READ")
            return None

        matched = digest == expected
        print(f"{path}: hash_match={matched}")
        if not matched:
            return None
        payloads[path] = payload

    try:
        return build_vm_last_successful_backup_integration(
            payloads[VM_SOURCE],
            payloads[TASK_SOURCE],
        )
    except Exception as exc:
        print("vm_assurance_derivation: FAILED")
        print("error_class:", type(exc).__name__)
        return None


def _strict_vm_index(vm_assurance: dict[str, Any] | None) -> dict[int, dict[str, Any]]:
    index: dict[int, dict[str, Any]] = {}
    if not isinstance(vm_assurance, dict):
        return index

    for asset in vm_assurance.get("assets", []):
        if not isinstance(asset, dict):
            continue
        vmid = asset.get("subject", {}).get("vmid")
        if isinstance(vmid, bool) or not isinstance(vmid, int):
            continue
        assurance = asset.get("assurance", {})
        evidence = assurance.get("last_successful_backup_evidence")
        strict = (
            assurance.get("last_successful_backup_status") == "OBSERVED"
            and isinstance(evidence, dict)
            and evidence.get("basis") == ["STRICT_SUCCESS_TASK_MATCH"]
        )
        index[vmid] = {
            "status": (
                "OBSERVED"
                if strict
                else assurance.get("last_successful_backup_status", "UNKNOWN")
            ),
            "latest": assurance.get("last_successful_backup_at") if strict else None,
            "strict": strict,
        }
    return index


def main() -> int:
    print("===== PVC INFRASTRUCTURE RECOVERY COVERAGE DISCOVERY =====")

    rc, context = _run(["kubectl", "config", "current-context"])
    print()
    print("===== KUBERNETES CONTEXT =====")
    print("context:", context.strip() if rc == 0 else "FAILED_TO_OBSERVE")

    pvc_rows = _pvc_rows()
    if pvc_rows is None:
        print("discovery_status: FAILED_TO_OBSERVE")
        print("No mutation was performed.")
        return 0

    rs_parents = _replicaset_parents()
    pod_refs = _pod_pvc_references(rs_parents)

    print()
    print("===== PVC FOUNDATION COMPARISON =====")
    print("accepted_foundation_pvc_assets:", ACCEPTED_FOUNDATION_PVC_COUNT)
    print("live_pvc_assets:", len(pvc_rows))
    print(
        "foundation_count_match:",
        len(pvc_rows) == ACCEPTED_FOUNDATION_PVC_COUNT,
    )

    for row in pvc_rows:
        status, node = _pv_storage_node(row["pv"])
        row["storage_node_status"] = status
        row["storage_node"] = node or "UNKNOWN"
        refs = pod_refs.get((row["namespace"], row["name"]), [])
        row["workload_refs"] = refs

    storage_nodes = sorted(
        {
            row["storage_node"]
            for row in pvc_rows
            if row["storage_node_status"] == "OBSERVED"
            and row["storage_node"] != "UNKNOWN"
        }
    )

    print()
    print("===== BOUNDED PVE NODE MAPPING =====")
    print("storage_nodes_to_map:", len(storage_nodes))

    pve_mapping: dict[str, dict[str, Any]] = {}
    try:
        getter, trust = build_getter_from_env(
            ENV_FILE,
            allow_discovery_credential=True,
            allow_insecure_tls_discovery=True,
        )
        status, data, error = getter(
            "/api2/json/cluster/resources",
            {"type": "vm"},
        )
        print("operation: GET /cluster/resources?type=vm")
        print("http_status:", status if status is not None else "NONE")
        print("runtime_credential_approved:", trust["runtime_credential_approved"])

        if status == 200 and isinstance(data, list):
            for node in storage_nodes:
                matches = [
                    item
                    for item in data
                    if isinstance(item, dict) and item.get("name") == node
                ]
                if len(matches) != 1:
                    pve_mapping[node] = {"status": "UNKNOWN"}
                    continue
                item = matches[0]
                vmid = item.get("vmid")
                if isinstance(vmid, bool) or not isinstance(vmid, int):
                    pve_mapping[node] = {"status": "UNKNOWN"}
                    continue
                pve_mapping[node] = {
                    "status": "OBSERVED",
                    "vmid": vmid,
                    "pve_node": item.get("node") or "UNKNOWN",
                }
        else:
            print("pve_mapping_status: FAILED_TO_OBSERVE")
            print("error_class:", error or "UNKNOWN")
    except Exception as exc:
        print("pve_mapping_status: FAILED_TO_OBSERVE")
        print("error_class:", type(exc).__name__)

    vm_index = _strict_vm_index(_accepted_vm_assurance())

    counts = defaultdict(int)

    print()
    print("===== PVC RECOVERY COVERAGE =====")

    for row in pvc_rows:
        refs: list[str] = row["workload_refs"]  # type: ignore[assignment]
        workload_status = "OBSERVED" if refs else "NONE_OBSERVED"

        mapping = pve_mapping.get(row["storage_node"], {"status": "UNKNOWN"})
        vmid = mapping.get("vmid") if mapping.get("status") == "OBSERVED" else None
        vm = vm_index.get(vmid, {}) if isinstance(vmid, int) else {}
        vm_backup = vm.get("status", "UNKNOWN")
        latest = vm.get("latest") or "UNKNOWN"

        if row["storage_node_status"] == "FAILED_TO_OBSERVE":
            recovery = "FAILED_TO_OBSERVE"
        elif (
            row["phase"] == "Bound"
            and row["storage_node_status"] == "OBSERVED"
            and mapping.get("status") == "OBSERVED"
            and vm.get("strict") is True
        ):
            recovery = "OBSERVED"
        else:
            recovery = "UNKNOWN"

        counts["total"] += 1
        counts[f"phase_{row['phase']}"] += 1
        counts[f"workload_{workload_status}"] += 1
        counts[f"storage_node_{row['storage_node_status']}"] += 1
        counts[f"vm_mapping_{mapping.get('status', 'UNKNOWN')}"] += 1
        counts[f"vm_backup_{vm_backup}"] += 1
        counts[f"recovery_{recovery}"] += 1

        refs_text = ",".join(refs[:3]) if refs else "NONE_OBSERVED"
        if len(refs) > 3:
            refs_text += f",+{len(refs) - 3}_more"

        print(
            f"{row['namespace']}/{row['name']}"
            f" phase={row['phase']}"
            f" storage_class={row['storage_class']}"
            f" workload_refs={refs_text}"
            f" storage_node={row['storage_node']}"
            f" vmid={vmid if vmid is not None else 'UNKNOWN'}"
            f" vm_backup={vm_backup}"
            f" latest={latest}"
            f" infrastructure_recovery={recovery}"
        )

    print()
    print("===== SUMMARY =====")
    print("pvc_assets_total:", counts["total"])
    print("pvc_bound:", counts["phase_Bound"])
    print("current_workload_reference_observed:", counts["workload_OBSERVED"])
    print("current_workload_reference_none_observed:", counts["workload_NONE_OBSERVED"])
    print("explicit_storage_node_observed:", counts["storage_node_OBSERVED"])
    print("explicit_storage_node_unknown:", counts["storage_node_UNKNOWN"])
    print("storage_node_failed_to_observe:", counts["storage_node_FAILED_TO_OBSERVE"])
    print("pve_vm_mapping_observed:", counts["vm_mapping_OBSERVED"])
    print("pve_vm_mapping_unknown:", counts["vm_mapping_UNKNOWN"])
    print("underlying_vm_last_successful_backup_observed:", counts["vm_backup_OBSERVED"])
    print("underlying_vm_last_successful_backup_unknown:", counts["vm_backup_UNKNOWN"])
    print("infrastructure_recovery_observed:", counts["recovery_OBSERVED"])
    print("infrastructure_recovery_unknown:", counts["recovery_UNKNOWN"])
    print("infrastructure_recovery_failed_to_observe:", counts["recovery_FAILED_TO_OBSERVE"])
    print("protection_promotions: 0")
    print("unprotected_claims: 0")
    print("backup_stale_claims: 0")
    print("rpo_violation_claims: 0")

    print()
    print("===== INTERPRETATION BOUNDARY =====")
    print(
        "OBSERVED infrastructure recovery means only PVC -> explicit storage node -> "
        "PVE VMID -> accepted strict VM last-successful-backup evidence."
    )
    print(
        "It does not establish application-consistent or database-consistent backup, "
        "retention, restore verification, integrity, RPO, or RTO."
    )
    print(
        "No current Pod reference is bounded negative evidence only and is not an orphan "
        "or UNPROTECTED classification."
    )
    print(
        "Timestamp age is not classified as BACKUP_STALE or RPO_VIOLATION without an "
        "accepted target."
    )

    print()
    print("===== TRUST BOUNDARY =====")
    print("No Kubernetes Secret values, env values, commands, or args were read.")
    print("No PV backing paths or CSI handles were read.")
    print("No raw PVE VM config, disk, network, or credential values were read or printed.")
    print("No application/database data or backup contents were read.")
    print("Only GET/read-only observations were used; no infrastructure mutation occurred.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
