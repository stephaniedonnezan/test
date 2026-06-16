"""Build title update actions for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflow status",
    "statusid",
    "stateid",
    "workflowstateid",
}
_STATUS_CHANGE_EVENT_NAMES = {
    "status changed",
    "status change",
    "issue status changed",
    "state changed",
    "workflow state changed",
}
_UPDATE_EVENT_NAMES = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters research."""
    if not isinstance(event, Mapping):
        return None

    contexts = list(_contexts(event))
    if not _is_status_change(contexts):
        return None

    if _normalize(_new_status(contexts)) != TARGET_STATUS:
        return None

    title = _first_text(contexts, ("title", "name", "summary"))
    issue_id = _first_text(
        contexts,
        ("issueId", "issue_id", "id", "identifier", "key"),
    )
    if not title or not issue_id:
        return None

    title = title.strip()
    if not title or title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield useful payload objects in preference order."""
    yield event

    for key in ("triggerContext", "trigger_context", "context", "payload"):
        value = event.get(key)
        if isinstance(value, Mapping):
            yield value

    for key in ("data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            yield value
            issue = value.get("issue")
            if isinstance(issue, Mapping):
                yield issue

    data = event.get("data")
    if isinstance(data, Mapping):
        for key in ("state", "status", "workflowState"):
            value = data.get(key)
            if isinstance(value, Mapping):
                yield value


def _is_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    event_names = (
        _normalize(context.get(key))
        for context in contexts
        for key in ("trigger", "webhookType", "webhook_type", "action", "type")
    )
    if any(name in _STATUS_CHANGE_EVENT_NAMES for name in event_names):
        return True

    if any(
        _normalize(context.get(key)) in _UPDATE_EVENT_NAMES
        for context in contexts
        for key in ("trigger", "webhookType", "webhook_type", "action", "type")
    ):
        return _has_status_change_marker(contexts)

    return _has_status_change_marker(contexts)


def _has_status_change_marker(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(context.get(key)):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping) and _contains_status_field(changes.keys()):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, Mapping):
        values = value.keys()
    elif isinstance(value, Iterable):
        values = value
    else:
        return False

    return any(_normalize_field_name(item) in _STATUS_FIELD_NAMES for item in values)


def _new_status(contexts: list[Mapping[str, Any]]) -> Any:
    for context in contexts:
        value = _first_existing(
            context,
            (
                "newStatus",
                "new_status",
                "newState",
                "new_state",
                "newWorkflowState",
                "new_workflow_state",
            ),
        )
        if value is not None:
            return _status_text(value)

    for context in contexts:
        changes = context.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for key, value in changes.items():
            if _normalize_field_name(key) in _STATUS_FIELD_NAMES:
                changed_to = _changed_to(value)
                if changed_to is not None:
                    return _status_text(changed_to)

    for context in contexts:
        value = _first_existing(context, ("status", "state", "workflowState", "workflow_state"))
        if value is not None:
            return _status_text(value)

    return None


def _changed_to(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value

    for key in (
        "to",
        "after",
        "new",
        "newValue",
        "new_value",
        "toStatus",
        "to_status",
        "toState",
        "to_state",
    ):
        if key in value:
            return value[key]
    return value


def _status_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        nested = _first_existing(value, ("name", "title", "status", "state", "workflowState"))
        if nested is not None and nested is not value:
            return _status_text(nested)
        return None
    if value is None:
        return None
    return str(value).strip()


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        value = _first_existing(context, keys)
        if value is None:
            continue
        if isinstance(value, Mapping):
            value = _first_existing(value, ("name", "title", "id", "identifier", "key"))
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _first_existing(context: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in context:
            return context[key]
    return None


def _normalize(value: Any) -> str:
    text = "" if value is None else str(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _normalize_field_name(value: Any) -> str:
    text = "" if value is None else str(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1\2", text)
    return re.sub(r"[^A-Za-z0-9]+", "", text).lower()


def main() -> int:
    event = json.load(sys.stdin)
    json.dump(build_issue_title_update(event), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
