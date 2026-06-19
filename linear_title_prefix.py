"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statusupdated",
    "statechanged",
    "workflowstatechanged",
}
GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action for Linear issues moved to "to research".

    The Cursor automation payload is flat under ``triggerContext`` while Linear
    webhooks commonly nest issue details under ``data.issue``. This helper
    accepts both shapes and returns a serializable action for the caller to
    apply.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _merge_payload(event)
    if not _is_status_change(payload):
        return None

    status = _extract_status(payload)
    if _normalize(status) != _normalize(TARGET_STATUS):
        return None

    issue_id = _clean_string(_first_value(payload, ("issueId", "issue_id", "id", "identifier", "key")))
    title = _clean_string(_first_value(payload, ("title", "name")))
    if not issue_id or not title:
        return None
    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _merge_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten known trigger and issue containers, preserving outer metadata."""

    payload: dict[str, Any] = {}
    for value in _candidate_mappings(event):
        payload.update(value)
    return payload


def _candidate_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        candidates.append(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            candidates.append(issue)
        candidates.append(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        candidates.append(issue)

    candidates.append(event)
    return candidates


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger_values = (
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    )
    normalized_triggers = {_normalize(value) for value in trigger_values if _clean_string(value)}

    if normalized_triggers & STATUS_CHANGE_TRIGGERS:
        return True

    if normalized_triggers & GENERIC_UPDATE_TRIGGERS:
        return _updated_status_fields(payload)

    return False


def _updated_status_fields(payload: Mapping[str, Any]) -> bool:
    updated_fields = payload.get("updatedFields") or payload.get("updated_fields")
    if isinstance(updated_fields, Mapping):
        return any(_normalize(key) in STATUS_FIELDS for key in updated_fields)
    if isinstance(updated_fields, (list, tuple, set)):
        return any(_normalize(field) in STATUS_FIELDS for field in updated_fields)

    changes = payload.get("changes") or payload.get("changedFields") or payload.get("changed_fields")
    if isinstance(changes, Mapping):
        return any(_normalize(key) in STATUS_FIELDS for key in changes)
    if isinstance(changes, (list, tuple, set)):
        return any(_normalize(field) in STATUS_FIELDS for field in changes)

    return False


def _extract_status(payload: Mapping[str, Any]) -> Any:
    for key in ("newStatus", "new_status", "statusName", "status_name"):
        value = payload.get(key)
        if _clean_string(value):
            return value

    for key in ("state", "workflowState", "workflow_state", "status"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            nested_name = value.get("name") or value.get("title")
            if _clean_string(nested_name):
                return nested_name
        elif _clean_string(value):
            return value

    return None


def _first_value(payload: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = payload.get(key)
        if _clean_string(value):
            return value
    return None


def _clean_string(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _normalize(value: Any) -> str:
    text = _clean_string(value)
    if not text:
        return ""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    if result is not None:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
