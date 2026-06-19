"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflowstatus"}
STATUS_CHANGED_TRIGGERS = {
    "statuschanged",
    "statechanged",
    "workflowstatechanged",
    "statuschange",
    "statechange",
}
GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    payload = _payload_context(event)
    if not _is_status_change(payload):
        return None

    new_status = _extract_new_status(payload)
    if _normalize(new_status) != _normalize(RESEARCH_STATUS):
        return None

    issue_id = _clean_text(_first_value(payload, ("issueId", "issue_id", "id", "identifier", "key")))
    title = _clean_text(_first_value(payload, ("title", "name", "issueTitle")))
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{RESEARCH_PREFIX}: {title}",
    }


def _payload_context(event: Mapping[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = {}

    containers = (
        _as_mapping(event.get("automation_trigger_info")),
        _as_mapping(event.get("automationTriggerInfo")),
    )
    for container in containers:
        if container:
            _merge(context, _payload_context(container))

    trigger_context = _as_mapping(event.get("triggerContext"))
    if trigger_context:
        _merge(context, _payload_context(trigger_context))

    data = _as_mapping(event.get("data"))
    if data:
        _merge(context, _payload_context(data))

    issue = _as_mapping(event.get("issue"))
    if issue:
        _merge(context, _flatten_issue(issue))

    _merge(context, _flatten_issue(event))
    _merge(context, event)
    return context


def _flatten_issue(issue: Mapping[str, Any]) -> dict[str, Any]:
    flattened = dict(issue)

    for key in ("status", "state", "workflowState", "workflowStatus"):
        value = issue.get(key)
        if isinstance(value, Mapping):
            name = _first_value(value, ("name", "title", "id", "key"))
            if name is not None:
                flattened[key] = name

    return flattened


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    ]
    normalized_triggers = {_normalize(value) for value in trigger_values if value is not None}

    if normalized_triggers & STATUS_CHANGED_TRIGGERS:
        return True

    if normalized_triggers & GENERIC_UPDATE_TRIGGERS:
        return _updated_status_fields(payload)

    return False


def _updated_status_fields(payload: Mapping[str, Any]) -> bool:
    candidates = (
        payload.get("updatedFields"),
        payload.get("updated_fields"),
        payload.get("changedFields"),
        payload.get("changed_fields"),
    )
    for candidate in candidates:
        if _contains_status_field(candidate):
            return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize(key) in STATUS_FIELDS for key in changes)

    if isinstance(changes, Sequence) and not isinstance(changes, (str, bytes, bytearray)):
        return any(_contains_status_field(change) for change in changes)

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize(value) in STATUS_FIELDS

    if isinstance(value, Mapping):
        field_name = _first_value(value, ("field", "fieldName", "name", "key"))
        return _normalize(field_name) in STATUS_FIELDS

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_status_field(item) for item in value)

    return False


def _extract_new_status(payload: Mapping[str, Any]) -> Any:
    direct_status = _first_value(
        payload,
        (
            "newStatus",
            "new_status",
            "statusName",
            "stateName",
            "workflowStateName",
            "workflowStatusName",
        ),
    )
    if direct_status is not None:
        return direct_status

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _normalize(key) in STATUS_FIELDS:
                return _change_new_value(value)

    if isinstance(changes, Sequence) and not isinstance(changes, (str, bytes, bytearray)):
        for change in changes:
            if isinstance(change, Mapping):
                field_name = _first_value(change, ("field", "fieldName", "name", "key"))
                if _normalize(field_name) in STATUS_FIELDS:
                    return _change_new_value(change)

    for status_key in ("status", "state", "workflowState", "workflowStatus"):
        value = payload.get(status_key)
        if isinstance(value, Mapping):
            nested = _first_value(value, ("name", "title", "id", "key"))
            if nested is not None:
                return nested
        elif value is not None:
            return value

    return None


def _change_new_value(change: Any) -> Any:
    if isinstance(change, Mapping):
        value = _first_value(change, ("newValue", "new_value", "to", "after", "value", "name"))
        if isinstance(value, Mapping):
            return _first_value(value, ("name", "title", "id", "key"))
        return value
    return change


def _first_value(mapping: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            return value
    return None


def _merge(target: dict[str, Any], source: Mapping[str, Any]) -> None:
    for key, value in source.items():
        if value is not None:
            target[key] = value


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _has_research_prefix(title: str) -> bool:
    return bool(re.match(rf"^\s*{re.escape(RESEARCH_PREFIX)}\b", title, flags=re.IGNORECASE))


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is None:
        return 0

    print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
