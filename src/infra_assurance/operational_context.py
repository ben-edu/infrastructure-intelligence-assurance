from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .evidence import freshness


def _rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _label(subject: dict[str, Any]) -> str:
    namespace = f"{subject['namespace']}/" if subject.get("namespace") else ""
    return f"{subject['kind']}/{namespace}{subject['name']}"


def _fact(envelope: dict[str, Any], now: datetime) -> dict[str, Any]:
    return {
        "subject": _label(envelope["subject"]),
        "plane": envelope["plane"],
        "value": envelope["data"],
        "freshness": freshness(envelope, now),
        "evidence_ids": [envelope["evidence_id"]],
    }


def _is_collection(envelope: dict[str, Any]) -> bool:
    return envelope["subject"]["kind"].endswith("Collection")


def _scaled_to_zero(envelope: dict[str, Any]) -> bool:
    kind = envelope["subject"]["kind"]
    data = envelope["data"]
    return kind in {"Deployment", "StatefulSet"} and data.get("desired_replicas") == 0


def _operational_inferences(envelope: dict[str, Any]) -> list[str]:
    kind = envelope["subject"]["kind"]
    data = envelope["data"]
    label = _label(envelope["subject"])
    statements: list[str] = []

    if kind == "Namespace" and data.get("phase") not in {None, "Active"}:
        statements.append(f"{label} is not Active (phase={data.get('phase')}).")

    elif kind == "Node":
        if data.get("ready") is False:
            statements.append(f"{label} is not Ready.")
        if data.get("unschedulable") is True:
            statements.append(f"{label} is unschedulable (cordoned).")

    elif kind in {"Deployment", "StatefulSet"}:
        desired = data.get("desired_replicas")
        ready = data.get("ready_replicas")
        if isinstance(desired, int) and desired > 0 and isinstance(ready, int) and ready < desired:
            statements.append(f"{label} has fewer ready replicas than desired ({ready}/{desired}).")

    elif kind == "DaemonSet":
        desired = data.get("desired_scheduled")
        ready = data.get("ready_scheduled")
        if isinstance(desired, int) and desired > 0 and isinstance(ready, int) and ready < desired:
            statements.append(f"{label} has fewer ready pods than desired ({ready}/{desired}).")

    elif kind == "PersistentVolumeClaim":
        phase = data.get("phase")
        if phase not in {None, "Bound"}:
            statements.append(f"{label} is not Bound (phase={phase}).")

    return statements


def _is_exception(envelope: dict[str, Any]) -> bool:
    return _scaled_to_zero(envelope) or bool(_operational_inferences(envelope))


def build_operational_context(
    snapshot: dict[str, Any], *, now: datetime | None = None
) -> dict[str, Any]:
    """Build compact, task-oriented context while preserving raw evidence separately."""
    now = now or datetime.now(timezone.utc)
    facts: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    inferences: list[dict[str, Any]] = []
    required: list[dict[str, Any]] = []

    for envelope in snapshot["evidence"]:
        subject = envelope["subject"]
        label = _label(subject)

        if envelope["observation_status"] == "FAILED_TO_OBSERVE":
            unknowns.append({"subject": label, "reason": "Latest collection attempt failed."})
            failures.append(
                {
                    "subject": label,
                    "evidence_id": envelope["evidence_id"],
                    "error_codes": [error["code"] for error in envelope["errors"]],
                }
            )
            required.append(
                {
                    "question": f"Can {label} be observed successfully now?",
                    "reason": "The latest collection attempt failed, so current state is unknown.",
                }
            )
            continue

        if _is_collection(envelope):
            collection_fact = _fact(envelope, now)
            facts.append(collection_fact)
            if collection_fact["freshness"] == "STALE":
                required.append(
                    {
                        "question": f"What is the current state of {label}?",
                        "reason": "Inventory collection evidence has expired.",
                    }
                )
            continue

        if _is_exception(envelope):
            facts.append(_fact(envelope, now))
            for statement in _operational_inferences(envelope):
                inferences.append(
                    {
                        "statement": statement,
                        "evidence_ids": [envelope["evidence_id"]],
                    }
                )

    return {
        "context_version": "0.1",
        "task": {
            "type": "kubernetes_operational_inventory",
            "scope": {"cluster": snapshot["cluster_id"], "namespace": None},
            "mutation_allowed": False,
        },
        "generated_at": _rfc3339(now),
        "facts": facts,
        "unknowns": unknowns,
        "observation_failures": failures,
        "inferences": inferences,
        "required_live_verification": required,
    }


