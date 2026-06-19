"""Build Linear issue title updates for Cursor research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
TITLE_SEPARATOR = ": "
STATUS_FIELDS = frozenset({"status", "state", "workflowstate", "workflow state"})


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action when an issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    status = _new_status(context)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(context, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(context, ("title", "name"))
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        updated_title = title
    else:
        updated_title = f"{PREFIX}{TITLE_SEPARATOR}{title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": updated_title,
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor and Linear payload layers into a flat lookup context."""

    context: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if isinstance(value, Mapping):
            context.update(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")
    data_issue = data.get("issue") if isinstance(data, Mapping) else None
    payload_issue = event.get("payload", {}).get("issue") if isinstance(event.get("payload"), Mapping) else None

    for layer in (payload_issue, data_issue, issue, data, trigger_context, event):
        merge(layer)

    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    event_types = [
        _normalize_text(context.get(key))
        for key in ("trigger", "webhookType", "action", "type")
        if context.get(key) is not None
    ]

    if any(event_type in {"status changed", "status change", "statuschanged"} for event_type in event_types):
        return True

    if any(event_type in {"update", "updated", "issue updated", "updated issue"} for event_type in event_types):
        return _updated_status_field(context)

    return False


def _updated_status_field(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields"):
        if _contains_status_field(context.get(key)):
            return True

    for key in ("changes", "changedFields", "changed_fields"):
        value = context.get(key)
        if isinstance(value, Mapping) and any(_is_status_field(field) for field in value):
            return True
        if _contains_status_field(value):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        return any(_is_status_field(field) for field in value)
    if isinstance(value, Sequence):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    normalized = _normalize_text(value)
    compact = normalized.replace(" ", "")
    return normalized in STATUS_FIELDS or compact in STATUS_FIELDS


def _new_status(context: Mapping[str, Any]) -> str | None:
    explicit_status = _first_text(
        context,
        (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "statusName",
            "status_name",
            "stateName",
            "state_name",
            "workflowStateName",
            "workflow_state_name",
        ),
    )
    if explicit_status:
        return explicit_status

    for key in ("status", "state", "workflowState", "workflow_state"):
        status = _text_or_name(context.get(key))
        if status:
            return status

    changes_status = _status_from_changes(context.get("changes"))
    if changes_status:
        return changes_status

    return None


def _status_from_changes(changes: Any) -> str | None:
    if not isinstance(changes, Mapping):
        return None

    for field in ("status", "state", "workflowState", "workflow_state"):
        if field not in changes:
            continue

        change = changes[field]
        if isinstance(change, Mapping):
            for key in ("to", "new", "after", "newValue", "new_value", "value", "name"):
                status = _text_or_name(change.get(key))
                if status:
                    return status
        else:
            status = _text_or_name(change)
            if status:
                return status

    return None


def _first_text(context: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        value = context.get(key)
        text = _text_or_name(value)
        if text:
            return text
    return None


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        return _first_text(value, ("name", "title", "id", "identifier", "key"))
    return None


def _has_prefix(title: str) -> bool:
    return title.lstrip().lower().startswith(PREFIX.lower())


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    """Read a JSON event from stdin and print the title update action, if any."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
