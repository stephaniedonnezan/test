"""Build Linear issue title updates for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "state id",
    "status id",
    "workflow state",
    "workflow state id",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return the Linear title update action for matching status-change events.

    The automation trigger may provide a flat `triggerContext`, while Linear
    webhooks commonly nest issue data under `data` or `issue`. This function
    accepts those shapes and returns None for events that should not be changed.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_changed_event(contexts):
        return None

    new_status = _new_status(contexts)
    if _normalize_phrase(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_string(_issue_contexts(event), ("id", "issueId", "issue_id", "identifier"))
    title = _first_string(_issue_contexts(event), ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload dictionaries from outermost trigger data to issue data."""

    contexts: list[Mapping[str, Any]] = [event]
    _append_mapping(contexts, event.get("triggerContext"))
    data = event.get("data")
    _append_mapping(contexts, data)
    _append_mapping(contexts, event.get("issue"))
    if isinstance(data, Mapping):
        _append_mapping(contexts, data.get("issue"))
    return contexts


def _issue_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload dictionaries from most issue-specific to most general."""

    contexts: list[Mapping[str, Any]] = []
    data = event.get("data")
    if isinstance(data, Mapping):
        _append_mapping(contexts, data.get("issue"))
    _append_mapping(contexts, event.get("issue"))
    _append_mapping(contexts, data)
    _append_mapping(contexts, event.get("triggerContext"))
    _append_mapping(contexts, event)
    return contexts


def _append_mapping(contexts: list[Mapping[str, Any]], value: Any) -> None:
    if isinstance(value, Mapping) and value not in contexts:
        contexts.append(value)


def _is_status_changed_event(contexts: Sequence[Mapping[str, Any]]) -> bool:
    trigger_values = list(_trigger_values(contexts))
    if any(_is_status_changed_value(value) for value in trigger_values):
        return True

    if any(_is_update_value(value) for value in trigger_values):
        return _updated_fields_include_status(contexts)

    return False


def _trigger_values(contexts: Sequence[Mapping[str, Any]]) -> Iterable[Any]:
    keys = ("trigger", "webhookType", "eventType", "action", "type", "kind")
    for context in contexts:
        for key in keys:
            if key in context:
                yield context[key]


def _is_status_changed_value(value: Any) -> bool:
    normalized = _normalize_phrase(value)
    return "status" in normalized and ("changed" in normalized or "change" in normalized)


def _is_update_value(value: Any) -> bool:
    normalized = _normalize_phrase(value)
    return normalized in {"update", "updated", "issue updated", "updated issue"} or (
        "issue" in normalized and "updated" in normalized
    )


def _updated_fields_include_status(contexts: Sequence[Mapping[str, Any]]) -> bool:
    field_keys = ("updatedFields", "updated_fields", "changedFields", "changed_fields", "updatedFrom")
    for context in contexts:
        for key in field_keys:
            if key in context and any(_is_status_field(field) for field in _field_names(context[key])):
                return True
    return False


def _field_names(value: Any) -> Iterable[Any]:
    if isinstance(value, Mapping):
        yield from value.keys()
    elif isinstance(value, str):
        yield value
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        yield from value


def _is_status_field(value: Any) -> bool:
    return _normalize_phrase(value) in _STATUS_FIELD_NAMES


def _new_status(contexts: Sequence[Mapping[str, Any]]) -> Any:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
    )
    status_keys = ("status", "state", "workflowState", "workflow_state")

    for keys in (explicit_keys, status_keys):
        value = _first_value(contexts, keys)
        if value is not None:
            return _string_or_name(value)
    return None


def _first_value(contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> Any:
    for context in contexts:
        for key in keys:
            if key in context:
                return context[key]
    return None


def _first_string(contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    value = _first_value(contexts, keys)
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _string_or_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _first_value([value], ("name", "title", "label"))
    return value


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_phrase(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    update = build_issue_title_update(json.load(sys.stdin))
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
