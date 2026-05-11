"""Build Linear issue title updates for issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
TITLE_UPDATE_ACTION = "update_issue_title"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "state updated",
    "workflow state changed",
    "workflow state change",
    "workflow state updated",
}
_ISSUE_UPDATE_EVENTS = {
    "issue updated",
    "updated issue",
    "update",
    "updated",
}
_STATUS_FIELD_NAMES = {
    "status",
    "status id",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
    "workflow status",
    "workflow status id",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research.

    Cursor automation trigger payloads usually place issue fields inside
    ``triggerContext``. Linear webhook payloads may instead place issue details
    under ``data`` or ``issue``. This function accepts those common shapes and
    returns ``None`` for unrelated or malformed events.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _event_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    if _normalize_label(_status_name(contexts)) != _normalize_label(TARGET_STATUS):
        return None

    issue_id = _first_text(contexts, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(contexts, ("title", "name"))
    if issue_id is None or title is None:
        return None

    clean_title = title.strip()
    if not clean_title or _has_title_prefix(clean_title):
        return None

    return {
        "action": TITLE_UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility alias for automation entrypoints named after the event."""

    return build_issue_title_update(event)


def _event_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely issue/status containers from most-specific to broadest."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and not any(value is existing for existing in contexts):
            contexts.append(value)

    def add_container(container: Any) -> None:
        if not isinstance(container, Mapping):
            return

        data = _get(container, "data")
        issue = _get(container, "issue")
        if isinstance(data, Mapping):
            add(_get(data, "issue"))
            add(data)
        add(issue)
        add(container)

    for key in ("triggerContext", "trigger_context", "context", "payload"):
        add_container(_get(event, key))

    add_container(_get(event, "data"))
    add_container(_get(event, "issue"))
    add(event)
    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    normalized_triggers = {
        _normalize_label(value)
        for context in contexts
        for key in ("trigger", "webhookType", "webhook_type", "action", "type", "eventType", "event_type")
        if (value := _get(context, key)) is not None
    }

    if normalized_triggers & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    return bool(normalized_triggers & _ISSUE_UPDATE_EVENTS) and _updated_fields_include_status(contexts)


def _updated_fields_include_status(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = _get(context, key)
            if _fields_include_status(fields):
                return True

        changes = _get(context, "changes")
        if isinstance(changes, Mapping) and _fields_include_status(changes):
            return True

    return False


def _fields_include_status(fields: Any) -> bool:
    if isinstance(fields, str):
        return _normalize_label(fields) in _STATUS_FIELD_NAMES
    if isinstance(fields, Mapping):
        return any(_normalize_label(field) in _STATUS_FIELD_NAMES for field in fields)
    if isinstance(fields, Iterable) and not isinstance(fields, (str, bytes, Mapping)):
        return any(_field_indicates_status(field) for field in fields)
    return False


def _field_indicates_status(field: Any) -> bool:
    if isinstance(field, Mapping):
        field = _first_text((field,), ("field", "name", "key", "id"))
    return isinstance(field, str) and _normalize_label(field) in _STATUS_FIELD_NAMES


def _status_name(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    explicit_status = _first_status_text(
        contexts,
        (
            "newStatus",
            "new_status",
            "newStatusName",
            "new_status_name",
            "newState",
            "new_state",
            "newWorkflowState",
            "new_workflow_state",
        ),
    )
    if explicit_status is not None:
        return explicit_status

    return _first_status_text(
        contexts,
        (
            "status",
            "statusName",
            "status_name",
            "state",
            "stateName",
            "state_name",
            "workflowState",
            "workflow_state",
            "workflowStateName",
            "workflow_state_name",
        ),
    )


def _first_status_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _get(context, key)
            if isinstance(value, Mapping):
                value = _first_text((value,), ("name", "title", "label"))
            if isinstance(value, str) and value.strip():
                return value
    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _get(context, key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _get(mapping: Mapping[str, Any], key: str) -> Any:
    if key in mapping:
        return mapping[key]

    normalized_key = _normalize_key(key)
    for existing_key, value in mapping.items():
        if isinstance(existing_key, str) and _normalize_key(existing_key) == normalized_key:
            return value
    return None


def _has_title_prefix(title: str) -> bool:
    normalized_title = _normalize_label(title)
    normalized_prefix = _normalize_label(TITLE_PREFIX)
    return normalized_title == normalized_prefix or normalized_title.startswith(f"{normalized_prefix} ")


def _normalize_label(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _normalize_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", value).lower()


def main() -> int:
    """Read a JSON event from stdin and print the title-update action, if any."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print(f"Invalid JSON payload: {error}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
