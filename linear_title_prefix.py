"""Build Linear issue title updates for Cursor research automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
UPDATE_ACTION = "update_issue_title"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_status"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action when an issue enters research."""

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)

    if not _is_status_change_event(payload):
        return None

    status = _new_status(payload)
    if _normalize_value(status) != "to research":
        return None

    title = _first_text(payload, ("title", "name"))
    issue_id = _first_text(payload, ("id", "issueId", "issue_id", "identifier"))
    if not title or not issue_id:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge the common Linear and automation wrapper objects into one mapping."""

    payload: dict[str, Any] = {}

    for key in ("issue", "data", "triggerContext"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            payload.update(_flatten_payload(nested))

    payload.update(event)
    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_words = [
        _normalize_value(value)
        for key in ("trigger", "webhookType", "action", "type")
        if (value := payload.get(key)) is not None
    ]

    if any(word in {"status changed", "status change", "statuschanged"} for word in event_words):
        return True

    if any(word in {"issue updated", "updated issue", "update", "updated"} for word in event_words):
        return _updated_status_field(payload)

    return False


def _updated_status_field(payload: Mapping[str, Any]) -> bool:
    updated_fields = (
        payload.get("updatedFields")
        or payload.get("updated_fields")
        or payload.get("changedFields")
        or payload.get("changed_fields")
    )
    if isinstance(updated_fields, str):
        fields = [updated_fields]
    elif isinstance(updated_fields, list | tuple | set):
        fields = list(updated_fields)
    else:
        return False

    return any(_normalize_field_name(field) in STATUS_FIELD_NAMES for field in fields)


def _new_status(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "status"):
        value = payload.get(key)
        if text := _text_or_nested_name(value):
            return text

    for key in ("state", "workflowState", "workflow_status"):
        value = payload.get(key)
        if text := _text_or_nested_name(value):
            return text

    return None


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _text_or_nested_name(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, Mapping):
        nested = value.get("name") or value.get("title")
        if isinstance(nested, str) and nested.strip():
            return nested
    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_value(value: Any) -> str:
    text = str(value)
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-\s]+", " ", text)
    return text.strip().casefold()


def _normalize_field_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9_]", "", str(value).strip().casefold())


def main() -> int:
    """Read a JSON event from stdin and print the resulting action, if any."""

    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
