from __future__ import annotations

import argparse
import json
import re
import subprocess
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode

from .io_utils import atomic_write_json, atomic_write_text
from .prometheus_runtime_intelligence import (
    DEFAULT_PROMETHEUS_NAMESPACE,
    DEFAULT_PROMETHEUS_PORT,
    DEFAULT_PROMETHEUS_SERVICE,
    DEFAULT_TIMEOUT_SECONDS,
    _proxy_get_json,
    _proxy_path,
)

RULE_CONTEXT_VERSION = "0.1"
DEFAULT_TTL_SECONDS = 300
DEFAULT_MAX_ALERT_NAMES = 20
Runner = Callable[..., subprocess.CompletedProcess[str]]
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9_.:-]{1,200}$")


def _rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_identifier(value: Any, *, fallback: str) -> str:
    if not isinstance(value, str):
        return fallback
    value = value.strip()
    if not _SAFE_IDENTIFIER.fullmatch(value):
        return fallback
    return value


def _health(value: Any) -> str:
    lowered = str(value or "").lower()
    if lowered in {"ok", "good"}:
        return "OK"
    if lowered in {"err", "error", "bad"}:
        return "ERROR"
    return "UNKNOWN"


def _state(value: Any) -> str:
    lowered = str(value or "").lower()
    if lowered == "firing":
        return "FIRING"
    if lowered == "pending":
        return "PENDING"
    if lowered == "inactive":
        return "INACTIVE"
    return "UNKNOWN"


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _active_alert_names(incident: dict[str, Any]) -> list[str]:
    names: set[str] = set()
    for candidate in incident.get("candidates", []):
        if candidate.get("state") != "ACTIVE":
            continue
        for alert in candidate.get("alerts", []):
            name = _safe_identifier(alert.get("alertname"), fallback="")
            if name:
                names.add(name)
    return sorted(names)


