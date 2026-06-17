"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {
    "status",
    "state",
    "stateid",
    "statename",
    "workflowstate",
    "workflowstateid",
    "workflowstatename",
}
STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statechanged",
    "workflowstatechanged",
}
ISSUE_UPDATE_TRIGGERS = {
    "issueupdated",
    "updatedissue",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research.

    The Cursor automation payload is usually flat under ``triggerContext``, while
    Linear webhook payloads can nest issue details under ``data`` or ``issue``.
    This function accepts both shapes and leaves API writes to the caller.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _payload(event)
    if not _is_status_change_event(payload):
        return None

    new_status = _new_status(payload)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _issue_id(payload)
    title = _issue_title(payload)
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        updated_title = title
    else:
        updated_title = f"{RESEARCH_PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": updated_title,
    }


def _payload(event: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}

    for source in _nested_mappings(event, ("issue",), ("data",), ("data", "issue")):
        merged.update(source)

    for source in _nested_mappings(event, ("issue",), ("data",), ("data", "issue")):
        for key in ("state", "status", "workflowState"):
            value = source.get(key)
            if key not in merged and isinstance(value, Mapping):
                merged[key] = value

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        merged.update(trigger_context)

    merged.update(event)
    return merged


def _nested_mappings(
    mapping: Mapping[str, Any],
    *paths: tuple[str, ...],
) -> Iterable[Mapping[str, Any]]:
    for path in paths:
        current: Any = mapping
        for key in path:
            if not isinstance(current, Mapping):
                break
            current = current.get(key)
        else:
            if isinstance(current, Mapping):
                yield current


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        payload.get("trigger"),
        payload.get("action"),
        payload.get("type"),
        payload.get("webhookType"),
        payload.get("eventType"),
    ]

    if any(_normalize_token(value) in STATUS_CHANGE_TRIGGERS for value in trigger_values):
        return True

    if not any(_normalize_token(value) in ISSUE_UPDATE_TRIGGERS for value in trigger_values):
        return False

    return _changed_status_field(payload)


def _changed_status_field(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "changedFields"):
        value = payload.get(key)
        if _contains_status_field(value):
            return True

    for key in ("changes", "updatedFrom", "previousValues"):
        value = payload.get(key)
        if isinstance(value, Mapping) and any(_is_status_field(field) for field in value):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        return any(_is_status_field(key) or _contains_status_field(item) for key, item in value.items())
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    return _normalize_token(value) in STATUS_FIELD_NAMES


def _new_status(payload: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "statusName",
        "stateName",
        "workflowStateName",
    ):
        value = _string_value(payload.get(key))
        if value:
            return value

    for collection_key in ("changes", "changedFields"):
        value = _status_from_change_collection(payload.get(collection_key))
        if value:
            return value

    for key in ("status", "state", "workflowState"):
        value = _string_value(payload.get(key))
        if value:
            return value

    return None


def _status_from_change_collection(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for field, change in value.items():
            if not _is_status_field(field):
                continue
            status = _string_value(change)
            if status:
                return status
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for item in value:
            if isinstance(item, Mapping):
                name = item.get("field") or item.get("name") or item.get("key")
                if _is_status_field(name):
                    status = _string_value(item)
                    if status:
                        return status
            elif _is_status_field(item):
                return None
    return None


def _string_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        for key in ("newValue", "to", "after", "value", "name", "title"):
            status = _string_value(value.get(key))
            if status:
                return status
    return None


def _issue_id(payload: Mapping[str, Any]) -> str | None:
    for key in ("issueId", "issue_id", "identifier", "key", "id"):
        value = _string_value(payload.get(key))
        if value:
            return value
    return None


def _issue_title(payload: Mapping[str, Any]) -> str | None:
    return _string_value(payload.get("title"))


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(RESEARCH_PREFIX.lower())


def _normalize_words(value: Any) -> str | None:
    text = _string_value(value)
    if not text:
        return None
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return re.sub(r"[\W_]+", " ", text).strip().casefold()


def _normalize_token(value: Any) -> str | None:
    words = _normalize_words(value)
    if not words:
        return None
    return words.replace(" ", "")


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
