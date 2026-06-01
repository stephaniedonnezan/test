"""Build Linear issue title updates for issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}
_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_ISSUE_UPDATE_TRIGGERS = {
    "issue updated",
    "updated issue",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research.

    Cursor automation payloads put the issue details in ``triggerContext``.
    Linear webhooks usually put them under ``data`` or ``data.issue``. This
    accepts those shapes and returns a small serializable action for the caller
    that applies updates to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_new_status(event)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_issue_title(event)
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    contexts = list(_iter_contexts(event))
    trigger_values: list[Any] = []
    for context in contexts:
        for key in (
            "trigger",
            "triggerType",
            "webhookTrigger",
            "event",
            "eventType",
            "action",
            "type",
        ):
            trigger_values.append(context.get(key))

    normalized_triggers = {_normalize(value) for value in trigger_values}
    if normalized_triggers & _STATUS_CHANGE_TRIGGERS:
        return True

    if normalized_triggers & _ISSUE_UPDATE_TRIGGERS:
        return _updated_fields_include_status(contexts)

    return False


def _updated_fields_include_status(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
        ):
            fields = context.get(key)
            if _field_collection_includes_status(fields):
                return True

        for key in ("updatedFrom", "updated_from", "previousValues", "previous_values"):
            fields = context.get(key)
            if isinstance(fields, Mapping) and _field_collection_includes_status(fields.keys()):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping) and _field_collection_includes_status(changes.keys()):
            return True

    return False


def _field_collection_includes_status(fields: Any) -> bool:
    if isinstance(fields, str):
        return _field_name_is_status(fields)

    if isinstance(fields, Mapping):
        fields = fields.keys()

    if not isinstance(fields, Iterable):
        return False

    return any(_field_name_is_status(field) for field in fields)


def _field_name_is_status(field: Any) -> bool:
    normalized = _normalize(field).replace(" ", "")
    return normalized in _STATUS_FIELD_NAMES


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    status_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "statusName",
        "status_name",
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    for context in _iter_contexts(event):
        status = _string_or_name(_first_value(context, status_keys))
        if status:
            return status

    for context in _iter_contexts(event):
        status = _string_or_name(_first_value(context, fallback_keys))
        if status:
            return status

    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for context in _iter_issue_contexts(event):
        value = _first_value(context, ("id", "issueId", "issue_id", "identifier"))
        if isinstance(value, str) and value.strip():
            return value
    return None


def _extract_issue_title(event: Mapping[str, Any]) -> str | None:
    for context in _iter_issue_contexts(event):
        value = _first_value(context, ("title", "issueTitle", "issue_title", "name"))
        if isinstance(value, str) and value.strip():
            return value
    return None


def _iter_issue_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield issue-shaped contexts before broader webhook metadata."""

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            yield issue

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue

    yield from _iter_contexts(event)


def _iter_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield trigger_context

    yield event

    data = event.get("data")
    if isinstance(data, Mapping):
        yield data
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            yield issue

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue


def _first_value(context: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in context:
            return context[key]
    return None


def _string_or_name(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, Mapping):
        name = value.get("name")
        if isinstance(name, str) and name.strip():
            return name
    return None


def _has_title_prefix(title: str) -> bool:
    return title.lstrip().casefold().startswith(TITLE_PREFIX.casefold())


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(build_issue_title_update(payload), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
