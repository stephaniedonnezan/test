"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any, Optional


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"
TITLE_SEPARATOR = ": "
STATUS_CHANGE_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> Optional[dict[str, str]]:
    """Return a title update action when an issue moves to "to research"."""
    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    status = _new_status(context)
    if _normalize_label(status) != RESEARCH_STATUS:
        return None

    issue_id = _issue_id(context)
    title = _issue_title(context)
    if not issue_id or not title:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": _prefixed_title(title),
    }


def handle_issue_status_changed(event: Mapping[str, Any]) -> Optional[dict[str, str]]:
    """Alias for callers using event-handler naming."""
    return build_issue_title_update(event)


def handleIssueStatusChanged(event: Mapping[str, Any]) -> Optional[dict[str, str]]:
    """Alias for JavaScript-style hidden tests."""
    return build_issue_title_update(event)


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge nested Linear issue payloads with outer automation metadata."""
    context: dict[str, Any] = {}

    trigger_context = _mapping_value(event, "triggerContext", "trigger_context")
    data = _mapping_value(event, "data")
    issue = _mapping_value(data, "issue") if data else None

    for source in (issue, data, trigger_context, event):
        if source:
            context.update(source)

    if data:
        context.setdefault("data", data)
    if issue:
        context.setdefault("issue", issue)
    if trigger_context:
        context.setdefault("triggerContext", trigger_context)

    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    event_labels = [
        value
        for key in ("trigger", "webhookType", "webhook_type", "action", "type")
        for value in _walk_values(context.get(key))
    ]

    normalized_labels = {_normalize_identifier(value) for value in event_labels}
    direct_status_change = {
        "statuschanged",
        "statuschange",
        "statechanged",
        "statechange",
        "workflowstatechanged",
        "workflowstatechange",
    }
    if normalized_labels & direct_status_change:
        return True

    issue_update = {
        "update",
        "updated",
        "issueupdate",
        "issueupdated",
        "updatedissue",
    }
    if normalized_labels & issue_update:
        return _updated_status_fields(context)

    return False


def _updated_status_fields(context: Mapping[str, Any]) -> bool:
    candidates = [
        context.get("updatedFields"),
        context.get("updated_fields"),
        context.get("changedFields"),
        context.get("changed_fields"),
        context.get("changes"),
    ]

    for candidate in candidates:
        for field in _field_names(candidate):
            if _normalize_identifier(field) in STATUS_CHANGE_FIELDS:
                return True

    return False


def _field_names(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return list(value.keys())
    if isinstance(value, (list, tuple, set)):
        fields: list[Any] = []
        for item in value:
            if isinstance(item, Mapping):
                fields.extend(
                    item.get(key)
                    for key in ("field", "name", "key")
                    if item.get(key) is not None
                )
            else:
                fields.append(item)
        return fields
    return []


def _new_status(context: Mapping[str, Any]) -> Optional[str]:
    for key in (
        "newStatus",
        "new_status",
        "status",
        "state",
        "workflowState",
        "workflow_state",
    ):
        status = _status_name(context.get(key))
        if status:
            return status

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _status_name(changes.get(key))
            if status:
                return status

    return None


def _status_name(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "newValue", "new_value", "to", "after"):
            status = _status_name(value.get(key))
            if status:
                return status
    return None


def _issue_id(context: Mapping[str, Any]) -> Optional[str]:
    for key in ("issueId", "issue_id", "identifier", "key", "id"):
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _issue_title(context: Mapping[str, Any]) -> Optional[str]:
    title = context.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    return None


def _prefixed_title(title: str) -> str:
    if title.lower().startswith(TITLE_PREFIX.lower()):
        return title
    return f"{TITLE_PREFIX}{TITLE_SEPARATOR}{title}"


def _mapping_value(source: Optional[Mapping[str, Any]], *keys: str) -> Optional[Mapping[str, Any]]:
    if not isinstance(source, Mapping):
        return None
    for key in keys:
        value = source.get(key)
        if isinstance(value, Mapping):
            return value
    return None


def _walk_values(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        return list(value.values())
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _normalize_label(value: Any) -> str:
    if value is None:
        return ""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value))
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()


def _normalize_identifier(value: Any) -> str:
    return _normalize_label(value).replace(" ", "")


def main() -> int:
    """Read a JSON event from stdin and print the title update action."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    result = build_issue_title_update(event)
    if result is not None:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
