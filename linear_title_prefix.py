"""Build Linear issue title updates for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    contexts = list(_contexts(event))
    if not _is_status_change(contexts):
        return None

    status = _new_status(contexts)
    if _normalize_phrase(status) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(contexts, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(contexts, ("title",))
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely metadata and issue payloads in precedence order."""
    trigger_context = _mapping(event.get("triggerContext"))
    data = _mapping(event.get("data"))
    top_issue = _mapping(event.get("issue"))
    trigger_issue = _mapping(trigger_context.get("issue")) if trigger_context else None
    data_issue = _mapping(data.get("issue")) if data else None

    for context in (
        trigger_context,
        event,
        data,
        top_issue,
        trigger_issue,
        data_issue,
    ):
        if context:
            yield context


def _mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _is_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type", "eventType"):
            value = context.get(key)
            normalized = _normalize_phrase(value)
            compact = normalized.replace(" ", "")
            if compact in {
                "statuschanged",
                "statuschange",
                "statechanged",
                "statechange",
                "workflowstatechanged",
                "workflowstatechange",
            }:
                return True

            if normalized in {"issue updated", "updated issue", "update", "updated"}:
                return _updated_fields_include_status(contexts)

    return _updated_fields_include_status(contexts) and _new_status(contexts) is not None


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
            "updatedProperties",
            "updatedFrom",
        ):
            if _fields_include_status(context.get(key)):
                return True
    return False


def _fields_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        fields = value.keys()
    elif isinstance(value, str):
        fields = (value,)
    elif isinstance(value, Iterable):
        fields = value
    else:
        return False

    for field in fields:
        normalized = _normalize_phrase(_field_name(field))
        if normalized in {"status", "state", "workflow state"}:
            return True
    return False


def _field_name(field: Any) -> Any:
    if isinstance(field, Mapping):
        return field.get("name") or field.get("field") or field.get("key")
    return field


def _new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "toStatus",
        "to_status",
        "statusName",
        "stateName",
        "workflowStateName",
        "workflow_state_name",
    )
    status_keys = ("status", "state", "workflowState", "workflow_state")

    return _first_status_text(contexts, explicit_keys) or _first_status_text(
        contexts, status_keys
    )


def _first_status_text(
    contexts: list[Mapping[str, Any]], keys: tuple[str, ...]
) -> str | None:
    for context in contexts:
        for key in keys:
            text = _status_text(context.get(key))
            if text:
                return text
    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _clean_text(value.get("name") or value.get("title") or value.get("id"))
    return _clean_text(value)


def _first_text(
    contexts: list[Mapping[str, Any]], keys: tuple[str, ...]
) -> str | None:
    for context in contexts:
        for key in keys:
            text = _clean_text(context.get(key))
            if text:
                return text
    return None


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    text = value.strip()
    return text or None


def _normalize_phrase(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    with_spaces = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    alphanumeric = re.sub(r"[^A-Za-z0-9]+", " ", with_spaces)
    return " ".join(alphanumeric.casefold().split())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
