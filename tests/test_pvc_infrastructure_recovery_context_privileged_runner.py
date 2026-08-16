from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/live_gates/run_m5_pvc_infrastructure_recovery_context.sh"


def test_privileged_runner_is_bounded_to_normalized_evidence_reads():
    text = RUNNER.read_text()

    assert 'KUBERNETES_SOURCE="/var/lib/infra-assurance/evidence/kubernetes.json"' in text
    assert 'TOPOLOGY_SOURCE="/var/lib/infra-assurance/evidence/topology.json"' in text
    assert 'sudo cat "$KUBERNETES_SOURCE"' in text
    assert 'sudo cat "$TOPOLOGY_SOURCE"' in text
    assert "privileged_evidence_read: BOUNDED_TO_NORMALIZED_ARTIFACTS" in text


def test_privileged_runner_does_not_run_gate_as_root_or_mutate_infrastructure():
    text = RUNNER.read_text().lower()

    assert 'sudo env' not in text
    assert 'sudo python' not in text
    assert 'sudo -u' not in text
    assert 'set -e' not in text
    assert 'set -euo' not in text

    for marker in (
        "chmod 777",
        "chown ",
        "systemctl start",
        "systemctl enable",
        "kubectl apply",
        "kubectl delete",
        "kubectl patch",
        "kubectl edit",
        "kubectl create",
        "pvesh set",
        "pvesh create",
        "pvesh delete",
    ):
        assert marker not in text

    assert 'chmod 600 "$kubernetes_copy" "$topology_copy"' in text
    assert "temporary evidence copies are removed" in text
