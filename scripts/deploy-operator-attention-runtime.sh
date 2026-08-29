#!/usr/bin/env bash
set -euo pipefail
umask 022

if [[ ${EUID} -ne 0 ]]; then
  echo "Run with sudo: sudo $0 --apply" >&2
  exit 1
fi

if [[ "${1:-}" != "--apply" ]]; then
  cat <<'EOF'
This deployment helper performs only these bounded mutations:
- installs src/infra_assurance/operator_attention.py into /opt/infra-assurance/src/infra_assurance/operator_attention.py
- installs systemd/infra-assurance-kubernetes.service into /etc/systemd/system/infra-assurance-kubernetes.service
- runs systemctl daemon-reload
- starts the existing infra-assurance-kubernetes.service once
- verifies operator-attention.json and operator-attention.md were produced

It does not run bootstrap-observer.sh, change Kubernetes RBAC, change kubeconfig, change Git source configuration, add a new service/timer, or broaden filesystem permissions.

Re-run with --apply only after explicit authorization.
EOF
  exit 2
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODULE_SOURCE="${REPO_ROOT}/src/infra_assurance/operator_attention.py"
UNIT_SOURCE="${REPO_ROOT}/systemd/infra-assurance-kubernetes.service"
MODULE_TARGET="/opt/infra-assurance/src/infra_assurance/operator_attention.py"
UNIT_TARGET="/etc/systemd/system/infra-assurance-kubernetes.service"
SERVICE="infra-assurance-kubernetes.service"
JSON_OUT="/var/lib/infra-assurance/evidence/operator-attention.json"
MARKDOWN_OUT="/var/lib/infra-assurance/evidence/operator-attention.md"

[[ -f "${MODULE_SOURCE}" ]] || { echo "Missing source module: ${MODULE_SOURCE}" >&2; exit 1; }
[[ -f "${UNIT_SOURCE}" ]] || { echo "Missing systemd unit: ${UNIT_SOURCE}" >&2; exit 1; }
[[ -d /opt/infra-assurance/src/infra_assurance ]] || { echo "Installed runtime package path is missing." >&2; exit 1; }
id infra-assurance >/dev/null 2>&1 || { echo "infra-assurance service identity is missing." >&2; exit 1; }

install -o root -g root -m 0644 "${MODULE_SOURCE}" "${MODULE_TARGET}"
install -o root -g root -m 0644 "${UNIT_SOURCE}" "${UNIT_TARGET}"

/usr/bin/python3 -m py_compile "${MODULE_TARGET}"
systemctl daemon-reload
systemctl start "${SERVICE}"

result="$(systemctl show "${SERVICE}" -p Result --value)"
if [[ "${result}" != "success" ]]; then
  echo "${SERVICE} result is ${result:-unknown}." >&2
  exit 1
fi

[[ -s "${JSON_OUT}" ]] || { echo "Missing generated artifact: ${JSON_OUT}" >&2; exit 1; }
[[ -s "${MARKDOWN_OUT}" ]] || { echo "Missing generated artifact: ${MARKDOWN_OUT}" >&2; exit 1; }

owner_json="$(stat -c '%U:%G' "${JSON_OUT}")"
owner_md="$(stat -c '%U:%G' "${MARKDOWN_OUT}")"
if [[ "${owner_json}" != "infra-assurance:infra-assurance" || "${owner_md}" != "infra-assurance:infra-assurance" ]]; then
  echo "Generated artifact ownership is unexpected: json=${owner_json} markdown=${owner_md}" >&2
  exit 1
fi

printf 'deployment_status=COMPLETE\n'
printf 'service_result=%s\n' "${result}"
printf 'operator_attention_json=OBSERVED\n'
printf 'operator_attention_markdown=OBSERVED\n'
printf 'runtime_identity=infra-assurance\n'