def _fact_summary(fact: dict[str, Any]) -> str:
    subject = fact["subject"]
    value = fact["value"]

    if subject.endswith("Collection/*"):
        return f"{value.get('resource_kind')}: {value.get('item_count')}"
    if subject.startswith("Node/"):
        return f"{subject}: ready={value.get('ready')}, unschedulable={value.get('unschedulable')}"
    if subject.startswith("Deployment/"):
        return f"{subject}: desired={value.get('desired_replicas')}, ready={value.get('ready_replicas')}, available={value.get('available_replicas')}"
    if subject.startswith("StatefulSet/"):
        return f"{subject}: desired={value.get('desired_replicas')}, ready={value.get('ready_replicas')}"
    if subject.startswith("DaemonSet/"):
        return f"{subject}: desired={value.get('desired_scheduled')}, ready={value.get('ready_scheduled')}, available={value.get('available_scheduled')}"
    if subject.startswith("PersistentVolumeClaim/"):
        return f"{subject}: phase={value.get('phase')}, storage_class={value.get('storage_class')}"
    if subject.startswith("Namespace/"):
        return f"{subject}: phase={value.get('phase')}"
    return f"{subject}: {json.dumps(value, sort_keys=True)}"


def render_operational_context_markdown(
    snapshot: dict[str, Any], context: dict[str, Any]
) -> str:
    collection_facts = [fact for fact in context["facts"] if fact["subject"].endswith("Collection/*")]
    exception_facts = [fact for fact in context["facts"] if not fact["subject"].endswith("Collection/*")]

    lines = [
        "# Kubernetes Operational Context",
        "",
        f"Cluster: `{snapshot['cluster_id']}`",
        f"Generated: `{context['generated_at']}`",
        "Mutation allowed: `false`",
        "",
        "## Inventory coverage",
        "",
    ]

    if collection_facts:
        for fact in collection_facts:
            lines.append(f"- {_fact_summary(fact)} ({fact['freshness']})")
    else:
        lines.append("- No successful collection facts are available.")

    lines.extend(["", "## Attention", ""])
    if context["inferences"]:
        for inference in context["inferences"]:
            lines.append(f"- {inference['statement']}")
    else:
        lines.append("- No current operational exceptions were inferred from the collected resource fields.")

    lines.extend(["", "## Exceptional observed conditions", ""])
    if exception_facts:
        for fact in exception_facts:
            lines.append(f"- {_fact_summary(fact)} ({fact['freshness']})")
    else:
        lines.append("- None.")

    lines.extend(["", "## Unknown or failed observation", ""])
    if context["observation_failures"]:
        for failure in context["observation_failures"]:
            codes = ", ".join(failure["error_codes"])
            lines.append(f"- {failure['subject']}: {codes}")
    else:
        lines.append("- None.")

    lines.extend(["", "## Required live verification", ""])
    if context["required_live_verification"]:
        for verification in context["required_live_verification"]:
            lines.append(f"- {verification['question']} — {verification['reason']}")
    else:
        lines.append("- None.")

    lines.extend(
        [
            "",
            "## Trust boundary",
            "",
            "Raw normalized evidence remains in `kubernetes.json`; this document is a compact operational projection, not a replacement for source evidence.",
            "",
        ]
    )
    return "\n".join(lines)
