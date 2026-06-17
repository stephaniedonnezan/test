"""Build Linear issue title update actions for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_KEYS = {
    "status",
    "state",
    "workflowstate",
    "workflow_state",
    "workflow status",
    "workflow_status",
}

_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "statuschange",
    "statuschanged",
    "issuestatuschange",
    "issuestatuschanged",
    "statechange",
    "statechanged",
    "workflowstatechange",
    "workflowstatechanged",
}

_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    The automation payloads seen by Cursor can be either flat
    ``triggerContext`` dictionaries or nested Linear webhook payloads. This
    function accepts both shapes and returns a serializable action for the
    caller to apply through the Linear API.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _canonical(new_status) != _canonical(TARGET_STATUS):
        return None

    title = _extract_title(event)
    issue_id = _extract_issue_id(event)
    if not title or not issue_id:
        return None

    clean_title = title.strip()
    clean_issue_id = issue_id.strip()
    if not clean_title or not clean_issue_id:
        return None

    if clean_title.lower().startswith(RESEARCH_PREFIX.lower()):
        updated_title = clean_title
    else:
        updated_title = f"{RESEARCH_PREFIX}: {clean_title}"

    return {
        "action": "update_issue_title",
        "issueId": clean_issue_id,
        "title": updated_title,
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = [
        value
        for payload in _candidate_payloads(event)
        for key in ("trigger", "action", "type", "webhookType", "webhook_type")
        for value in [_coerce_string(payload.get(key))]
        if value
    ]
    trigger_codes = {_canonical(value) for value in trigger_values}

    if trigger_codes & _DIRECT_STATUS_CHANGE_TRIGGERS:
        return True

    if trigger_codes & _GENERIC_UPDATE_TRIGGERS:
        return _status_field_changed(event)

    # Some webhook wrappers omit an explicit action but still include change
    # metadata. Treat that as a status change only when status/state changed.
    return bool(trigger_codes) and _status_field_changed(event)


def _status_field_changed(event: Mapping[str, Any]) -> bool:
    if _first_string(event, ("oldStatus", "old_status", "previousStatus", "previous_status")):
        if _first_string(event, ("newStatus", "new_status")):
            return True

    for payload in _walk_mappings(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(payload.get(key)):
                return True

        for key in ("changes", "changed", "updates"):
            value = payload.get(key)
            if isinstance(value, Mapping) and _mapping_mentions_status_field(value):
                return True

    return False


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    explicit = _first_string(event, explicit_keys)
    if explicit:
        return explicit

    changed = _status_from_change_metadata(event)
    if changed:
        return changed

    for payload in _candidate_payloads(event):
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _extract_name(payload.get(key))
            if status:
                return status

    return None


def _status_from_change_metadata(event: Mapping[str, Any]) -> str | None:
    for payload in _walk_mappings(event):
        for key in ("changes", "changed", "updates", "updatedFields", "updated_fields"):
            value = payload.get(key)
            if not isinstance(value, Mapping):
                continue
            for field_name, field_value in value.items():
                if not _is_status_field_name(field_name):
                    continue
                status = _extract_changed_value(field_value)
                if status:
                    return status
    return None


def _extract_changed_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in (
            "newValue",
            "new_value",
            "to",
            "after",
            "value",
            "name",
            "displayName",
            "display_name",
        ):
            extracted = _extract_name(value.get(key))
            if extracted:
                return extracted
        return None
    return _coerce_string(value)


def _extract_title(event: Mapping[str, Any]) -> str | None:
    return _first_string(event, ("title",))


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    return _first_string(event, ("issueId", "issue_id", "identifier", "key", "id"))


def _first_string(event: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for payload in _candidate_payloads(event):
        for key in keys:
            value = _coerce_string(payload.get(key))
            if value:
                return value
    return None


def _candidate_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    payloads: list[Mapping[str, Any]] = []

    def add(payload: Mapping[str, Any]) -> None:
        if any(payload is existing for existing in payloads):
            return
        payloads.append(payload)
        for key in ("triggerContext", "data", "issue", "resource", "entity", "payload"):
            child = payload.get(key)
            if isinstance(child, Mapping):
                add(child)

    add(event)
    return payloads


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_mappings(child)


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        return _mapping_mentions_status_field(value)
    if isinstance(value, (list, tuple, set)):
        return any(_contains_status_field(item) for item in value)
    return False


def _mapping_mentions_status_field(value: Mapping[Any, Any]) -> bool:
    return any(
        _is_status_field_name(key)
        or (isinstance(child, Mapping) and _mapping_mentions_status_field(child))
        or _contains_status_field(child)
        for key, child in value.items()
    )


def _is_status_field_name(value: Any) -> bool:
    text = _coerce_string(value)
    if not text:
        return False
    return _canonical(text) in {_canonical(field) for field in _STATUS_FIELD_KEYS}


def _extract_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "displayName", "display_name", "title", "value"):
            extracted = _extract_name(value.get(key))
            if extracted:
                return extracted
        return None
    return _coerce_string(value)


def _coerce_string(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _canonical(value: str | None) -> str:
    if not value:
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", "", spaced.lower())


def main() -> int:
    action = build_issue_title_update(json.load(sys.stdin))
    print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
