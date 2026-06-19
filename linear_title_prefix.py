"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELDS = {
    "status",
    "state",
    "workflow_state",
    "workflow_status",
    "workflowstate",
    "workflowstatus",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change(event, payload):
        return None

    status = _extract_new_status(payload)
    if _normalize_text(status) != _normalize_text(RESEARCH_STATUS):
        return None

    issue_id = _first_text(payload, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{RESEARCH_PREFIX}: {title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for section in (
        event,
        event.get("triggerContext"),
        event.get("data"),
        event.get("data", {}).get("issue") if isinstance(event.get("data"), Mapping) else None,
        event.get("issue"),
    ):
        if isinstance(section, Mapping):
            payload.update(section)
    return payload


def _is_status_change(event: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
    event_names = [
        value
        for source in (event, event.get("triggerContext"), event.get("data"), payload)
        if isinstance(source, Mapping)
        for key in ("trigger", "webhookType", "action", "type")
        if (value := source.get(key)) is not None
    ]

    if any(_is_direct_status_change_name(value) for value in event_names):
        return True

    if not any(_is_issue_update_name(value) for value in event_names):
        return False

    updated_fields = _updated_field_names(event, payload)
    return bool(updated_fields & STATUS_FIELDS)


def _is_direct_status_change_name(value: Any) -> bool:
    normalized = _normalize_text(value)
    return normalized in {
        "status changed",
        "status change",
        "state changed",
        "workflow state changed",
        "workflow status changed",
    }


def _is_issue_update_name(value: Any) -> bool:
    normalized = _normalize_text(value)
    return normalized in {"update", "updated", "issue update", "issue updated", "updated issue"}


def _updated_field_names(*sources: Mapping[str, Any]) -> set[str]:
    names: set[str] = set()
    for source in sources:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            names.update(_field_names(source.get(key)))

        changes = source.get("changes") or source.get("changed")
        if isinstance(changes, Mapping):
            names.update(_normalize_field_name(name) for name in changes)
        elif isinstance(changes, Iterable) and not isinstance(changes, (str, bytes)):
            names.update(_field_names(changes))
    return {name for name in names if name}


def _field_names(value: Any) -> set[str]:
    if isinstance(value, str):
        return {_normalize_field_name(value)}

    if isinstance(value, Mapping):
        return {_normalize_field_name(name) for name in value}

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        names: set[str] = set()
        for item in value:
            if isinstance(item, Mapping):
                names.update(
                    _normalize_field_name(item.get(key))
                    for key in ("field", "fieldName", "name", "key")
                    if item.get(key) is not None
                )
            else:
                names.add(_normalize_field_name(item))
        return names

    return set()


def _extract_new_status(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "status_name"):
        value = _text_or_name(payload.get(key))
        if value:
            return value

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflowStatus"):
            changed_value = changes.get(key)
            if isinstance(changed_value, Mapping):
                value = _text_or_name(
                    changed_value.get("to")
                    or changed_value.get("new")
                    or changed_value.get("newValue")
                    or changed_value.get("after")
                )
            else:
                value = _text_or_name(changed_value)
            if value:
                return value

    for key in ("status", "state", "workflowState", "workflowStatus"):
        value = _text_or_name(payload.get(key))
        if value:
            return value

    return None


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _first_text(value, ("name", "title", "label", "value"))
    if isinstance(value, str):
        return value
    return None


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(RESEARCH_PREFIX.casefold())


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return re.sub(r"[^a-z0-9_]+", "_", value.casefold()).strip("_")


def main() -> int:
    """Read a JSON webhook payload from stdin and print the resulting action."""
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
