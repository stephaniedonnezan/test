"""Build title update actions for Linear issues entering research status."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    status = _extract_new_status(context)
    if _normalize_value(status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(context)
    title = _extract_title(context)
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common automation and Linear webhook shapes into one lookup dict."""

    context: dict[str, Any] = {}

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        _merge_mapping(context, trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        _merge_mapping(context, data)
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            _merge_mapping(context, issue)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        _merge_mapping(context, issue)

    # Top-level automation metadata should take precedence over nested issue fields.
    _merge_mapping(context, event)
    return context


def _merge_mapping(target: dict[str, Any], source: Mapping[str, Any]) -> None:
    for key, value in source.items():
        if key not in {"triggerContext", "data", "issue"}:
            target[key] = value


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    event_names = (
        context.get("trigger"),
        context.get("webhookType"),
        context.get("action"),
        context.get("type"),
    )

    if any(_normalize_value(name) in {"status changed", "status change"} for name in event_names):
        return True

    if any(_normalize_value(name) in {"update", "updated", "issue updated", "updated issue"} for name in event_names):
        return _updated_fields_include_status(context)

    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields") or context.get("updated_fields")
    if isinstance(updated_fields, str):
        fields = [updated_fields]
    elif isinstance(updated_fields, list | tuple | set):
        fields = list(updated_fields)
    else:
        fields = []

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        fields.extend(str(key) for key in changes.keys())

    return any(_normalize_field_name(field) in STATUS_FIELDS for field in fields)


def _extract_new_status(context: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "status_name"):
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = _change_new_value(changes.get(key))
            if value:
                return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = context.get(key)
        extracted = _status_value(value)
        if extracted:
            return extracted

    return None


def _change_new_value(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("newValue", "new_value", "to", "after"):
            value = _status_value(change.get(key))
            if value:
                return value
    return _status_value(change)


def _status_value(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()
    return None


def _extract_issue_id(context: Mapping[str, Any]) -> str | None:
    for key in ("issueId", "issue_id", "identifier", "key", "id"):
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_title(context: Mapping[str, Any]) -> str | None:
    value = context.get("title")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _normalize_value(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    normalized = re.sub(r"[_\-\s]+", " ", separated).strip().lower()
    return normalized


def _normalize_field_name(value: Any) -> str:
    return re.sub(r"[_\-\s]+", "", str(value)).lower()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is None:
        return 0

    print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
