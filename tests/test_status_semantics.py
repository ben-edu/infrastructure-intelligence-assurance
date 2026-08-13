import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "schemas" / "observation-envelope.schema.json").read_text(encoding="utf-8")
)
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def load_example(name: str):
    return json.loads(
        (ROOT / "examples" / "observations" / name).read_text(encoding="utf-8")
    )


def assert_invalid(instance):
    assert list(VALIDATOR.iter_errors(instance)), "expected schema validation to fail"


def freshness(envelope, now: datetime) -> str:
    expires_at = envelope["expires_at"]
    if expires_at is None:
        raise ValueError("Freshness is undefined without a successful observation expiry")
    expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    return "CURRENT" if now <= expiry else "STALE"


def test_failed_observation_cannot_claim_absence():
    record = load_example("deployment-failed-to-observe.json")
    record["existence"] = "ABSENT"
    assert_invalid(record)


def test_failed_observation_cannot_claim_presence():
    record = load_example("deployment-failed-to-observe.json")
    record["existence"] = "PRESENT"
    assert_invalid(record)


def test_absence_requires_complete_observation():
    record = load_example("deployment-absent.json")
    record["observation_status"] = "PARTIAL"
    assert_invalid(record)


def test_failed_observation_requires_error():
    record = load_example("deployment-failed-to-observe.json")
    record["errors"] = []
    assert_invalid(record)


def test_current_freshness_is_derived_from_expiry():
    record = load_example("deployment-present-current.json")
    now = datetime(2026, 8, 13, 15, 2, tzinfo=timezone.utc)
    assert freshness(record, now) == "CURRENT"


def test_stale_freshness_is_derived_from_expiry():
    record = load_example("deployment-stale.json")
    now = datetime(2026, 8, 13, 15, 2, tzinfo=timezone.utc)
    assert freshness(record, now) == "STALE"


def test_failed_observation_has_no_freshness_claim():
    record = load_example("deployment-failed-to-observe.json")
    now = datetime(2026, 8, 13, 15, 2, tzinfo=timezone.utc)
    try:
        freshness(record, now)
    except ValueError:
        pass
    else:
        raise AssertionError("failed observations must not produce CURRENT or STALE")


def test_declared_and_observed_examples_keep_separate_planes():
    observed = load_example("deployment-present-current.json")
    declared = json.loads(
        (ROOT / "examples" / "declared" / "deployment-declared-git.json").read_text(
            encoding="utf-8"
        )
    )

    assert observed["subject"] == declared["subject"]
    assert observed["plane"] == "observed"
    assert declared["plane"] == "declared"
    assert observed["data"]["desired_replicas"] != declared["data"]["desired_replicas"]


def test_example_keys_are_explicitly_allowlisted():
    allowed_keys = {
        "schema_version", "evidence_id", "plane", "subject", "system", "cluster",
        "api_group", "kind", "namespace", "name", "existence",
        "observation_status", "attempted_at", "observed_at", "expires_at", "data",
        "desired_replicas", "ready_replicas", "images", "image", "provenance",
        "source_type", "source_id", "collector", "collector_version", "operation",
        "revision", "errors", "code", "summary", "context_version", "task", "type",
        "scope", "mutation_allowed", "generated_at", "facts", "value", "freshness",
        "evidence_ids", "unknowns", "reason", "observation_failures", "inferences",
        "statement", "required_live_verification", "question", "error_codes"
    }

    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                assert key in allowed_keys, f"unexpected example field: {key}"
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    files = list((ROOT / "examples").rglob("*.json"))
    assert files
    for path in files:
        walk(json.loads(path.read_text(encoding="utf-8")))
