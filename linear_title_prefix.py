"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "statuschanged",
    "status updated",
    "state changed",
    "workflowstate changed",
    "workflow state changed",
}
ISSUE_UPDATE_TRIGGERS = {
    "issue updated",
    "updated issue",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    payload = _payload(event)
    if not _is_status_change(payload):
        return None

    new_status = _new_status(payload)
    if _normalize_status(new_status) != TARGET_STATUS:
        return None

    issue_id = _clean_text(_first_value(payload, ("id", "issueId", "issue_id", "identifier", "key")))
    title = _clean_text(_first_value(payload, ("title", "name")))
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Cursor and Linear webhook shapes into one lookup dict."""

    flattened: dict[str, Any] = {}

    for value in _walk_mappings(event):
        if _looks_like_issue(value) or _has_trigger_metadata(value):
            flattened.update(value)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        flattened.update(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            flattened.update(issue)
        flattened.update(data)

    flattened.update(event)
    return flattened


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize_event_type(value)
        for value in _first_values(payload, ("trigger", "webhookType", "action", "type"))
    ]

    if any(value in STATUS_CHANGE_TRIGGERS for value in trigger_values):
        return True

    if any(value in ISSUE_UPDATE_TRIGGERS for value in trigger_values):
        return _changed_fields_include_status(payload)

    return _changed_fields_include_status(payload)


def _changed_fields_include_status(payload: Mapping[str, Any]) -> bool:
    for value in _first_values(payload, ("updatedFields", "changedFields")):
        if isinstance(value, str) and _normalize_field_name(value) in STATUS_FIELDS:
            return True

        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
            for field in value:
                if _normalize_field_name(field) in STATUS_FIELDS:
                    return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(field) in STATUS_FIELDS for field in changes)

    return False


def _new_status(payload: Mapping[str, Any]) -> Any:
    for key in (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "newState",
        "new_state",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    ):
        value = payload.get(key)
        if value is not None:
            return _name_value(value)

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = changes.get(key)
            if value is None:
                continue
            if isinstance(value, Mapping):
                for nested_key in ("to", "after", "newValue", "new", "value"):
                    if nested_key in value:
                        return _name_value(value[nested_key])
            return _name_value(value)

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = payload.get(key)
        if value is not None:
            return _name_value(value)

    return None


def _first_value(payload: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    return next(_first_values(payload, keys), None)


def _first_values(payload: Mapping[str, Any], keys: tuple[str, ...]) -> Iterable[Any]:
    for key in keys:
        if key in payload:
            yield payload[key]


def _name_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if key in value:
                return value[key]
    return value


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    value = value.strip()
    return value or None


def _normalize_status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    return " ".join(_split_words(value))


def _normalize_event_type(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    return " ".join(_split_words(value))


def _normalize_field_name(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    return "".join(_split_words(value))


def _split_words(value: str) -> list[str]:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    words = re.split(r"[^A-Za-z0-9]+", spaced)
    return [word.lower() for word in words if word]


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_mappings(child)


def _looks_like_issue(value: Mapping[str, Any]) -> bool:
    return bool({"id", "issueId", "issue_id", "identifier"} & set(value)) and bool(
        {"title", "name"} & set(value)
    )


def _has_trigger_metadata(value: Mapping[str, Any]) -> bool:
    return bool({"trigger", "webhookType", "action", "type", "updatedFields", "changes"} & set(value))


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
