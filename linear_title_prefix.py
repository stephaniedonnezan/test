"""Build Linear issue title update actions for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
UPDATE_ACTION = "update_issue_title"
RESEARCH_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_status"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to the research status."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change_event(event, payload):
        return None

    if _normalize_status(_status_value(payload)) != RESEARCH_STATUS:
        return None

    issue_id = _string_value(payload, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _string_value(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge useful nested payload sections while keeping outer trigger metadata."""
    payload: dict[str, Any] = {}

    trigger_context = _mapping_value(event.get("triggerContext"))
    data = _mapping_value(event.get("data"))
    issue = _mapping_value(data.get("issue")) if data else {}

    for section in (issue, data, trigger_context, event):
        payload.update(section)

    state = _mapping_value(payload.get("state"))
    if state and "status" not in payload and "name" in state:
        payload["status"] = state["name"]

    workflow_state = _mapping_value(payload.get("workflowState"))
    if workflow_state and "status" not in payload and "name" in workflow_state:
        payload["status"] = workflow_state["name"]

    return payload


def _is_status_change_event(event: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
    trigger_values = list(_trigger_values(event)) + list(_trigger_values(payload))
    if any(_is_direct_status_change(value) for value in trigger_values):
        return True

    if any(_is_issue_update(value) for value in trigger_values):
        return _updated_status_fields(payload)

    return False


def _trigger_values(source: Mapping[str, Any]) -> Iterable[Any]:
    for key in ("trigger", "webhookType", "action", "type", "eventType"):
        value = source.get(key)
        if isinstance(value, Mapping) and "name" in value:
            yield value["name"]
        elif value is not None:
            yield value


def _is_direct_status_change(value: Any) -> bool:
    normalized = _normalize_key(value)
    return normalized in {
        "statuschanged",
        "statuschange",
        "statechanged",
        "workflowstatechanged",
    }


def _is_issue_update(value: Any) -> bool:
    normalized = _normalize_key(value)
    return normalized in {
        "update",
        "updated",
        "issueupdated",
        "updatedissue",
        "issueupdate",
    }


def _updated_status_fields(payload: Mapping[str, Any]) -> bool:
    fields = payload.get("updatedFields")
    if fields is None:
        fields = payload.get("updated_fields")

    if _contains_status_field(fields):
        return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_key(field) in STATUS_FIELD_NAMES for field in changes)

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_key(value) in STATUS_FIELD_NAMES

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
        return any(_contains_status_field(item) for item in value)

    if isinstance(value, Mapping):
        return any(_normalize_key(key) in STATUS_FIELD_NAMES for key in value)

    return False


def _status_value(payload: Mapping[str, Any]) -> Any:
    for key in ("newStatus", "new_status", "toStatus", "to_status", "status"):
        if key in payload:
            return _name_or_value(payload[key])

    for key in ("state", "workflowState"):
        value = _mapping_value(payload.get(key))
        if value:
            if "name" in value:
                return value["name"]
            if "status" in value:
                return value["status"]

    changes = _mapping_value(payload.get("changes"))
    if changes:
        for field_name, change in changes.items():
            if _normalize_key(field_name) in STATUS_FIELD_NAMES:
                return _change_new_value(change)

    return None


def _change_new_value(change: Any) -> Any:
    if isinstance(change, Mapping):
        for key in ("newValue", "new_value", "to", "after", "name"):
            if key in change:
                return _name_or_value(change[key])
    return _name_or_value(change)


def _name_or_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "value"):
            if key in value:
                return value[key]
    return value


def _string_value(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _mapping_value(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _normalize_status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    words = re.sub(r"([a-z])([A-Z])", r"\1 \2", value.strip())
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", words).casefold()
    return " ".join(normalized.split())


def _normalize_key(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    words = re.sub(r"([a-z])([A-Z])", r"\1 \2", value.strip())
    return re.sub(r"[^a-zA-Z0-9]+", "", words).casefold()


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print(f"Invalid JSON: {error}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout, indent=2)
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
