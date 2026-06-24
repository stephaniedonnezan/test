"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate"}
_DIRECT_STATUS_CHANGE_NAMES = {
    "statuschanged",
    "statuschange",
    "statusupdated",
    "statusupdate",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}
_GENERIC_UPDATE_NAMES = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    contexts = list(_candidate_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    status = _new_status(contexts)
    if _normalize_words(status) != _normalize_words(TARGET_STATUS):
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(contexts, ("title", "issueTitle", "issue_title", "name"))
    if not issue_id or not title:
        return None

    cleaned_title = title.strip()
    if _has_prefix(cleaned_title):
        return None

    return {
        "action": ACTION,
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {cleaned_title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely places where Cursor or Linear payloads store issue data."""
    seen: set[int] = set()

    def emit(value: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            yield value

    yield from emit(event.get("triggerContext"))

    automation_info = event.get("automation_trigger_info")
    if isinstance(automation_info, Mapping):
        yield from emit(automation_info.get("triggerContext"))

    yield from emit(event)
    yield from emit(event.get("issue"))

    data = event.get("data")
    yield from emit(data)
    if isinstance(data, Mapping):
        yield from emit(data.get("issue"))

    payload = event.get("payload")
    yield from emit(payload)
    if isinstance(payload, Mapping):
        yield from emit(payload.get("issue"))
        yield from emit(payload.get("data"))


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    contexts = list(contexts)
    event_names = {
        _normalize_token(str(value))
        for context in contexts
        for key in ("trigger", "webhookType", "event", "eventType", "type", "action")
        if (value := context.get(key)) is not None
    }

    if event_names & _DIRECT_STATUS_CHANGE_NAMES:
        return True

    if event_names & _GENERIC_UPDATE_NAMES:
        return _updated_fields_include_status(contexts)

    return _updated_fields_include_status(contexts)


def _updated_fields_include_status(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _field_collection_includes_status(context.get(key)):
                return True

        for key in ("changes", "changed", "updatedFrom", "updated_from"):
            value = context.get(key)
            if isinstance(value, Mapping) and any(_is_status_field(field) for field in value):
                return True

    return False


def _new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    contexts = list(contexts)
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "toStatus",
        "to_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    status_keys = ("status", "state", "workflowState", "workflow_state")

    for context in contexts:
        status = _first_text((context,), explicit_keys)
        if status:
            return status

    for context in contexts:
        for key in ("changes", "changed"):
            status = _status_from_change_mapping(context.get(key))
            if status:
                return status

    for context in contexts:
        status = _first_text((context,), status_keys)
        if status:
            return status

    return None


def _status_from_change_mapping(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for field, change in value.items():
        if not _is_status_field(field):
            continue
        if isinstance(change, Mapping):
            status = _first_text(
                (change,),
                ("newValue", "new_value", "to", "after", "name", "value"),
            )
            if status:
                return status
        status = _text_value(change)
        if status:
            return status

    return None


def _field_collection_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
        return any(_is_status_field(field) for field in value)
    return False


def _is_status_field(value: Any) -> bool:
    return _normalize_token(str(value)) in _STATUS_FIELD_NAMES


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            text = _text_value(value)
            if text:
                return text
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        return _first_text((value,), ("name", "title", "displayName", "value"))
    return None


def _has_prefix(title: str) -> bool:
    return title.lstrip().lower().startswith(PREFIX.lower())


def _normalize_words(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"[^a-z0-9]+", " ", _split_camel_case(value).lower()).strip()


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _split_camel_case(value).lower())


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
