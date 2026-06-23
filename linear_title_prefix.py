"""Build Linear issue title updates for Cursor research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflow_state",
    "workflow state",
}


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _new_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _issue_id(contexts)
    title = _issue_title(contexts)
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = [event]

    for path in (
        ("triggerContext",),
        ("automation_trigger_info",),
        ("automation_trigger_info", "triggerContext"),
        ("data",),
        ("data", "issue"),
        ("issue",),
    ):
        value = _get_path(event, path)
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    event_names = []
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type", "event", "eventType"):
            event_names.append(_normalize(context.get(key)))

    if any(
        name
        in {
            "status changed",
            "status change",
            "state changed",
            "workflow state changed",
        }
        for name in event_names
    ):
        return True

    is_update = any(
        name in {"update", "updated", "issue updated", "updated issue"}
        for name in event_names
    )
    return is_update and _updated_fields_include_status(contexts)


def _updated_fields_include_status(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _fields_include_status(context.get(key)):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            if any(_is_status_field(key) for key in changes.keys()):
                return True
        elif isinstance(changes, Iterable) and not isinstance(changes, (str, bytes)):
            for change in changes:
                if isinstance(change, Mapping) and any(
                    _is_status_field(change.get(key))
                    for key in ("field", "name", "key", "property")
                ):
                    return True

    return False


def _fields_include_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value.keys())

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_is_status_field(item) for item in value)

    return False


def _new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    contexts = list(contexts)
    for context in contexts:
        for key in (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "newWorkflowState",
            "new_workflow_state",
            "statusName",
            "status_name",
        ):
            value = _text(context.get(key))
            if value:
                return value

        value = _status_from_changes(context.get("changes"))
        if value:
            return value

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = _text(context.get(key))
            if value:
                return value

    return None


def _status_from_changes(changes: Any) -> str | None:
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _is_status_field(key):
                return _change_new_value(value)
        return None

    if isinstance(changes, Iterable) and not isinstance(changes, (str, bytes)):
        for change in changes:
            if not isinstance(change, Mapping):
                continue
            field = next(
                (
                    change.get(key)
                    for key in ("field", "name", "key", "property")
                    if change.get(key) is not None
                ),
                None,
            )
            if _is_status_field(field):
                return _change_new_value(change)

    return None


def _change_new_value(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("newValue", "new_value", "to", "after", "value", "name"):
            value = _text(change.get(key))
            if value:
                return value
    return _text(change)


def _issue_id(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in ("issueId", "issue_id", "identifier", "key", "id"):
            value = _text(context.get(key))
            if value:
                return value
    return None


def _issue_title(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in ("title", "issueTitle", "issue_title", "name"):
            value = _text(context.get(key))
            if value:
                return value
    return None


def _has_research_prefix(title: str) -> bool:
    return _normalize(title).startswith(TITLE_PREFIX.lower())


def _is_status_field(value: Any) -> bool:
    normalized = _normalize(value)
    return normalized.replace(" ", "") in {
        field.replace(" ", "").replace("_", "") for field in _STATUS_FIELD_NAMES
    }


def _text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _text(value.get(key))
            if text:
                return text
        return None

    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _normalize(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def _get_path(mapping: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = mapping
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
