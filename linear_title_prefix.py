"""Build Linear issue title updates for Cursor research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_MARKERS = {
    "statuschange",
    "statuschanged",
    "statechange",
    "statechanged",
    "workflowstatechange",
    "workflowstatechanged",
}
_UPDATE_MARKERS = {
    "issueupdate",
    "issueupdated",
    "updatedissue",
    "update",
    "updated",
}
_EVENT_MARKER_KEYS = (
    "trigger",
    "triggerType",
    "webhookType",
    "action",
    "type",
    "event",
    "eventType",
)
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflow_state",
    "workflowStatus",
    "workflow_status",
    "statusId",
    "stateId",
}
_STATUS_VALUE_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflow_state",
    "workflowStatus",
    "workflow_status",
}
_CHANGE_CONTAINER_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
    "changes",
    "updatedFrom",
    "updated_from",
)
_EXPLICIT_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "targetStatus",
    "target_status",
)
_CURRENT_STATUS_KEYS = (
    "status",
    "state",
    "workflowState",
    "workflow_state",
    "statusName",
    "stateName",
    "workflowStateName",
    "workflow_state_name",
)


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research.

    The Cursor automation trigger can provide a flat ``triggerContext`` payload,
    while native Linear webhooks commonly nest issue data under ``data`` or
    ``issue``. This function accepts both shapes and returns a serializable
    action for the automation runner, or ``None`` when no title update is needed.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_candidate_contexts(event))
    if not _is_status_change_event(contexts, event):
        return None

    new_status = _find_new_status(contexts)
    if _normalize_label(new_status) != _normalize_label(TARGET_STATUS):
        return None

    issue_id = _find_first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _find_first_text(contexts, ("title", "issueTitle", "issue_title", "name"))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if _normalize_prefix(clean_title).startswith(_normalize_prefix(PREFIX)):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely issue/trigger dictionaries with more specific data first."""

    trigger_context = _mapping_at(event, "triggerContext")
    if trigger_context:
        yield trigger_context

    data = _mapping_at(event, "data")
    data_issue = _mapping_at(data, "issue") if data else None
    if data_issue:
        yield data_issue

    issue = _mapping_at(event, "issue")
    if issue:
        yield issue

    if data:
        yield data

    yield event


def _is_status_change_event(contexts: list[Mapping[str, Any]], event: Mapping[str, Any]) -> bool:
    markers = {
        _normalize_marker(value)
        for context in contexts
        for key in _EVENT_MARKER_KEYS
        for value in _values_for_key(context, key)
    }
    markers.discard("")

    if markers & _DIRECT_STATUS_CHANGE_MARKERS:
        return True

    if markers & _UPDATE_MARKERS:
        return _has_status_field_change(event)

    return False


def _has_status_field_change(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in _CHANGE_CONTAINER_KEYS and _change_container_mentions_status(item):
                return True
            if isinstance(item, (Mapping, list, tuple)) and _has_status_field_change(item):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_has_status_field_change(item) for item in value)

    return False


def _change_container_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Mapping):
        for key, item in value.items():
            if _is_status_field_name(key):
                return True
            if _is_status_field_name(_text_from_value(item)):
                return True
            if isinstance(item, (Mapping, list, tuple)) and _change_container_mentions_status(item):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_change_container_mentions_status(item) for item in value)

    return False


def _find_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in _EXPLICIT_NEW_STATUS_KEYS:
            text = _find_text_for_key(context, key)
            if text:
                return text

    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields", "changes"):
            for value in _values_for_key(context, key):
                status = _new_status_from_change_container(value)
                if status:
                    return status

    for context in contexts:
        for key in _CURRENT_STATUS_KEYS:
            text = _find_text_for_key(context, key)
            if text:
                return text

    return None


def _new_status_from_change_container(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _is_status_field_name(key):
                text = _new_value_text(item)
                if text and _can_use_as_status_value(key, text):
                    return text
            if isinstance(item, (Mapping, list, tuple)):
                text = _new_status_from_change_container(item)
                if text:
                    return text

    if isinstance(value, (list, tuple)):
        for item in value:
            if isinstance(item, Mapping):
                field_name = _find_text_for_key(item, "name") or _find_text_for_key(item, "field")
                if _is_status_field_name(field_name):
                    text = _new_value_text(item)
                    if text and _can_use_as_status_value(field_name, text):
                        return text
            text = _new_status_from_change_container(item)
            if text:
                return text

    return None


def _new_value_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None

    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "new", "to", "after", "current"):
            text = _find_text_for_key(value, key)
            if text:
                return text
        for key in ("name", "label"):
            text = _find_text_for_key(value, key)
            if text:
                return text

    return _text_from_value(value)


def _find_first_text(contexts: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        for context in contexts:
            text = _find_text_for_key(context, key)
            if text:
                return text
    return None


def _find_text_for_key(context: Mapping[str, Any], key: str) -> str | None:
    for value in _values_for_key(context, key):
        text = _text_from_value(value)
        if text:
            return text
    return None


def _values_for_key(context: Mapping[str, Any], key: str) -> Iterable[Any]:
    if key in context:
        yield context[key]


def _text_from_value(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, str):
        text = value.strip()
        return text or None

    if isinstance(value, Mapping):
        for key in ("name", "label", "title"):
            text = _find_text_for_key(value, key)
            if text:
                return text
        return None

    if isinstance(value, (int, float)):
        return str(value)

    return None


def _mapping_at(context: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if not isinstance(context, Mapping):
        return None
    value = context.get(key)
    return value if isinstance(value, Mapping) else None


def _is_status_field_name(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = _normalize_marker(value)
    return normalized in {_normalize_marker(field) for field in _STATUS_FIELD_NAMES}


def _can_use_as_status_value(field_name: Any, value: str) -> bool:
    if not isinstance(field_name, str):
        return False
    normalized_field = _normalize_marker(field_name)
    value_fields = {_normalize_marker(field) for field in _STATUS_VALUE_FIELD_NAMES}
    return normalized_field in value_fields or _normalize_label(value) == _normalize_label(TARGET_STATUS)


def _normalize_marker(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", "", spaced.lower())


def _normalize_label(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()


def _normalize_prefix(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("null")
        return

    print(json.dumps(build_issue_title_update(payload)))


if __name__ == "__main__":
    main()
