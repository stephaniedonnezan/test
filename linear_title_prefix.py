"""Helpers for updating Linear issue titles when research starts."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELDS = {
    "status",
    "status_id",
    "state",
    "state_id",
    "workflowstate",
    "workflowstate_id",
    "workflow_state",
    "workflow_state_id",
}
_DIRECT_STATUS_CHANGE_EVENTS = {
    "statuschanged",
    "statuschange",
    "statuschanged",
    "status_changed",
    "status-change",
    "issue_status_changed",
    "issuestatuschanged",
}
_ISSUE_UPDATE_EVENTS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Build a title update action for Linear issues moved to To Research.

    The Cursor automation trigger provides a compact, flat ``triggerContext``
    payload. Linear webhooks are often nested under ``data`` or ``issue``. This
    function accepts both shapes and returns a side-effect-free action that the
    caller can apply through its Linear client.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _payload(event)
    if not _is_status_change(payload):
        return None

    status = _new_status(payload)
    if _normalize_status(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(payload, ("title", "name", "issueTitle", "issue_title"))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility wrapper for automation entrypoints."""

    return build_issue_title_update(event)


def _payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common automation and Linear webhook containers into one view."""

    merged: dict[str, Any] = {}

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping):
            return

        # Issue data is more specific than its enclosing webhook, so merge it
        # first and then let outer trigger metadata override event fields.
        for key in ("issue", "data", "triggerContext", "trigger_context"):
            child = value.get(key)
            if isinstance(child, Mapping):
                visit(child)

        for key, child in value.items():
            if isinstance(child, Mapping) and key in {
                "state",
                "status",
                "workflowState",
                "workflow_state",
            }:
                name = _text(child.get("name"))
                if name:
                    merged[key] = name
                    merged[f"{key}Name"] = name
            elif key not in {"issue", "data", "triggerContext", "trigger_context"}:
                merged[key] = child

    visit(event)
    return merged


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    event_values = [
        payload.get(key)
        for key in ("trigger", "event", "action", "type", "webhookType", "webhook_type")
    ]
    normalized_events = {_normalize_event(value) for value in event_values if _text(value)}

    if normalized_events & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    updated_fields = _updated_fields(payload)
    if updated_fields & _STATUS_FIELDS:
        if not normalized_events:
            return True
        return bool(normalized_events & _ISSUE_UPDATE_EVENTS)

    return False


def _new_status(payload: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "statusName",
        "stateName",
        "workflowStateName",
        "workflow_stateName",
        "status",
        "state",
        "workflowState",
        "workflow_state",
    ):
        value = _text(payload.get(key))
        if value:
            return value
    return None


def _updated_fields(payload: Mapping[str, Any]) -> set[str]:
    raw = (
        payload.get("updatedFields")
        or payload.get("updated_fields")
        or payload.get("changedFields")
        or payload.get("changed_fields")
        or payload.get("updatedFrom")
        or payload.get("updated_from")
        or payload.get("changes")
    )
    fields: set[str] = set()

    if isinstance(raw, Mapping):
        fields.update(_normalize_field(key) for key in raw.keys())
    elif isinstance(raw, str):
        fields.update(_normalize_field(part) for part in re.split(r"[, ]+", raw))
    elif isinstance(raw, list | tuple | set):
        for item in raw:
            if isinstance(item, Mapping):
                field = item.get("field") or item.get("name") or item.get("key")
                if field:
                    fields.add(_normalize_field(field))
            else:
                fields.add(_normalize_field(item))

    return {field for field in fields if field}


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _text(payload.get(key))
        if value:
            return value
    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_status(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    text = _split_camel_case(text)
    return re.sub(r"[\s_-]+", " ", text).strip().lower()


def _normalize_event(value: Any) -> str:
    text = _text(value) or ""
    text = _split_camel_case(text).strip().lower()
    compact = re.sub(r"[\s_-]+", "", text)
    spaced = re.sub(r"[\s_-]+", " ", text)
    if compact in _DIRECT_STATUS_CHANGE_EVENTS or compact in _ISSUE_UPDATE_EVENTS:
        return compact
    return spaced


def _normalize_field(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    return re.sub(r"[\s_-]+", "_", _split_camel_case(text)).strip("_").lower()


def _split_camel_case(value: str) -> str:
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", value)


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        return _text(value.get("name"))
    if isinstance(value, int):
        return str(value)
    return None


def main() -> int:
    """Read an event JSON payload from stdin and print an update action."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON input: {exc}") from exc

    result = build_issue_title_update(event)
    if result is not None:
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
