"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "workflow state changed",
}
ISSUE_UPDATE_TRIGGERS = {
    "issue updated",
    "updated issue",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _first_value(contexts, ("newStatus", "new_status", "statusName", "status_name"))
    if status is None:
        status = _status_from_changes(contexts)
    if status is None:
        status = _first_status_value(contexts)

    if _normalize_text(status) != _normalize_text(TARGET_STATUS):
        return None

    issue_id = _clean_text(_first_value(contexts, ("issueId", "issue_id", "id", "identifier", "key")))
    title = _clean_text(_first_value(contexts, ("title",)))
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        prefixed_title = title
    else:
        prefixed_title = f"{TITLE_PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": prefixed_title,
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    for value in _walk_mappings(event):
        contexts.append(value)

    # Prefer outer automation metadata over nested issue data when keys overlap.
    return contexts


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested in value.values():
            yield from _walk_mappings(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_mappings(item)


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    trigger_values: list[str] = []

    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            value = context.get(key)
            if isinstance(value, str):
                trigger_values.append(_normalize_text(value))

    if any(value in STATUS_CHANGE_TRIGGERS for value in trigger_values):
        return True

    if any(value in ISSUE_UPDATE_TRIGGERS for value in trigger_values):
        return _updated_status_field(contexts)

    return False


def _updated_status_field(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields"):
            if _contains_status_field(context.get(key)):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping) and any(_is_status_field(key) for key in changes):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Iterable) and not isinstance(value, (bytes, Mapping)):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    return _normalize_key(value) in STATUS_FIELDS


def _status_from_changes(contexts: Iterable[Mapping[str, Any]]) -> Any:
    for context in contexts:
        changes = context.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for key, change in changes.items():
            if not _is_status_field(key):
                continue

            if isinstance(change, Mapping):
                for value_key in ("newValue", "new_value", "to", "after", "name"):
                    value = change.get(value_key)
                    if value is not None:
                        return _status_name(value)
            elif change is not None:
                return change

    return None


def _first_status_value(contexts: Iterable[Mapping[str, Any]]) -> Any:
    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = context.get(key)
            if isinstance(value, Mapping):
                nested = _status_name(value)
                if nested is not None:
                    return nested
            elif value is not None:
                return value
    return None


def _status_name(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value

    for key in ("name", "title"):
        nested = value.get(key)
        if nested is not None:
            return nested
    return None


def _first_value(contexts: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> Any:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if value is not None:
                return value
    return None


def _normalize_text(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return ""

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().casefold()


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _normalize_text(value))


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def main() -> int:
    """Read a JSON payload from stdin and print the title update, if any."""

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
