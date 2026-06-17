"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters To Research."""

    if not isinstance(event, Mapping):
        return None

    for context in _candidate_contexts(event):
        if not _is_status_change_event(context):
            continue

        if _normalize_text(_new_status(context)) != TARGET_STATUS:
            continue

        title = _string_value(context.get("title"))
        issue_id = _issue_id(context)
        if not title or not issue_id:
            return None

        if title.lower().startswith(PREFIX.lower()):
            return None

        return {
            "action": UPDATE_ACTION,
            "issueId": issue_id,
            "title": f"{PREFIX}: {title}",
        }

    return None


def _candidate_contexts(event: Mapping[str, Any]) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = [dict(event)]

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        contexts.append(_merge(event, trigger_context))

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        contexts.append(_merge(event, issue))

    data = event.get("data")
    if isinstance(data, Mapping):
        contexts.append(_merge(event, data))

        data_issue = data.get("issue")
        if isinstance(data_issue, Mapping):
            contexts.append(_merge(event, data, data_issue))

    return contexts


def _merge(*values: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for value in values:
        merged.update(value)
    return merged


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    event_names = [
        context.get("trigger"),
        context.get("webhookType"),
        context.get("action"),
        context.get("type"),
        context.get("eventType"),
    ]

    for value in event_names:
        normalized = _normalize_text(value)
        if not normalized:
            continue
        if _is_direct_status_change_name(normalized):
            return True

    for value in event_names:
        normalized = _normalize_text(value)
        if normalized in {"update", "issue update", "issue updated", "updated issue"}:
            return _has_status_change_metadata(context)

    return False


def _is_direct_status_change_name(normalized: str) -> bool:
    return "change" in normalized and (
        "status" in normalized
        or "state" in normalized
        or "workflow state" in normalized
    )


def _has_status_change_metadata(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "changedFields"):
        fields = context.get(key)
        if _contains_status_field(fields):
            return True

    for key in ("changes", "updatedFrom", "previous", "previousValues"):
        changes = context.get(key)
        if isinstance(changes, Mapping) and any(
            _is_status_field_name(field) for field in changes.keys()
        ):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Mapping):
        field_name = (
            value.get("field")
            or value.get("fieldName")
            or value.get("name")
            or value.get("key")
        )
        if _is_status_field_name(field_name):
            return True
        return any(_contains_status_field(item) for item in value.values())

    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)

    return False


def _is_status_field_name(value: Any) -> bool:
    return _normalize_key(value) in _STATUS_FIELD_NAMES


def _new_status(context: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "statusName",
        "stateName",
    ):
        value = _name_value(context.get(key))
        if value:
            return value

    for key in ("changes", "updatedFields"):
        value = _changed_status_value(context.get(key))
        if value:
            return value

    for key in ("status", "state", "workflowState"):
        value = _name_value(context.get(key))
        if value:
            return value

    return None


def _changed_status_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for field, change in value.items():
            if _is_status_field_name(field):
                return _change_new_value(change)
        return None

    if isinstance(value, list | tuple):
        for item in value:
            if not isinstance(item, Mapping):
                continue
            field = (
                item.get("field")
                or item.get("fieldName")
                or item.get("name")
                or item.get("key")
            )
            if not _is_status_field_name(field):
                continue
            changed_value = _change_new_value(item)
            if changed_value:
                return changed_value

    return None


def _change_new_value(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return _name_value(value)

    for key in ("to", "new", "newValue", "after", "value", "name"):
        changed_value = _name_value(value.get(key))
        if changed_value:
            return changed_value

    return None


def _issue_id(context: Mapping[str, Any]) -> str | None:
    for key in ("issueId", "issue_id", "identifier", "key", "id"):
        value = _string_value(context.get(key))
        if value:
            return value
    return None


def _name_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            named_value = _string_value(value.get(key))
            if named_value:
                return named_value
        return None

    return _string_value(value)


def _string_value(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _normalize_text(value: Any) -> str:
    text = _string_value(value)
    if not text:
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _normalize_key(value: Any) -> str:
    return _normalize_text(value).replace(" ", "")


def main() -> int:
    update = build_issue_title_update(json.load(sys.stdin))
    if update is not None:
        json.dump(update, sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
