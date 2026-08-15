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
HISTORY_RETENTION="${HISTORY_RETENTION:-288}"
PROMETHEUS_NAMESPACE="${PROMETHEUS_NAMESPACE:-monitoring}"
PROMETHEUS_SERVICE="${PROMETHEUS_SERVICE:-kube-prom-stack-prometheus}"
PROMETHEUS_PORT="${PROMETHEUS_PORT:-9090}"
ALERTMANAGER_NAMESPACE="${ALERTMANAGER_NAMESPACE:-monitoring}"
ALERTMANAGER_SERVICE="${ALERTMANAGER_SERVICE:-kube-prom-stack-alertmanager}"
ALERTMANAGER_PORT="${ALERTMANAGER_PORT:-9093}"
EVENT_WINDOW_SECONDS="${EVENT_WINDOW_SECONDS:-3600}"
EVENT_MAX_RECORDS="${EVENT_MAX_RECORDS:-500}"
INSTALL_ROOT="/opt/infra-assurance"
CONFIG_DIR="/etc/infra-assurance"
STATE_DIR="/var/lib/infra-assurance"
SERVICE_USER="infra-assurance"
OBSERVER_KUBECONFIG="${CONFIG_DIR}/kubeconfig"
PREFLIGHT_BIN="/usr/local/bin/iia-k8s-preflight"
HISTORY_BIN="/usr/local/bin/iia-k8s-history"
GIT_SOURCE_BIN="/usr/local/bin/iia-git-source"
INVENTORY_BIN="/usr/local/bin/iia-inventory"
PREFLIGHT_EXAMPLE="${CONFIG_DIR}/examples/hypothetical-app-deployment.json"

GIT_CONFIG="${CONFIG_DIR}/git-source.json"
GIT_CONFIG_DIR="${CONFIG_DIR}/git"
GIT_PRIVATE_KEY="${GIT_CONFIG_DIR}/api-cluster-infra_ed25519"
GIT_PUBLIC_KEY="${GIT_PRIVATE_KEY}.pub"
GIT_KNOWN_HOSTS="${GIT_CONFIG_DIR}/known_hosts"
GIT_STATE_DIR="${STATE_DIR}/git"
DECLARED_STATE_DIR="${STATE_DIR}/declared"
DECLARED_CURRENT_DIR="${DECLARED_STATE_DIR}/current"
DECLARED_SOURCE_STATUS="${DECLARED_STATE_DIR}/source-status.json"

command -v kubectl >/dev/null
command -v python3 >/dev/null
command -v git >/dev/null
command -v ssh-keygen >/dev/null

if [[ "${PROMETHEUS_NAMESPACE}" != "monitoring" || "${PROMETHEUS_SERVICE}" != "kube-prom-stack-prometheus" || "${PROMETHEUS_PORT}" != "9090" ]]; then
  echo "Current Prometheus proxy RBAC is pinned to monitoring/kube-prom-stack-prometheus:9090; update reviewed RBAC before changing PROMETHEUS_NAMESPACE, PROMETHEUS_SERVICE, or PROMETHEUS_PORT." >&2
  exit 1
fi
if [[ "${ALERTMANAGER_NAMESPACE}" != "monitoring" || "${ALERTMANAGER_SERVICE}" != "kube-prom-stack-alertmanager" || "${ALERTMANAGER_PORT}" != "9093" ]]; then
  echo "Current Alertmanager proxy RBAC is pinned to monitoring/kube-prom-stack-alertmanager:9093; update reviewed RBAC before changing ALERTMANAGER_NAMESPACE, ALERTMANAGER_SERVICE, or ALERTMANAGER_PORT." >&2
  exit 1
fi
PROMETHEUS_PROXY_NAME="${PROMETHEUS_SERVICE}:${PROMETHEUS_PORT}"
ALERTMANAGER_PROXY_NAME="${ALERTMANAGER_SERVICE}:${ALERTMANAGER_PORT}"

