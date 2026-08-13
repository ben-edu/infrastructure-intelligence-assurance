import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate(instance, schema):
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
    assert not errors, "\n".join(error.message for error in errors)


def test_all_observation_examples_validate():
    schema = load_json(ROOT / "schemas" / "observation-envelope.schema.json")
    files = list((ROOT / "examples" / "observations").glob("*.json"))
    files += list((ROOT / "examples" / "declared").glob("*.json"))

    assert files
    for path in files:
        validate(load_json(path), schema)


def test_ai_context_example_validates():
    schema = load_json(ROOT / "schemas" / "ai-context.schema.json")
    validate(
        load_json(ROOT / "examples" / "context" / "deployment-planning-context.json"),
        schema,
    )