def _candidate_specs(incident: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for candidate in incident.get("candidates", []):
        if candidate.get("state") != "ACTIVE":
            continue
        names = sorted(
            {
                name
                for alert in candidate.get("alerts", [])
                if (name := _safe_identifier(alert.get("alertname"), fallback=""))
            }
        )
        result.append(
            {
                "candidate_id": candidate.get("candidate_id"),
                "scope": {
                    "type": candidate.get("scope", {}).get("type"),
                    "subject": candidate.get("scope", {}).get("subject"),
                },
                "alert_names": names,
            }
        )
    return result


def _rules_api_path(
    *,
    namespace: str,
    service: str,
    port: int,
    alert_names: list[str],
) -> str:
    query_items: list[tuple[str, str]] = [
        ("type", "alert"),
        ("exclude_alerts", "true"),
    ]
    query_items.extend(("rule_name[]", name) for name in alert_names)
    api_path = "api/v1/rules?" + urlencode(query_items)
    return _proxy_path(
        namespace=namespace,
        service=service,
        port=port,
        api_path=api_path,
    )


def _normalize_rules(
    data: dict[str, Any],
    *,
    requested_names: set[str],
    now: datetime,
    ttl_seconds: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups = data.get("groups")
    if not isinstance(groups, list):
        return [], [
            {
                "code": "PROMETHEUS_RULES_RESPONSE_INVALID",
                "subject": None,
                "statement": "Prometheus rule data did not contain a groups list.",
                "evidence_ids": [],
            }
        ]

    records: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for group in groups:
        if not isinstance(group, dict):
            continue
        group_name = _safe_identifier(group.get("name"), fallback="REDACTED_GROUP")
        rules = group.get("rules")
        if not isinstance(rules, list):
            unknowns.append(
                {
                    "code": "PROMETHEUS_RULE_GROUP_INVALID",
                    "subject": group_name,
                    "statement": "A returned Prometheus rule group did not contain a rules list.",
                    "evidence_ids": [],
                }
            )
            continue

        for item in rules:
            if not isinstance(item, dict):
                continue
            rule_type = str(item.get("type") or "").lower()
            if rule_type and rule_type != "alerting":
                continue
            name = _safe_identifier(item.get("name"), fallback="")
            if not name or name not in requested_names:
                continue

            key = (group_name, name)
            if key in seen:
                continue
            seen.add(key)

            evidence_id = f"ev-prometheus-rule-{uuid.uuid4()}"
            record = {
                "rule_id": "prom-rule-" + uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"prometheus-rule:{group_name}:{name}",
                ).hex[:24],
                "evidence_id": evidence_id,
                "observed_at": _rfc3339(now),
                "expires_at": _rfc3339(now + timedelta(seconds=ttl_seconds)),
                "alertname": name,
                "group_name": group_name,
                "rule_type": "ALERTING",
                "state": _state(item.get("state")),
                "health": _health(item.get("health")),
                "duration_seconds": _number(item.get("duration")),
                "keep_firing_for_seconds": _number(item.get("keepFiringFor")),
                "evaluation_time_seconds": _number(item.get("evaluationTime")),
                "last_evaluation": (
                    item.get("lastEvaluation")
                    if isinstance(item.get("lastEvaluation"), str)
                    and item.get("lastEvaluation")
                    else None
                ),
                "expression_persisted": False,
            }
            records.append(record)

            if record["health"] == "UNKNOWN":
                unknowns.append(
                    {
                        "code": "PROMETHEUS_RULE_HEALTH_UNKNOWN",
                        "subject": name,
                        "statement": f"Prometheus alert rule {name} did not report a recognized rule health state.",
                        "evidence_ids": [evidence_id],
                    }
                )
            if record["state"] == "UNKNOWN":
                unknowns.append(
                    {
                        "code": "PROMETHEUS_RULE_STATE_UNKNOWN",
                        "subject": name,
                        "statement": f"Prometheus alert rule {name} did not report a recognized rule state.",
                        "evidence_ids": [evidence_id],
                    }
                )

    return sorted(records, key=lambda item: (item["alertname"], item["group_name"])), unknowns


def _candidate_context(
    incident: dict[str, Any],
    rules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_name: dict[str, list[dict[str, Any]]] = {}
    for rule in rules:
        by_name.setdefault(rule["alertname"], []).append(rule)

    result: list[dict[str, Any]] = []
    for spec in _candidate_specs(incident):
        matched: list[str] = []
        evidence_ids: list[str] = []
        unmatched: list[str] = []
        for name in spec["alert_names"]:
            rule_matches = by_name.get(name, [])
            if not rule_matches:
                unmatched.append(name)
                continue
            for rule in rule_matches:
                matched.append(rule["rule_id"])
                evidence_ids.append(rule["evidence_id"])

        result.append(
            {
                "candidate_id": spec["candidate_id"],
                "scope": spec["scope"],
                "alert_names": spec["alert_names"],
                "matched_rule_ids": sorted(set(matched)),
                "unmatched_alert_names": unmatched,
                "basis": ["EXACT_ALERTNAME_PROMETHEUS_RULE_MATCH"] if matched else [],
                "evidence_ids": sorted(set(evidence_ids)),
                "required_live_verification": (
                    [
                        {
                            "target": "PROMETHEUS_RULE_INPUTS",
                            "statement": "Prometheus rule metadata is observed, but current PromQL input values are not collected by this slice and require separate live verification before causal interpretation.",
                        }
                    ]
                    if matched
                    else []
                ),
            }
        )
    return result


def build_prometheus_rule_context(
    incident: dict[str, Any],
    *,
    kubectl_context: str | None = None,
    prometheus_namespace: str = DEFAULT_PROMETHEUS_NAMESPACE,
    prometheus_service: str = DEFAULT_PROMETHEUS_SERVICE,
    prometheus_port: int = DEFAULT_PROMETHEUS_PORT,
    runner: Runner = subprocess.run,
    now: datetime | None = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_alert_names: int = DEFAULT_MAX_ALERT_NAMES,
) -> dict[str, Any]:
    if max_alert_names < 1:
        raise ValueError("max_alert_names must be positive")

    now = now or datetime.now(timezone.utc)
    cluster_id = str(incident.get("cluster_id") or "")
    if not cluster_id:
        raise ValueError("Incident artifact must identify a cluster")

    active_names_all = _active_alert_names(incident)
    requested_names = active_names_all[:max_alert_names]
    truncated = len(active_names_all) > len(requested_names)
    errors: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    rules: list[dict[str, Any]] = []
    queried = bool(requested_names)

    if truncated:
        unknowns.append(
            {
                "code": "PROMETHEUS_RULE_ALERT_SCOPE_TRUNCATED",
                "subject": None,
                "statement": f"Active alert-name rule lookup was bounded to {max_alert_names} names; omitted names remain unknown in this slice.",
                "evidence_ids": [],
            }
        )

    if requested_names:
        path = _rules_api_path(
            namespace=prometheus_namespace,
            service=prometheus_service,
            port=prometheus_port,
            alert_names=requested_names,
        )
        data, error = _proxy_get_json(
            path,
            kubectl_context=kubectl_context,
            runner=runner,
            timeout_seconds=timeout_seconds,
        )
        if error:
            errors.append({"scope": "rules", **error})
        elif data is not None:
            rules, rule_unknowns = _normalize_rules(
                data,
                requested_names=set(requested_names),
                now=now,
                ttl_seconds=ttl_seconds,
            )
            unknowns.extend(rule_unknowns)

    matched_names = sorted({rule["alertname"] for rule in rules})
    unmatched_names = sorted(set(requested_names) - set(matched_names))
    for name in unmatched_names:
        unknowns.append(
            {
                "code": "PROMETHEUS_ALERT_RULE_NOT_MATCHED",
                "subject": name,
                "statement": f"No exact Prometheus alert-rule record was returned for active alert name {name}; this does not prove the rule is absent if the source observation was incomplete.",
                "evidence_ids": [],
            }
        )

    if errors:
        source_status = "FAILED_TO_OBSERVE"
    elif truncated:
        source_status = "PARTIAL"
    else:
        source_status = "COMPLETE"

    candidate_context = _candidate_context(incident, rules)
    health_counts = Counter(rule["health"] for rule in rules)
    state_counts = Counter(rule["state"] for rule in rules)

    return {
        "prometheus_rule_context_version": RULE_CONTEXT_VERSION,
        "cluster_id": cluster_id,
        "generated_at": _rfc3339(now),
        "mutation_allowed": False,
        "source": {
            "type": "prometheus_http_api",
            "access": "kubernetes_service_proxy",
            "namespace": prometheus_namespace,
            "service": prometheus_service,
            "port": prometheus_port,
            "operation": "GET_RULES_BY_EXACT_ACTIVE_ALERTNAME",
            "queried": queried,
            "status": source_status,
            "collector": "infra_assurance.prometheus_rule_context",
            "collector_version": RULE_CONTEXT_VERSION,
        },
        "bounds": {
            "max_active_alert_names": max_alert_names,
            "active_alert_names_total": len(active_names_all),
            "active_alert_names_requested": len(requested_names),
            "active_alert_names_truncated": truncated,
        },
        "summary": {
            "active_alert_names_requested": len(requested_names),
            "alert_names_matched_to_rules": len(matched_names),
            "alert_names_unmatched": len(unmatched_names),
            "rule_records": len(rules),
            "rule_health_ok": health_counts["OK"],
            "rule_health_error": health_counts["ERROR"],
            "rule_health_unknown": health_counts["UNKNOWN"],
            "rules_firing": state_counts["FIRING"],
            "rules_pending": state_counts["PENDING"],
            "rules_inactive": state_counts["INACTIVE"],
            "rules_state_unknown": state_counts["UNKNOWN"],
            "active_candidates": len(candidate_context),
            "active_candidates_with_rule_match": sum(bool(item["matched_rule_ids"]) for item in candidate_context),
        },
        "requested_alert_names": requested_names,
        "matched_alert_names": matched_names,
        "unmatched_alert_names": unmatched_names,
        "rules": rules,
        "candidate_context": candidate_context,
        "unknowns": unknowns,
        "errors": errors,
        "caveats": [
            "Rule metadata is Prometheus-observed rule state, not proof of the current metric input values that caused an alert to fire.",
            "PromQL expressions, rule labels, annotations, rule files, embedded active alerts, last-error text, raw API payloads, URLs, credentials, and connection strings are not persisted by this slice.",
            "Exact alertname correlation is used; fuzzy rule matching is not performed.",
        ],
    }


def render_prometheus_rule_context_markdown(artifact: dict[str, Any]) -> str:
    lines = [
        "# Prometheus Rule Context",
        "",
        f"Cluster: `{artifact['cluster_id']}`",
        f"Generated: `{artifact['generated_at']}`",
        f"Mutation allowed: `{str(artifact['mutation_allowed']).lower()}`",
        f"Source status: `{artifact['source']['status']}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in artifact["summary"].items():
        lines.append(f"- {key}: {value}")

    lines += ["", "## Active candidate rule context", ""]
    if not artifact["candidate_context"]:
        lines.append("- No active incident candidate required rule lookup in this cycle.")
    for item in artifact["candidate_context"]:
        scope = item["scope"]
        lines.append(
            f"- {scope.get('type')} {scope.get('subject')} alerts={','.join(item['alert_names']) or 'none'} matched_rules={len(item['matched_rule_ids'])} unmatched={','.join(item['unmatched_alert_names']) or 'none'}"
        )

    lines += [
        "",
        "## Trust boundary",
        "",
        "This artifact confirms exact Prometheus alert-rule metadata matches only. It does not collect PromQL expressions or current metric input values and does not establish alert cause or business impact.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect bounded Prometheus alert-rule context for current active incident alert names.")
    parser.add_argument("--incident", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--summary-out", type=Path, required=True)
    parser.add_argument("--prometheus-namespace", default=DEFAULT_PROMETHEUS_NAMESPACE)
    parser.add_argument("--prometheus-service", default=DEFAULT_PROMETHEUS_SERVICE)
    parser.add_argument("--prometheus-port", type=int, default=DEFAULT_PROMETHEUS_PORT)
    parser.add_argument("--max-alert-names", type=int, default=DEFAULT_MAX_ALERT_NAMES)
    args = parser.parse_args()

    incident = json.loads(args.incident.read_text(encoding="utf-8"))
    artifact = build_prometheus_rule_context(
        incident,
        prometheus_namespace=args.prometheus_namespace,
        prometheus_service=args.prometheus_service,
        prometheus_port=args.prometheus_port,
        max_alert_names=args.max_alert_names,
    )
    atomic_write_json(args.out, artifact)
    atomic_write_text(args.summary_out, render_prometheus_rule_context_markdown(artifact))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
