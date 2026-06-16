"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}
TRIGGER_FIELDS = ("trigger", "webhookType", "action", "type")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(event, context):
        return None

    status = _first_text(
        context,
        (
            "newStatus",
            "new_status",
            "status",
            "state",
            "workflowState",
            "workflow_state",
        ),
    )
    if _normalize_status(status) != _normalize_status(TARGET_STATUS):
        return None

    issue_id = _issue_identifier(event, context)
    title = _first_text(context, ("title", "name"))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if _has_research_prefix(clean_title):
        new_title = clean_title
    else:
        new_title = f"{PREFIX}: {clean_title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": new_title,
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge likely Linear/Cursor payload locations into one lookup context."""

    context: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if isinstance(value, Mapping):
            context.update(value)

    data = event.get("data")
    issue = data.get("issue") if isinstance(data, Mapping) else None
    trigger_context = event.get("triggerContext")

    merge(issue)
    merge(data)
    merge(trigger_context)
    merge(event)

    return context


def _is_status_change_event(
    event: Mapping[str, Any], context: Mapping[str, Any]
) -> bool:
    trigger_values = [
        value
        for value in _nested_values(event, TRIGGER_FIELDS)
        if isinstance(value, str)
    ]
    trigger_values.extend(
        value for value in _nested_values(context, TRIGGER_FIELDS) if isinstance(value, str)
    )

    normalized_triggers = {_normalize_token(value) for value in trigger_values}
    if any(value in {"statuschanged", "statechanged", "workflowstatechanged"} for value in normalized_triggers):
        return True

    if any(value in {"issueupdated", "updatedissue", "update"} for value in normalized_triggers):
        return _updated_fields_include_status(event) or _updated_fields_include_status(context)

    return False


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    field_containers = (
        "updatedFields",
        "updated_fields",
        "changedFields",
        "changed_fields",
    )
    for key in field_containers:
        fields = payload.get(key)
        if _contains_status_field(fields):
            return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        return any(_is_status_field(field) for field in changes)

    if isinstance(changes, Sequence) and not isinstance(changes, (str, bytes)):
        return any(_change_mentions_status(change) for change in changes)

    return False


def _contains_status_field(fields: Any) -> bool:
    if isinstance(fields, str):
        return _is_status_field(fields)

    if isinstance(fields, Mapping):
        return any(_is_status_field(key) for key in fields)

    if isinstance(fields, Sequence) and not isinstance(fields, (str, bytes)):
        return any(_contains_status_field(field) for field in fields)

    return False


def _change_mentions_status(change: Any) -> bool:
    if isinstance(change, str):
        return _is_status_field(change)

    if isinstance(change, Mapping):
        field_name = _first_text(change, ("field", "fieldName", "name", "key"))
        return bool(field_name and _is_status_field(field_name))

    return False


def _is_status_field(field: Any) -> bool:
    return isinstance(field, str) and _normalize_token(field) in STATUS_FIELDS


def _issue_identifier(event: Mapping[str, Any], context: Mapping[str, Any]) -> str | None:
    data = event.get("data")
    issue = data.get("issue") if isinstance(data, Mapping) else None
    if isinstance(issue, Mapping):
        identifier = _first_text(issue, ("identifier", "issueId", "issue_id", "key"))
        if identifier:
            return identifier

    return _first_text(context, ("issueId", "issue_id", "identifier", "key", "id"))


def _first_text(mapping: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        text = _text_value(value)
        if text is not None and text.strip():
            return text
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if isinstance(value, Mapping):
        return _first_text(value, ("name", "title", "value"))

    return None


def _nested_values(value: Any, keys: Sequence[str]) -> list[Any]:
    values: list[Any] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if key in keys:
                values.append(nested)
            values.extend(_nested_values(nested, keys))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for nested in value:
            values.extend(_nested_values(nested, keys))
    return values


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_status(value: str | None) -> str:
    if not value:
        return ""
    return _normalize_words(value)


def _normalize_token(value: str) -> str:
    return _normalize_words(value).replace(" ", "")


def _normalize_words(value: str) -> str:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    return re.sub(r"[^a-z0-9]+", " ", spaced.casefold()).strip()


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    if action is None:
        return 0

    print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
