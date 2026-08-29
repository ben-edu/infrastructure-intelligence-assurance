from __future__ import annotations

from infra_assurance.operator_attention import (
    DEFAULT_SOURCES,
    build_operator_attention_summary,
    load_default_sources,
)

MAX_PRINTED_ITEMS = 10


def _safe(value: object) -> str:
    if value is None:
        return "-"
    return str(value).replace("\n", " ")[:180]


def main() -> int:
    print("===== M7 OPERATOR ATTENTION SUMMARY PROBE =====")
    print()
    print("===== SAFETY =====")
    print("mutation_allowed: False")
    print("live_infrastructure_query_performed: False")
    print("source_artifacts_written: False")
    print("new_datastore_used: False")
    print("raw_source_artifacts_projected: False")
    print("secrets_or_credentials_projected: False")

    try:
        sources = load_default_sources(DEFAULT_SOURCES)
        summary = build_operator_attention_summary(
            sources["inventory"],
            sources["context"],
            sources["change_context"],
        )
    except (OSError, UnicodeError, ValueError) as exc:
        print()
        print("===== SOURCE STATUS =====")
        print("source_status: FAILED_TO_OBSERVE")
        print("failure_category:", type(exc).__name__)
        print("No operator-attention conclusion is allowed from this failed observation.")
        return 2

    counts = summary["summary"]
    print()
    print("===== SOURCE STATUS =====")
    print("source_status: COMPLETE")
    print("source_artifacts_loaded: 3")
    print("cluster_id:", summary["cluster_id"])
    print("scope:", summary["scope"])

    print()
    print("===== OPERATOR SUMMARY =====")
    print("workloads_total:", counts["workloads_total"])
    print("workloads_with_attention:", counts["workloads_with_attention"])
    print("attention_now_total:", counts["attention_now_total"])
    print("recent_changes_total:", counts["recent_changes_total"])
    print("unknowns_total:", counts["unknowns_total"])
    print("required_live_verification_total:", counts["required_live_verification_total"])

    print()
    print("===== ATTENTION NOW =====")
    if summary["attention_now"]:
        for index, item in enumerate(summary["attention_now"][:MAX_PRINTED_ITEMS], start=1):
            print(
                f"item={index} source={_safe(item.get('source'))} code={_safe(item.get('code'))} "
                f"severity={_safe(item.get('severity'))} subject={_safe(item.get('subject'))}"
            )
    else:
        print("NONE_OBSERVED")

    print()
    print("===== RECENT CHANGES =====")
    if summary["recent_changes"]:
        for index, item in enumerate(summary["recent_changes"][:MAX_PRINTED_ITEMS], start=1):
            print(
                f"item={index} classification={_safe(item.get('classification'))} "
                f"subject={_safe(item.get('subject'))}"
            )
    else:
        print("NONE_OBSERVED")

    print()
    print("===== UNKNOWN OR STALE =====")
    if summary["unknowns"]:
        for index, item in enumerate(summary["unknowns"][:MAX_PRINTED_ITEMS], start=1):
            print(
                f"item={index} source={_safe(item.get('source'))} code={_safe(item.get('code'))} "
                f"subject={_safe(item.get('subject'))}"
            )
    else:
        print("NONE_OBSERVED")

    print()
    print("===== REQUIRED LIVE VERIFICATION =====")
    if summary["required_live_verification"]:
        for index, item in enumerate(summary["required_live_verification"][:MAX_PRINTED_ITEMS], start=1):
            print(
                f"item={index} source={_safe(item.get('source'))} code={_safe(item.get('code'))}"
            )
    else:
        print("NONE_OBSERVED")

    print()
    print("===== TRUNCATION =====")
    for key, value in summary["truncation"].items():
        print(f"{key}: {value}")

    print()
    print("===== INTERPRETATION BOUNDARY =====")
    print("This is a derived operator-facing projection over existing Kubernetes evidence artifacts only.")
    print("It does not perform live infrastructure queries, create a new source of truth, or replace the underlying inventory/context/change-context artifacts.")
    print("Absence in a projected section is only absence in the currently loaded source artifacts, subject to their own freshness and trust boundaries.")

    print()
    print("===== TRUST BOUNDARY =====")
    print("Only allowlisted summary fields, attention metadata, recent-change metadata, unknown metadata, and required-verification metadata are projected.")
    print("Raw Kubernetes evidence, arbitrary resource values, raw diagnostics, credentials, Secret values, Terraform state, and sensitive connection strings are not read or printed by this probe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
