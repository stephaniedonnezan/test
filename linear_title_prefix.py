"""Build Linear issue title updates for research status changes.

The helper is dependency-free so webhook automations can run it as a
JSON-in/JSON-out step.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}
STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "status update",
    "status updated",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue enters research."""

    if not isinstance(event, Mapping) or not _is_status_change_event(event):
        return None

    status = _new_status(event)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(event, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(event, ("title", "name"))
    if issue_id is None or title is None or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    for context in _candidate_contexts(event):
        trigger_names = {
            normalized
            for normalized in (
                _normalize(value)
                for value in _direct_values(
                    context,
                    ("trigger", "type", "webhookType", "webhook_type", "action"),
                )
            )
            if normalized is not None
        }
        if trigger_names & STATUS_CHANGE_TRIGGERS:
            return True

        if trigger_names & UPDATE_TRIGGERS and _status_changed(context):
            return True

        if not trigger_names and _status_changed(context):
            return True

    return False


def _new_status(event: Mapping[str, Any]) -> str | None:
    for context in _candidate_contexts(event):
        status = _first_direct_value(
            context,
            (
                "newStatus",
                "new_status",
                "newState",
                "new_state",
                "status",
                "state",
                "workflowState",
                "workflow_state",
            ),
        )
        status_text = _status_text(status)
        if status_text is not None:
            return status_text

        changed_to = _changed_to_status(context)
        if changed_to is not None:
            return changed_to

        issue_state = _get_value(context, ("issue", "state"))
        status_text = _status_text(issue_state)
        if status_text is not None:
            return status_text

        issue_workflow_state = _get_value(context, ("issue", "workflowState"))
        status_text = _status_text(issue_workflow_state)
        if status_text is not None:
            return status_text

    return None


def _changed_to_status(context: Mapping[str, Any]) -> str | None:
    changes = _get_value(context, ("changes",))
    if not isinstance(changes, Mapping):
        return None

    for key, change in changes.items():
        if _normalize_field_name(key) not in STATUS_FIELD_NAMES:
            continue

        if isinstance(change, Mapping):
            changed_to = _first_direct_value(
                change,
                ("newValue", "new_value", "toValue", "to_value", "to", "after"),
            )
            status_text = _status_text(changed_to)
            if status_text is not None:
                return status_text
        else:
            status_text = _status_text(change)
            if status_text is not None:
                return status_text

    return None


def _status_changed(context: Mapping[str, Any]) -> bool:
    changes = _get_value(context, ("changes",))
    if isinstance(changes, Mapping):
        for key in changes:
            if _normalize_field_name(key) in STATUS_FIELD_NAMES:
                return True

    updated_from = _get_value(context, ("updatedFrom",))
    if isinstance(updated_from, Mapping):
        for key in updated_from:
            if _normalize_field_name(key) in STATUS_FIELD_NAMES:
                return True

    for field_list_key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = _get_value(context, (field_list_key,))
        if _contains_status_field(fields):
            return True

    return False


def _contains_status_field(fields: Any) -> bool:
    if isinstance(fields, str):
        return _normalize_field_name(fields) in STATUS_FIELD_NAMES

    if not isinstance(fields, Iterable) or isinstance(fields, Mapping):
        return False

    for field in fields:
        if isinstance(field, Mapping):
            field = _first_direct_value(field, ("field", "name", "key"))
        if _normalize_field_name(field) in STATUS_FIELD_NAMES:
            return True

    return False


def _first_text(event: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for context in _candidate_contexts(event):
        value = _first_direct_value(context, keys)
        text = _coerce_text(value)
        if text is not None:
            return text
    return None


def _candidate_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    seen: set[int] = set()
    for path in (
        ("automation_trigger_info", "triggerContext"),
        ("automation_trigger_info", "trigger_context"),
        ("triggerContext",),
        ("trigger_context",),
        ("data", "issue"),
        ("issue",),
        ("payload", "issue"),
        ("data",),
        ("payload",),
        ("automation_trigger_info",),
        (),
    ):
        value = _get_value(event, path)
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            yield value


def _status_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        value = _first_direct_value(value, ("name", "title", "label"))
    return _coerce_text(value)


def _coerce_text(value: Any) -> str | None:
    if value is None or isinstance(value, (Mapping, list, tuple, set)):
        return None
    text = str(value).strip()
    return text or None


def _get_value(context: Mapping[str, Any], keys: Iterable[str]) -> Any:
    current: Any = context
    for key in keys:
        if not isinstance(current, Mapping) or key not in current:
            return None
        current = current[key]
    return current


def _first_direct_value(context: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in context:
            return context[key]
    return None


def _direct_values(context: Mapping[str, Any], keys: Iterable[str]) -> Iterable[Any]:
    for key in keys:
        if key in context:
            yield context[key]


def _normalize(value: Any) -> str | None:
    text = _coerce_text(value)
    if text is None:
        return None

    camel_spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    words = re.sub(r"[_-]+", " ", camel_spaced).strip().lower()
    return re.sub(r"\s+", " ", words)


def _normalize_field_name(value: Any) -> str | None:
    normalized = _normalize(value)
    if normalized is None:
        return None
    return normalized.replace(" ", "")


def _has_prefix(title: str) -> bool:
    normalized_title = _normalize(title)
    normalized_prefix = _normalize(PREFIX)
    return bool(normalized_title and normalized_prefix and normalized_title.startswith(normalized_prefix))


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
