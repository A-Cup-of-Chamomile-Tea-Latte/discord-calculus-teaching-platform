from __future__ import annotations

from copy import deepcopy
from typing import Any

from discord_course_bots.data_lab.contracts import FIXTURE_REFS

FIXTURE_CATALOG: dict[str, dict[str, Any]] = {
    "fixture://public/basic-v1": {
        "caseRef": "TST-BASIC-001",
        "module": "M01",
        "keyword": "limit",
        "lifecycleStatus": "OPEN",
        "taAction": "REVIEW",
        "deadline": None,
        "reopenCount": 0,
        "actorRef": "SYN-LAB-TA",
        "analysisEligible": False,
        "occurredAt": "2026-08-11T04:00:00Z",
    },
    "fixture://public/close-reopen-v1": {
        "caseRef": "TST-CYCLE-001",
        "module": "M02",
        "keyword": "continuity",
        "lifecycleStatus": "OPEN",
        "taAction": "FOLLOW_UP",
        "deadline": "2026-08-13T04:00:00Z",
        "reopenCount": 0,
        "actorRef": "SYN-LAB-TA",
        "analysisEligible": False,
        "occurredAt": "2026-08-11T04:05:00Z",
    },
    "fixture://failure/stale-version-v1": {
        "caseRef": "TST-STALE-001",
        "module": "M03",
        "keyword": "derivative",
        "lifecycleStatus": "OPEN",
        "taAction": "REVIEW",
        "deadline": None,
        "reopenCount": 0,
        "actorRef": "SYN-LAB-TA",
        "analysisEligible": False,
        "occurredAt": "2026-08-11T04:10:00Z",
    },
    "fixture://failure/bad-checksum-v1": {
        "caseRef": "TST-CHECKSUM-001",
        "module": "M04",
        "keyword": "integral",
        "lifecycleStatus": "OPEN",
        "taAction": "REVIEW",
        "deadline": None,
        "reopenCount": 0,
        "actorRef": "SYN-LAB-TA",
        "analysisEligible": False,
        "occurredAt": "2026-08-11T04:15:00Z",
    },
}


def get_fixture(reference: str) -> dict[str, Any]:
    if reference not in FIXTURE_REFS or reference not in FIXTURE_CATALOG:
        raise ValueError("FIXTURE_REF_UNSUPPORTED")
    return deepcopy(FIXTURE_CATALOG[reference])