if ! id "${SERVICE_USER}" >/dev/null 2>&1; then
  useradd --system --home-dir "${STATE_DIR}" --create-home --shell /usr/sbin/nologin "${SERVICE_USER}"
fi

install -d -o root -g "${SERVICE_USER}" -m 0750 "${CONFIG_DIR}"
install -d -o root -g "${SERVICE_USER}" -m 0750 "${CONFIG_DIR}/examples"
install -d -o root -g "${SERVICE_USER}" -m 0750 "${GIT_CONFIG_DIR}"
install -d -o "${SERVICE_USER}" -g "${SERVICE_USER}" -m 0750 "${STATE_DIR}/evidence"
install -d -o "${SERVICE_USER}" -g "${SERVICE_USER}" -m 0750 "${STATE_DIR}/history"
install -d -o "${SERVICE_USER}" -g "${SERVICE_USER}" -m 0750 "${STATE_DIR}/history/kubernetes"
install -d -o "${SERVICE_USER}" -g "${SERVICE_USER}" -m 0750 "${GIT_STATE_DIR}"
install -d -o "${SERVICE_USER}" -g "${SERVICE_USER}" -m 0750 "${DECLARED_STATE_DIR}"
install -d -o "${SERVICE_USER}" -g "${SERVICE_USER}" -m 0750 "${DECLARED_CURRENT_DIR}"
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

if [[ ! -s "${GIT_PRIVATE_KEY}" || ! -s "${GIT_PUBLIC_KEY}" ]]; then
  rm -f "${GIT_PRIVATE_KEY}" "${GIT_PUBLIC_KEY}"
  ssh-keygen \
    -q \
    -t ed25519 \
    -N '' \
    -C 'infra-assurance:ben-edu/api-cluster-infra' \
    -f "${GIT_PRIVATE_KEY}"
fi
chown "${SERVICE_USER}:${SERVICE_USER}" "${GIT_PRIVATE_KEY}"
chmod 0600 "${GIT_PRIVATE_KEY}"
chown root:"${SERVICE_USER}" "${GIT_PUBLIC_KEY}"
chmod 0644 "${GIT_PUBLIC_KEY}"

GIT_HOST_KEYS_TMP="$(mktemp)"
if python3 - "${GIT_HOST_KEYS_TMP}" <<'PY'
import json
import sys
import urllib.request

request = urllib.request.Request(
    "https://api.github.com/meta",
    headers={"User-Agent": "infrastructure-intelligence-assurance"},
)
with urllib.request.urlopen(request, timeout=15) as response:
    value = json.load(response)
keys = value.get("ssh_keys", [])
if not keys:
    raise SystemExit("GitHub metadata returned no SSH host keys")
with open(sys.argv[1], "w", encoding="utf-8") as handle:
    for key in keys:
        handle.write(f"github.com {key}\n")
PY
then
  install -o root -g "${SERVICE_USER}" -m 0644 "${GIT_HOST_KEYS_TMP}" "${GIT_KNOWN_HOSTS}"
elif [[ ! -s "${GIT_KNOWN_HOSTS}" ]]; then
  rm -f "${GIT_HOST_KEYS_TMP}"
  echo "Could not initialize trusted GitHub SSH host keys and no previous known_hosts file exists." >&2
  exit 1
fi
rm -f "${GIT_HOST_KEYS_TMP}"

