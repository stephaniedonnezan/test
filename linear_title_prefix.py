"""Build Linear issue title updates for research status changes.

The automation environment calls into this module with the webhook payload it
received from Linear/Cursor.  `build_issue_title_update` returns a small action
object that the surrounding runner can apply, or ``None`` when no title change
is needed.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELDS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "toStatus",
    "to_status",
    "toState",
    "to_state",
    "status",
    "state",
    "workflowState",
)
_EXPLICIT_NEW_STATUS_FIELDS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "toStatus",
    "to_status",
    "toState",
    "to_state",
)
_ISSUE_ID_FIELDS = ("issueId", "issue_id", "id", "identifier")
_TITLE_FIELDS = ("title", "issueTitle", "issue_title", "name")
_TRIGGER_FIELDS = ("trigger", "action", "event", "type", "webhookType", "webhook_type")
_STATUS_CHANGE_FIELD_NAMES = {
    "status",
    "statusId",
    "statusName",
    "state",
    "stateId",
    "stateName",
    "workflowState",
    "workflowStateId",
    "workflowStateName",
    "workflow_state",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters To Research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    if _normalized_status(_first_status_value(contexts)) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, _ISSUE_ID_FIELDS)
    title = _first_text(contexts, _TITLE_FIELDS)
    if not issue_id or not title:
        return None

    if title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely metadata/issue objects in priority order."""

    contexts: list[Mapping[str, Any]] = []

    trigger_context = _mapping_value(event, "triggerContext")
    if trigger_context:
        contexts.append(trigger_context)

    contexts.append(event)

    issue = _mapping_value(event, "issue")
    if issue:
        contexts.append(issue)

    data = _mapping_value(event, "data")
    if data:
        data_issue = _mapping_value(data, "issue")
        if data_issue:
            contexts.append(data_issue)
        contexts.append(data)

    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    saw_issue_update = False
    status_field_updated = False

    for context in contexts:
        for field in _TRIGGER_FIELDS:
            value = _text_value(context.get(field))
            if not value:
                continue
            normalized = _normalize(value)
            if normalized in {"status changed", "status change", "status updated"}:
                return True
            if "status" in normalized and ("change" in normalized or "update" in normalized):
                return True
            if normalized in {"issue updated", "updated issue", "update"}:
                saw_issue_update = True

        if _contains_status_field(context.get("updatedFields")):
            status_field_updated = True
        if _contains_status_field(context.get("updated_fields")):
            status_field_updated = True
        if _contains_status_field(context.get("updatedFrom")):
            status_field_updated = True
        if _contains_status_field(context.get("updated_from")):
            status_field_updated = True

    return saw_issue_update and status_field_updated


def _first_status_value(contexts: list[Mapping[str, Any]]) -> Any:
    for field in _EXPLICIT_NEW_STATUS_FIELDS:
        for context in contexts:
            if field in context:
                return context[field]

    for field in _STATUS_FIELDS:
        for context in contexts:
            if field in context:
                return context[field]

    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], fields: Iterable[str]) -> str | None:
    for context in contexts:
        for field in fields:
            value = _text_value(context.get(field))
            if value:
                return value
    return None


def _normalized_status(value: Any) -> str | None:
    text = _text_value(value)
    if not text:
        return None
    return _normalize(text)


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None

    if isinstance(value, Mapping):
        for field in ("name", "title", "status", "state"):
            text = _text_value(value.get(field))
            if text:
                return text

    return None


def _mapping_value(mapping: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else None


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _field_name_is_status(value)

    if isinstance(value, Mapping):
        return any(_field_name_is_status(str(key)) for key in value)

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _field_name_is_status(value: str) -> bool:
    normalized = _normalize(value).replace(" ", "")
    return normalized in {name.lower().replace("_", "") for name in _STATUS_CHANGE_FIELD_NAMES}


def _normalize(value: str) -> str:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", words)


def main() -> int:
    payload = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(payload), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
