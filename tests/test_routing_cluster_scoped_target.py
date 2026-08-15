from __future__ import annotations

import subprocess
from datetime import datetime, timezone

from infra_assurance.routing_ownership import build_routing_ownership


def test_cluster_scoped_non_pod_target_does_not_inherit_service_namespace():
    endpoint_output = (
        "monitoring\tkubelet-a\tkubelet\t"
        "v1|Node||k3s-worker-01|true||;\n"
    )

    def runner(command, **kwargs):
        assert command[command.index("get") + 1] == "endpointslices.discovery.k8s.io"
        return subprocess.CompletedProcess(command, 0, endpoint_output, "")

    snapshot = {
        "cluster_id": "k3s-main",
        "evidence": [
            {
                "evidence_id": "service-collection",
                "observation_status": "COMPLETE",
                "subject": {"kind": "ServiceCollection", "namespace": None, "name": "*"},
            },
            {
                "evidence_id": "service-kubelet",
                "observation_status": "COMPLETE",
                "subject": {"kind": "Service", "namespace": "monitoring", "name": "kubelet"},
            },
            *[
                {
                    "evidence_id": f"{kind.lower()}-collection",
                    "observation_status": "COMPLETE",
                    "subject": {"kind": f"{kind}Collection", "namespace": None, "name": "*"},
                }
                for kind in ("Deployment", "StatefulSet", "DaemonSet")
            ],
        ],
    }

    result = build_routing_ownership(
        snapshot,
        runner=runner,
        now=datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc),
    )

    path = result["service_routes"][0]["paths"][0]
    assert path["resolution"] == "NON_POD_TARGET"
    assert path["target"] == {
        "api_group": "",
        "kind": "Node",
        "namespace": None,
        "name": "k3s-worker-01",
    }
