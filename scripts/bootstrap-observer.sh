#!/usr/bin/env bash
set -euo pipefail
umask 077

if [[ ${EUID} -ne 0 ]]; then
  echo "Run with sudo: sudo $0" >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ADMIN_KUBECONFIG="${ADMIN_KUBECONFIG:-/home/ben/.kube/config}"
CLUSTER_ID="${CLUSTER_ID:-k3s-main}"
INSTALL_ROOT="/opt/infra-assurance"
CONFIG_DIR="/etc/infra-assurance"
STATE_DIR="/var/lib/infra-assurance"
SERVICE_USER="infra-assurance"
OBSERVER_KUBECONFIG="${CONFIG_DIR}/kubeconfig"

command -v kubectl >/dev/null
command -v python3 >/dev/null

if ! id "${SERVICE_USER}" >/dev/null 2>&1; then
  useradd --system --home-dir "${STATE_DIR}" --create-home --shell /usr/sbin/nologin "${SERVICE_USER}"
fi
install -d -o root -g "${SERVICE_USER}" -m 0750 "${CONFIG_DIR}"
install -d -o "${SERVICE_USER}" -g "${SERVICE_USER}" -m 0750 "${STATE_DIR}/evidence"
install -d -o root -g root -m 0755 "${INSTALL_ROOT}"

KUBECONFIG="${ADMIN_KUBECONFIG}" kubectl apply -f "${REPO_ROOT}/deploy/kubernetes/observer-rbac.yaml" >/dev/null

for _ in $(seq 1 30); do
  TOKEN_B64="$(KUBECONFIG="${ADMIN_KUBECONFIG}" kubectl -n infra-assurance-system get secret infra-assurance-observer-token -o jsonpath='{.data.token}' 2>/dev/null || true)"
  CA_DATA="$(KUBECONFIG="${ADMIN_KUBECONFIG}" kubectl -n infra-assurance-system get secret infra-assurance-observer-token -o jsonpath='{.data.ca\.crt}' 2>/dev/null || true)"
  [[ -n "${TOKEN_B64}" && -n "${CA_DATA}" ]] && break
  sleep 1
done
[[ -n "${TOKEN_B64:-}" && -n "${CA_DATA:-}" ]] || { echo "Observer credential was not populated" >&2; exit 1; }
TOKEN="$(printf '%s' "${TOKEN_B64}" | base64 -d)"
API_SERVER="$(KUBECONFIG="${ADMIN_KUBECONFIG}" kubectl config view --raw --minify -o jsonpath='{.clusters[0].cluster.server}')"

cat > "${OBSERVER_KUBECONFIG}" <<EOF
apiVersion: v1
kind: Config
clusters:
- name: target
  cluster:
    server: ${API_SERVER}
    certificate-authority-data: ${CA_DATA}
users:
- name: observer
  user:
    token: ${TOKEN}
contexts:
- name: infra-assurance
  context:
    cluster: target
    user: observer
current-context: infra-assurance
EOF
chown root:"${SERVICE_USER}" "${OBSERVER_KUBECONFIG}"
chmod 0640 "${OBSERVER_KUBECONFIG}"
unset TOKEN TOKEN_B64 CA_DATA

rm -rf "${INSTALL_ROOT}/src"
cp -a "${REPO_ROOT}/src" "${INSTALL_ROOT}/src"
chown -R root:root "${INSTALL_ROOT}/src"

cat > "${CONFIG_DIR}/collector.env" <<EOF
IIA_CLUSTER_ID=${CLUSTER_ID}
KUBECONFIG=${OBSERVER_KUBECONFIG}
EOF
chown root:"${SERVICE_USER}" "${CONFIG_DIR}/collector.env"
chmod 0640 "${CONFIG_DIR}/collector.env"

install -m 0644 "${REPO_ROOT}/systemd/infra-assurance-kubernetes.service" /etc/systemd/system/infra-assurance-kubernetes.service
install -m 0644 "${REPO_ROOT}/systemd/infra-assurance-kubernetes.timer" /etc/systemd/system/infra-assurance-kubernetes.timer
systemctl daemon-reload
systemctl enable --now infra-assurance-kubernetes.timer >/dev/null
systemctl start infra-assurance-kubernetes.service

assert_can_i() {
  local expected="$1"
  shift
  local actual
  actual="$(KUBECONFIG="${OBSERVER_KUBECONFIG}" kubectl auth can-i "$@" 2>/dev/null || true)"
  if [[ "${actual}" != "${expected}" ]]; then
    echo "RBAC verification failed: expected '${expected}' for: kubectl auth can-i $*; got '${actual}'" >&2
    exit 1
  fi
}

assert_can_i yes list nodes
assert_can_i yes list deployments.apps --all-namespaces
assert_can_i no list secrets --all-namespaces
assert_can_i no create deployments.apps -n default

echo "Observer installed."
echo "Evidence: ${STATE_DIR}/evidence/kubernetes.json"
echo "Context:  ${STATE_DIR}/evidence/context.json"
systemctl --no-pager --full status infra-assurance-kubernetes.service || true
