"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statusupdated",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}
GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action for issues moved to To Research."""
    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not contexts:
        return None

    if not _is_status_change(contexts):
        return None

    if _normalize_status(_first_text(contexts, _status_values)) != TARGET_STATUS:
        return None

    title = _first_text(contexts, _title_values)
    issue_id = _first_text(contexts, _issue_id_values)
    if not title or not issue_id:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely metadata/issue dictionaries from outermost to innermost."""
    contexts: list[Mapping[str, Any]] = [event]
    for path in (
        ("automation_trigger_info", "triggerContext"),
        ("triggerContext",),
        ("data",),
        ("data", "issue"),
        ("issue",),
    ):
        value = _get_path(event, path)
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)
    return contexts


def _is_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    normalized_triggers = {
        _normalize_token(value)
        for context in contexts
        for key in ("trigger", "webhookType", "action", "type")
        if (value := context.get(key)) is not None
    }

    if normalized_triggers & STATUS_CHANGE_TRIGGERS:
        return True

    if normalized_triggers & GENERIC_UPDATE_TRIGGERS:
        return _updated_status_field(contexts)

    return False


def _updated_status_field(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = context.get(key)
            if _contains_status_field(fields):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping) and any(
            _normalize_field_name(key) in STATUS_FIELDS for key in changes
        ):
            return True

    return False


def _contains_status_field(fields: Any) -> bool:
    if isinstance(fields, str):
        return _normalize_field_name(fields) in STATUS_FIELDS
    if isinstance(fields, Mapping):
        return any(_normalize_field_name(key) in STATUS_FIELDS for key in fields)
    if isinstance(fields, list | tuple | set):
        return any(_contains_status_field(field) for field in fields)
    return False


def _status_values(context: Mapping[str, Any]) -> list[Any]:
    values = [
        context.get("newStatus"),
        context.get("new_status"),
        context.get("status"),
        context.get("state"),
        context.get("workflowState"),
        context.get("workflow_state"),
    ]

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for field in ("status", "state", "workflowState", "workflow_state"):
            change = changes.get(field)
            if isinstance(change, Mapping):
                values.extend([change.get("newValue"), change.get("to"), change.get("after")])

    return values


def _title_values(context: Mapping[str, Any]) -> list[Any]:
    return [context.get("title"), context.get("name")]


def _issue_id_values(context: Mapping[str, Any]) -> list[Any]:
    return [
        context.get("issueId"),
        context.get("issue_id"),
        context.get("id"),
        context.get("identifier"),
        context.get("key"),
    ]


def _first_text(
    contexts: list[Mapping[str, Any]],
    collector: Any,
) -> str | None:
    for context in contexts:
        for value in collector(context):
            text = _text(value)
            if text:
                return text
    return None


def _text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "id", "identifier", "key"):
            text = _text(value.get(key))
            if text:
                return text
        return None
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"[\s_-]+", " ", _split_camel_case(value)).strip().lower()


def _normalize_token(value: Any) -> str:
    text = _text(value) or ""
    return re.sub(r"[^a-z0-9]+", "", _split_camel_case(text).lower())


def _normalize_field_name(value: Any) -> str:
    text = _text(value) or ""
    return re.sub(r"[^a-z0-9]+", "", _split_camel_case(text).lower())


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def _get_path(root: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = root
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def main() -> int:
    """Read a JSON event from stdin and print the requested title update."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print(f"Invalid JSON payload: {error}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
