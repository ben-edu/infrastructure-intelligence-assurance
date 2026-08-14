import json
from pathlib import Path

import jsonschema

from infra_assurance.planning_preflight import validate_request

ROOT = Path(__file__).resolve().parents[1]
REQUEST_SCHEMA = json.loads(
    (ROOT / "schemas" / "hypothetical-deployment-request.schema.json").read_text(
        encoding="utf-8"
    )
)


def test_request_examples_follow_their_strict_contract():
    files = list((ROOT / "examples" / "requests").glob("*.json"))
    assert files

    validator = jsonschema.Draft202012Validator(REQUEST_SCHEMA)
    for path in files:
        request = json.loads(path.read_text(encoding="utf-8"))
        validator.validate(request)
        validate_request(request)