cat > "${GIT_CONFIG}" <<EOF
{
  "git_source_version": "0.2",
  "sources": [
    {
      "id": "github.com/ben-edu/api-cluster-infra",
      "repository": "git@github.com:ben-edu/api-cluster-infra.git",
      "branch": "main",
      "cluster_id": "${CLUSTER_ID}",
      "raw_manifest_paths": [
        "kubernetes/bookstack/01-pvc.yaml",
        "kubernetes/bookstack/02-mariadb.yaml",
        "kubernetes/bookstack/03-bookstack.yaml",
        "kubernetes/validation/nginx/nginx-validation.yaml"
      ],
      "kustomize_targets": [
        "kubernetes/fastapi-platform/overlays/dev",
        "kubernetes/fastapi-platform/overlays/prod"
      ],
      "private_key_file": "${GIT_PRIVATE_KEY}",
      "public_key_file": "${GIT_PUBLIC_KEY}",
      "known_hosts_file": "${GIT_KNOWN_HOSTS}"
    }
  ]
}
EOF
chown root:"${SERVICE_USER}" "${GIT_CONFIG}"
chmod 0640 "${GIT_CONFIG}"

rm -rf "${INSTALL_ROOT}/src"
cp -a "${REPO_ROOT}/src" "${INSTALL_ROOT}/src"
chown -R root:root "${INSTALL_ROOT}/src"
install -o root -g "${SERVICE_USER}" -m 0640 \
  "${REPO_ROOT}/examples/requests/hypothetical-app-deployment.json" \
  "${PREFLIGHT_EXAMPLE}"

cat > "${PREFLIGHT_BIN}" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=/opt/infra-assurance/src
exec /usr/bin/python3 -m infra_assurance.planning_preflight "$@"
EOF
chown root:root "${PREFLIGHT_BIN}"
chmod 0755 "${PREFLIGHT_BIN}"

cat > "${HISTORY_BIN}" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=/opt/infra-assurance/src
exec /usr/bin/python3 -m infra_assurance.history_cli "$@"
EOF
chown root:root "${HISTORY_BIN}"
chmod 0755 "${HISTORY_BIN}"

cat > "${GIT_SOURCE_BIN}" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=/opt/infra-assurance/src
exec /usr/bin/python3 -m infra_assurance.git_declared_observer "$@"
EOF
chown root:root "${GIT_SOURCE_BIN}"
chmod 0755 "${GIT_SOURCE_BIN}"

cat > "${INVENTORY_BIN}" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=/opt/infra-assurance/src
exec /usr/bin/python3 -m infra_assurance.inventory_cli "$@"
EOF
chown root:root "${INVENTORY_BIN}"
chmod 0755 "${INVENTORY_BIN}"

cat > "${CONFIG_DIR}/collector.env" <<EOF
IIA_CLUSTER_ID=${CLUSTER_ID}
IIA_HISTORY_RETENTION=${HISTORY_RETENTION}
IIA_PROMETHEUS_NAMESPACE=${PROMETHEUS_NAMESPACE}
IIA_PROMETHEUS_SERVICE=${PROMETHEUS_SERVICE}
IIA_PROMETHEUS_PORT=${PROMETHEUS_PORT}
IIA_ALERTMANAGER_NAMESPACE=${ALERTMANAGER_NAMESPACE}
IIA_ALERTMANAGER_SERVICE=${ALERTMANAGER_SERVICE}
IIA_ALERTMANAGER_PORT=${ALERTMANAGER_PORT}
IIA_EVENT_WINDOW_SECONDS=${EVENT_WINDOW_SECONDS}
IIA_EVENT_MAX_RECORDS=${EVENT_MAX_RECORDS}
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
assert_can_i yes list events --all-namespaces
assert_can_i yes list prometheuses.monitoring.coreos.com --all-namespaces
assert_can_i yes list servicemonitors.monitoring.coreos.com --all-namespaces
assert_can_i yes list podmonitors.monitoring.coreos.com --all-namespaces
assert_can_i yes get "services/${PROMETHEUS_PROXY_NAME}" --subresource=proxy -n "${PROMETHEUS_NAMESPACE}"
assert_can_i yes get "services/${ALERTMANAGER_PROXY_NAME}" --subresource=proxy -n "${ALERTMANAGER_NAMESPACE}"
assert_can_i no get services/not-authorized:9090 --subresource=proxy -n "${PROMETHEUS_NAMESPACE}"
assert_can_i no get services/not-authorized:9093 --subresource=proxy -n "${ALERTMANAGER_NAMESPACE}"
assert_can_i no get "services/${PROMETHEUS_PROXY_NAME}" --subresource=proxy -n default
assert_can_i no get "services/${ALERTMANAGER_PROXY_NAME}" --subresource=proxy -n default
assert_can_i no get "services/${PROMETHEUS_SERVICE}" --subresource=proxy -n "${PROMETHEUS_NAMESPACE}"
assert_can_i no get "services/${ALERTMANAGER_SERVICE}" --subresource=proxy -n "${ALERTMANAGER_NAMESPACE}"
assert_can_i no get services/alertmanager-operated:9093 --subresource=proxy -n "${ALERTMANAGER_NAMESPACE}"
assert_can_i no list secrets --all-namespaces
assert_can_i no create events -n default
assert_can_i no create deployments.apps -n default
assert_can_i no create servicemonitors.monitoring.coreos.com -n monitoring

