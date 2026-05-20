"""Build Linear issue-title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_UPDATE_FIELDS = {"status", "state", "workflowstate", "workflow state"}
_STATUS_TRIGGER_VALUES = {
    "status change",
    "status changed",
    "status update",
    "state change",
    "state changed",
    "workflow state change",
    "workflow state changed",
}
_ISSUE_UPDATE_VALUES = {"update", "updated", "issue update", "issue updated", "updated issue"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters To Research.

    The handler accepts the flat Cursor automation payload shape as well as
    nested Linear issue webhook payloads. It returns None when the event is not
    a status change to the target status or when the title already has the
    prefix.
    """

    if not isinstance(event, Mapping):
        return None

    trigger_context = _mapping_value(event, "triggerContext")
    data = _mapping_value(event, "data")
    issue = _first_mapping(
        _mapping_value(data, "issue"),
        _mapping_value(event, "issue"),
        _mapping_value(trigger_context, "issue"),
    )

    contexts = [context for context in (trigger_context, event, data, issue) if context]

    if not _is_status_change_event(contexts):
        return None

    status = _extract_new_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(contexts, ("issueId", "issue_id", "id", "identifier"))
    title = _extract_first_text(contexts, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    has_issue_update = False

    for context in contexts:
        for key in ("trigger", "webhookType", "event", "type", "action"):
            value = _normalize(context.get(key))
            if value in _STATUS_TRIGGER_VALUES:
                return True
            if value in _ISSUE_UPDATE_VALUES:
                has_issue_update = True

    return has_issue_update and any(_mentions_status_field(context) for context in contexts)


def _mentions_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        updated_fields = value.get("updatedFields")
        if _status_field_in(updated_fields):
            return True

        updated_from = value.get("updatedFrom")
        if isinstance(updated_from, Mapping) and any(
            _normalize(key) in _STATUS_UPDATE_FIELDS for key in updated_from
        ):
            return True

        return any(_mentions_status_field(child) for child in value.values())

    if isinstance(value, list):
        return any(_mentions_status_field(item) for item in value)

    return False


def _status_field_in(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize(value) in _STATUS_UPDATE_FIELDS
    if isinstance(value, Iterable):
        return any(_status_field_in(item) for item in value)
    return False


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "statusName",
        "stateName",
        "workflowStateName",
    )
    fallback_keys = ("status", "state", "workflowState")

    for keys in (explicit_keys, fallback_keys):
        for context in contexts:
            value = _extract_value(context, keys)
            if value:
                return value

    return None


def _extract_value(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        if key not in context:
            continue
        value = context[key]
        if isinstance(value, Mapping):
            named = _extract_first_text((value,), ("name", "title"))
            if named:
                return named
        elif value is not None:
            text = str(value).strip()
            if text:
                return text
    return None


def _extract_first_text(contexts: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
    return None


def _first_mapping(*values: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    return next((value for value in values if value), None)


def _mapping_value(context: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if not isinstance(context, Mapping):
        return None
    value = context.get(key)
    return value if isinstance(value, Mapping) else None


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def main() -> int:
    """Read an event JSON document from stdin and print the update action."""

    update = build_issue_title_update(json.load(sys.stdin))
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
