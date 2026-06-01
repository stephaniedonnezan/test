"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


RESEARCH_STATUS = "toresearch"
TITLE_PREFIX = "Cursor researching"
TITLE_PREFIX_WITH_SEPARATOR = f"{TITLE_PREFIX}: "
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any] | Any) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    payload = _payload(event)
    if not _is_status_change_event(payload):
        return None

    status = _new_status(payload)
    if _normalize(status) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(payload, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if not stripped_title or _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX_WITH_SEPARATOR}{stripped_title}",
    }


def _payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common automation and Linear webhook wrappers into one payload."""

    payload: dict[str, Any] = {}

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        payload.update(_flatten_issue_data(trigger_context))

    payload.update(_flatten_issue_data(event))
    return payload


def _flatten_issue_data(data: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    for wrapper_key in ("data", "issue"):
        wrapped = data.get(wrapper_key)
        if isinstance(wrapped, Mapping):
            payload.update(_flatten_issue_data(wrapped))

    for key, value in data.items():
        if key not in {"data", "issue"}:
            payload[key] = value

    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_names = [
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    ]

    if any(_normalize(name) in {"statuschanged", "statuschange", "statusupdated"} for name in event_names):
        return True

    if any(_normalize(name) in {"issueupdated", "updatedissue", "update"} for name in event_names):
        return _updated_status_field(payload.get("updatedFields") or payload.get("updated_fields"))

    return False


def _updated_status_field(fields: Any) -> bool:
    if isinstance(fields, str):
        return _normalize(fields) in STATUS_FIELD_NAMES

    if isinstance(fields, Mapping):
        return any(_normalize(field) in STATUS_FIELD_NAMES for field in fields)

    if isinstance(fields, list | tuple | set):
        return any(_normalize(field) in STATUS_FIELD_NAMES for field in fields)

    return False


def _new_status(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "status"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            name = _first_text(value, ("name", "title"))
            if name:
                return name
        elif isinstance(value, str):
            return value

    for key in ("state", "workflowState", "workflow_state"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            name = _first_text(value, ("name", "title"))
            if name:
                return name
        elif isinstance(value, str):
            return value

    return None


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            stripped_value = value.strip()
            if stripped_value:
                return stripped_value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", "", separated.lower())


def main() -> int:
    update = build_issue_title_update(json.load(sys.stdin))
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
