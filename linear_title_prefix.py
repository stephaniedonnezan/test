"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TITLE_SEPARATOR = ": "
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "state id",
    "stateid",
    "workflow state",
    "workflowstate",
    "workflow state id",
    "workflowstateid",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    mappings = _collect_mappings(event)
    if not _is_status_change_event(mappings):
        return None

    status = _first_status_value(mappings)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_issue_id(mappings)
    title = _first_text(mappings, ("title", "name"))
    if issue_id is None or title is None:
        return None

    issue_id = issue_id.strip()
    title = title.strip()
    if not issue_id or not title or _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}{TITLE_SEPARATOR}{title}",
    }


def _collect_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect common Linear and automation payload layers in precedence order."""
    mappings: list[Mapping[str, Any]] = [event]
    seen: set[int] = set()

    def add_mapping(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        identity = id(value)
        if identity in seen:
            return
        seen.add(identity)
        mappings.append(value)

    seen.add(id(event))
    for key in ("triggerContext", "trigger_context", "webhook", "data", "issue"):
        add_mapping(event.get(key))

    index = 0
    while index < len(mappings):
        mapping = mappings[index]
        for key in (
            "triggerContext",
            "trigger_context",
            "webhook",
            "data",
            "issue",
            "node",
            "object",
            "state",
            "status",
            "workflowState",
            "workflow_state",
        ):
            add_mapping(mapping.get(key))
        index += 1

    return mappings


def _is_status_change_event(mappings: Iterable[Mapping[str, Any]]) -> bool:
    normalized_events: list[str] = []
    has_status_field_update = False

    for mapping in mappings:
        for key in ("trigger", "event", "eventType", "event_type", "webhookType", "webhook_type", "type", "action"):
            value = mapping.get(key)
            if isinstance(value, str):
                normalized_events.append(_normalize(value) or "")

        if _updated_fields_include_status(mapping.get("updatedFields")):
            has_status_field_update = True
        if _updated_fields_include_status(mapping.get("updated_fields")):
            has_status_field_update = True
        if _updated_fields_include_status(mapping.get("updatedFrom")):
            has_status_field_update = True
        if _updated_fields_include_status(mapping.get("updated_from")):
            has_status_field_update = True

    if any(
        value in {"status changed", "status change", "state changed", "workflow state changed"}
        or "status changed" in value
        or "state changed" in value
        for value in normalized_events
    ):
        return True

    return has_status_field_update and any(
        value in {"update", "updated", "issue updated", "updated issue"} for value in normalized_events
    )


def _updated_fields_include_status(updated_fields: Any) -> bool:
    if isinstance(updated_fields, str):
        fields: Iterable[Any] = (updated_fields,)
    elif isinstance(updated_fields, Mapping):
        fields = updated_fields.keys()
    elif isinstance(updated_fields, Iterable) and not isinstance(updated_fields, bytes):
        fields = updated_fields
    else:
        return False

    for field in fields:
        if isinstance(field, Mapping):
            field = field.get("name") or field.get("field") or field.get("key")
        if _normalize(field) in _STATUS_FIELD_NAMES:
            return True
    return False


def _first_status_value(mappings: Iterable[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "toStatus",
        "to_status",
        "toState",
        "to_state",
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    return _first_text(mappings, explicit_keys) or _first_text(mappings, fallback_keys)


def _first_issue_id(mappings: Iterable[Mapping[str, Any]]) -> str | None:
    mappings = list(mappings)
    id_keys = ("id", "issueId", "issue_id", "identifier")

    for mapping in mappings:
        if _first_text((mapping,), ("title",)):
            issue_id = _first_text((mapping,), id_keys)
            if issue_id is not None:
                return issue_id

    return _first_text(mappings, id_keys)


def _first_text(mappings: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for mapping in mappings:
        for key in keys:
            if key not in mapping:
                continue
            value = _text_value(mapping[key])
            if value is not None and value.strip():
                return value
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return _first_text((value,), ("name", "title", "label", "id"))
    return None


def _has_title_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize(value: Any) -> str | None:
    text = _text_value(value)
    if text is None:
        return None

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def main() -> int:
    """Read a JSON event from stdin and print the title update action, if any."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
