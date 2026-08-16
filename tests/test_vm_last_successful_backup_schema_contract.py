from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_vm_integration_reuses_accepted_pve_task_result_id_contract():
    source_schema = json.loads(
        (ROOT / "schemas" / "proxmox-ve-backup-task-results.schema.json").read_text()
    )
    integration_schema = json.loads(
        (ROOT / "schemas" / "vm-last-successful-backup-integration.schema.json").read_text()
    )

    source_pattern = source_schema["$defs"]["task_result"]["properties"]["task_result_id"]["pattern"]
    integration_pattern = integration_schema["properties"]["assets"]["items"]["properties"]["assurance"]["properties"]["last_successful_backup_evidence"]["oneOf"][1]["properties"]["task_result_id"]["pattern"]

    assert source_pattern == r"^pve-backup-task:[a-f0-9]{24}$"
    assert integration_pattern == source_pattern

    accepted_id = "pve-backup-task:f37e030ddb424ce85a743c30"
    stale_fixture_shape = "pve-task-f37e030ddb424ce85a743c30"

    assert re.fullmatch(source_pattern, accepted_id)
    assert re.fullmatch(integration_pattern, accepted_id)
    assert not re.fullmatch(integration_pattern, stale_fixture_shape)
