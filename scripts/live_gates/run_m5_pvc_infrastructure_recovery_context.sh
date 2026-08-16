#!/usr/bin/env bash

# Manual wrapper for the PVC infrastructure recovery context live gate.
# Do not enable shell strict mode here: this is intended for an interactive SSH session.

if [ "${EUID:-$(id -u)}" -eq 0 ]; then
  echo "Do not run this wrapper as root."
  echo "Run it as the normal operator user; it will request sudo only for two bounded evidence reads."
  exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
KUBERNETES_SOURCE="/var/lib/infra-assurance/evidence/kubernetes.json"
TOPOLOGY_SOURCE="/var/lib/infra-assurance/evidence/topology.json"
TMP_DIR="$(mktemp -d /tmp/iia-pvc-gate.XXXXXX)"
KUBERNETES_COPY="$TMP_DIR/kubernetes.json"
TOPOLOGY_COPY="$TMP_DIR/topology.json"

cleanup() {
  rm -f "$KUBERNETES_COPY" "$TOPOLOGY_COPY" 2>/dev/null
  rmdir "$TMP_DIR" 2>/dev/null
}
trap cleanup EXIT

echo "===== BOUNDED PRIVILEGED EVIDENCE READ ====="
echo "Only normalized Kubernetes evidence and topology artifacts will be read with sudo."
echo "The live gate itself will continue as the current non-root user."
echo

sudo cat "$KUBERNETES_SOURCE" > "$KUBERNETES_COPY"
KUBE_RC=$?
if [ "$KUBE_RC" -ne 0 ]; then
  echo "Kubernetes evidence privileged read failed rc=$KUBE_RC"
  echo "No infrastructure mutation was performed."
  exit 2
fi

sudo cat "$TOPOLOGY_SOURCE" > "$TOPOLOGY_COPY"
TOPO_RC=$?
if [ "$TOPO_RC" -ne 0 ]; then
  echo "Topology evidence privileged read failed rc=$TOPO_RC"
  echo "No infrastructure mutation was performed."
  exit 2
fi

chmod 600 "$KUBERNETES_COPY" "$TOPOLOGY_COPY"

cd "$ROOT" || exit 2

PYTHONPATH="$ROOT/src" python3 - "$ROOT" "$KUBERNETES_COPY" "$TOPOLOGY_COPY" <<'PY'
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

root = Path(sys.argv[1])
kubernetes_copy = Path(sys.argv[2])
topology_copy = Path(sys.argv[3])
gate_path = root / "scripts/live_gates/m5_pvc_infrastructure_recovery_context.py"

spec = importlib.util.spec_from_file_location("m5_pvc_live_gate", gate_path)
if spec is None or spec.loader is None:
    print("Unable to load PVC live gate.")
    raise SystemExit(2)

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.KUBERNETES_EVIDENCE = kubernetes_copy
module.TOPOLOGY_EVIDENCE = topology_copy

print("privileged_evidence_read: BOUNDED_TO_NORMALIZED_ARTIFACTS")
print("gate_effective_user: CURRENT_NON_ROOT_SHELL_USER")
print()
raise SystemExit(module.main())
PY
GATE_RC=$?

echo
echo "===== PRIVILEGE BOUNDARY ====="
echo "sudo was used only to read the two normalized evidence artifacts."
echo "No permission, ownership, service, Kubernetes, PVE, application, or database state was changed."
echo "Temporary evidence copies are removed on wrapper exit."
echo "gate_rc=$GATE_RC"

exit "$GATE_RC"
