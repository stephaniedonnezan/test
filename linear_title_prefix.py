"""Build Linear title updates for issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELDS = ("newStatus", "new_status", "status", "state", "workflowState")
_ISSUE_ID_FIELDS = ("issueId", "issue_id", "id", "identifier", "key")
_TITLE_FIELDS = ("title", "name")
_ISSUE_FIELDS = _STATUS_FIELDS + _ISSUE_ID_FIELDS + _TITLE_FIELDS


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title update action for matching research transitions."""
    if not isinstance(event, Mapping):
        return None

    context = _trigger_context(event)
    issue = _issue_context(event)

    if not _is_status_change(context):
        return None

    status = _new_status(context, issue)
    if _normalize(status) != TARGET_STATUS:
        return None

    title = _first_text(issue, _TITLE_FIELDS)
    issue_id = _first_text(issue, _ISSUE_ID_FIELDS)
    if not title or not issue_id:
        return None

    clean_title = title.strip()
    if not clean_title or _has_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _trigger_context(event: Mapping[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = {}

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        context.update(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        context.update({key: value for key, value in data.items() if key != "issue"})

    context.update(event)
    return context


def _issue_context(event: Mapping[str, Any]) -> dict[str, Any]:
    issue: dict[str, Any] = {}

    _copy_issue_fields(issue, event)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        _copy_issue_fields(issue, trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        _copy_issue_fields(issue, data)

        nested_issue = data.get("issue")
        if isinstance(nested_issue, Mapping):
            if _first_text(nested_issue, _ISSUE_ID_FIELDS):
                _clear_issue_id_fields(issue)
            _copy_issue_fields(issue, nested_issue)

    return issue


def _copy_issue_fields(target: dict[str, Any], source: Mapping[str, Any]) -> None:
    for field in _ISSUE_FIELDS:
        if field in source:
            target[field] = source[field]


def _clear_issue_id_fields(target: dict[str, Any]) -> None:
    for field in _ISSUE_ID_FIELDS:
        target.pop(field, None)


def _is_status_change(context: Mapping[str, Any]) -> bool:
    event_names = [
        value
        for key in ("trigger", "webhookType", "action", "type")
        if isinstance(value := context.get(key), str)
    ]
    normalized_names = {_normalize(name) for name in event_names}

    if normalized_names & {"status changed", "status change", "status updated"}:
        return True

    if normalized_names & {"update", "updated", "issue update", "issue updated", "updated issue"}:
        return _updated_fields_include_status(context)

    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    field_values = []
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        value = context.get(key)
        if isinstance(value, str):
            field_values.append(value)
        elif isinstance(value, Iterable):
            field_values.extend(item for item in value if isinstance(item, str))

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        field_values.extend(key for key in changes if isinstance(key, str))

    return any(_normalize(field) in {"status", "state", "workflow state"} for field in field_values)


def _new_status(context: Mapping[str, Any], issue: Mapping[str, Any]) -> str | None:
    for source in (context, issue):
        for field in _STATUS_FIELDS:
            value = source.get(field)
            text = _text_value(value)
            if text:
                return text

    return None


def _first_text(source: Mapping[str, Any], fields: Iterable[str]) -> str | None:
    for field in fields:
        text = _text_value(source.get(field))
        if text:
            return text
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "id", "identifier", "key"):
            nested = value.get(key)
            if isinstance(nested, str):
                return nested
    return None


def _normalize(value: str | None) -> str:
    if not value:
        return ""

    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", separated).strip().lower()
    return re.sub(r"\s+", " ", words)


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


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
