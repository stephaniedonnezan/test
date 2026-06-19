"""Build Linear issue title updates for research status changes.

The automation platform is responsible for applying the returned action to
Linear. This module keeps the webhook parsing and title decision deterministic
and easy to test.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


CURSOR_RESEARCHING_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
    "workflowstatus",
    "workflowstatusid",
}
STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "statuschanged",
    "state changed",
    "state change",
    "statechanged",
    "workflow state changed",
    "workflow state change",
    "workflowstatechanged",
}
ISSUE_UPDATE_TRIGGERS = {
    "issue updated",
    "updated issue",
    "issue update",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue moves to research.

    The function accepts both Cursor's flat ``triggerContext`` shape and nested
    Linear webhook payloads. It returns ``None`` when the payload does not
    represent a status change to ``to research`` or when the title is already
    prefixed.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_status(new_status) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(contexts, ("id", "issueId", "issue_id", "identifier", "key"))
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{CURSOR_RESEARCHING_PREFIX}: {title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely payload contexts, ordered from most to least specific."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event.get("triggerContext"))
    data = event.get("data")
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("node"))
    issue = event.get("issue")
    add(issue)
    node = event.get("node")
    add(node)
    add(event)

    return contexts


def _is_status_change_event(contexts: Sequence[Mapping[str, Any]]) -> bool:
    trigger_values = _event_type_values(contexts)
    normalized_triggers = {_normalize_event_type(value) for value in trigger_values}

    if normalized_triggers & STATUS_CHANGE_TRIGGERS:
        return True

    if normalized_triggers & ISSUE_UPDATE_TRIGGERS:
        return _updated_status_fields(contexts)

    return False


def _event_type_values(contexts: Sequence[Mapping[str, Any]]) -> list[Any]:
    values: list[Any] = []
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            value = context.get(key)
            if value is not None:
                values.append(value)
    return values


def _updated_status_fields(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        if _contains_status_field(context.get("updatedFields")):
            return True
        if _contains_status_field(context.get("changedFields")):
            return True
        if _contains_status_field(context.get("changes")):
            return True
        if _contains_status_field(context.get("updatedFrom")):
            return True
        if _contains_status_field(context.get("updatedTo")):
            return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(_normalize_field_name(key) in STATUS_FIELD_NAMES for key in value)

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_status_field(item) for item in value)

    return False


def _extract_new_status(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    for key in ("newStatus", "new_status", "toStatus", "to_status", "statusName", "stateName"):
        value = _first_value(contexts, (key,))
        status = _text_or_nested_name(value)
        if status:
            return status

    status = _status_from_change_maps(contexts)
    if status:
        return status

    for key in ("status", "state", "workflowState", "workflowStatus"):
        value = _first_value(contexts, (key,))
        status = _text_or_nested_name(value)
        if status:
            return status

    return None


def _status_from_change_maps(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in ("changes", "updatedTo"):
            value = context.get(key)
            if not isinstance(value, Mapping):
                continue

            for field_name, change in value.items():
                if _normalize_field_name(field_name) not in STATUS_FIELD_NAMES:
                    continue

                if isinstance(change, Mapping):
                    for new_value_key in ("to", "toValue", "new", "newValue", "after", "name"):
                        status = _text_or_nested_name(change.get(new_value_key))
                        if status:
                            return status
                else:
                    status = _text_or_nested_name(change)
                    if status:
                        return status

    return None


def _first_text(contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    value = _first_value(contexts, keys)
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _first_value(contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> Any:
    for context in contexts:
        for key in keys:
            if key in context and context[key] is not None:
                return context[key]
    return None


def _text_or_nested_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()

    return None


def _has_research_prefix(title: str) -> bool:
    return title.strip().lower().startswith(CURSOR_RESEARCHING_PREFIX.lower())


def _normalize_status(value: str | None) -> str | None:
    if not value:
        return None
    return _words(value)


def _normalize_event_type(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _words(value)


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]", "", _split_camel_case(value).lower())


def _words(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", _split_camel_case(value).lower())).strip()


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    """Read a JSON event from stdin and print the title update action."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2

    result = build_issue_title_update(event)
    if result is not None:
        print(json.dumps(result, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