echo "Observer installed."
echo "Evidence:         ${STATE_DIR}/evidence/kubernetes.json"
echo "Context:          ${STATE_DIR}/evidence/context.json"
echo "Topology:         ${STATE_DIR}/evidence/topology.json"
echo "History:          ${STATE_DIR}/history/kubernetes"
echo "Latest diff:      ${STATE_DIR}/evidence/diff.json"
echo "Latest drift:     ${STATE_DIR}/evidence/drift.json"
echo "Change context:   ${STATE_DIR}/evidence/change-context.json"
echo "Observability:    ${STATE_DIR}/evidence/observability-coverage.json"
echo "Obs. context:     ${STATE_DIR}/evidence/observability-coverage.md"
echo "Prometheus runtime:${STATE_DIR}/evidence/prometheus-runtime.json"
echo "Prom. runtime ctx: ${STATE_DIR}/evidence/prometheus-runtime.md"
echo "Alertmanager runtime:${STATE_DIR}/evidence/alertmanager-runtime.json"
echo "Alertmanager ctx: ${STATE_DIR}/evidence/alertmanager-runtime.md"
echo "Alert attention:  ${STATE_DIR}/evidence/alert-attention.json"
echo "Attention context:${STATE_DIR}/evidence/alert-attention.md"
echo "Kubernetes Events:${STATE_DIR}/evidence/kubernetes-event-runtime.json"
echo "Event context:    ${STATE_DIR}/evidence/kubernetes-event-runtime.md"
echo "Event correlation:${STATE_DIR}/evidence/kubernetes-event-correlation.json"
echo "Event corr. ctx:  ${STATE_DIR}/evidence/kubernetes-event-correlation.md"
echo "Inventory JSON:   ${STATE_DIR}/evidence/inventory.json"
echo "Inventory context:${STATE_DIR}/evidence/inventory.md"
echo "Preflight CLI:    ${PREFLIGHT_BIN}"
echo "History CLI:      ${HISTORY_BIN}"
echo "Git source CLI:   ${GIT_SOURCE_BIN}"
echo "Inventory CLI:    ${INVENTORY_BIN}"
echo "Prometheus source:${PROMETHEUS_NAMESPACE}/${PROMETHEUS_PROXY_NAME}"
echo "Alertmanager source:${ALERTMANAGER_NAMESPACE}/${ALERTMANAGER_PROXY_NAME}"
echo "Event window:     ${EVENT_WINDOW_SECONDS}s max=${EVENT_MAX_RECORDS}"
echo "Git source:       github.com/ben-edu/api-cluster-infra"
echo "Declared state:   ${DECLARED_CURRENT_DIR}"
echo "Git source status:${DECLARED_SOURCE_STATUS}"
echo "Example request:  ${PREFLIGHT_EXAMPLE}"
echo
echo "Read-only Git deploy public key:"
cat "${GIT_PUBLIC_KEY}"
echo
systemctl --no-pager --full status infra-assurance-kubernetes.service || true
