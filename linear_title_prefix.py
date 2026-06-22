"""Build Linear issue title updates for research status transitions.

The automation runner can pass either Cursor's flat ``triggerContext`` payload or
Linear's nested issue webhook shape.  This module keeps the contract small:
return an update action only when an issue status changes to "to research".
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
    "workflow_state",
    "workflow_state_id",
}
_NEW_STATUS_FIELD_NAMES = {
    "newstatus",
    "new_status",
    "statusname",
    "state_name",
    "statename",
    "workflow_state_name",
    "workflowstatename",
}
_TRIGGER_FIELD_NAMES = {
    "action",
    "event",
    "eventtype",
    "event_type",
    "trigger",
    "type",
    "webhooktype",
    "webhook_type",
}
_STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statechanged",
    "workflowstatechanged",
}
_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when a status changes to research.

    The returned dictionary is intentionally transport-agnostic so an automation
    runner can translate it to a Linear API call.
    """

    if not isinstance(event, Mapping):
        return None

    mappings = list(_walk_mappings(event))
    if not _is_status_change_event(mappings):
        return None
    if not any(_normalize_status(status) == TARGET_STATUS for status in _status_candidates(mappings)):
        return None

    issue_id = _first_text_value(mappings, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text_value(mappings, ("title",))
    if issue_id is None or title is None:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested in value.values():
            yield from _walk_mappings(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_mappings(item)


def _is_status_change_event(mappings: list[Mapping[str, Any]]) -> bool:
    trigger_values = [
        _normalize_token(value)
        for mapping in mappings
        for key, value in mapping.items()
        if _normalize_key(key) in _TRIGGER_FIELD_NAMES and _text(value) is not None
    ]

    if any(
        value in _STATUS_CHANGE_TRIGGERS or any(value.endswith(trigger) for trigger in _STATUS_CHANGE_TRIGGERS)
        for value in trigger_values
    ):
        return True

    return any(value in _GENERIC_UPDATE_TRIGGERS for value in trigger_values) and _updated_fields_include_status(
        mappings
    )


def _updated_fields_include_status(mappings: list[Mapping[str, Any]]) -> bool:
    return any(
        _change_map_includes_status(mapping)
        or _updated_fields_include_status_value(mapping.get("updatedFields"))
        or _updated_fields_include_status_value(mapping.get("updated_fields"))
        for mapping in mappings
    )


def _change_map_includes_status(mapping: Mapping[str, Any]) -> bool:
    for key in ("changes", "updatedFrom", "updated_from"):
        changes = mapping.get(key)
        if not isinstance(changes, Mapping):
            continue
        for field_name in changes:
            if _is_status_field(field_name):
                return True
    return False


def _updated_fields_include_status_value(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        field = value.get("field") or value.get("name") or value.get("key")
        return _updated_fields_include_status_value(field)
    if isinstance(value, list):
        return any(_updated_fields_include_status_value(item) for item in value)
    return False


def _status_candidates(mappings: list[Mapping[str, Any]]) -> Iterable[str]:
    for mapping in mappings:
        yield from _new_status_candidates_from_changes(mapping)
        yield from _new_status_candidates_from_updated_fields(mapping.get("updatedFields"))
        yield from _new_status_candidates_from_updated_fields(mapping.get("updated_fields"))

    for mapping in mappings:
        for key, value in mapping.items():
            normalized_key = _normalize_key(key)
            if _is_previous_status_key(key):
                continue
            if normalized_key in _NEW_STATUS_FIELD_NAMES or _is_status_field(key):
                text = _status_text(value)
                if text is not None:
                    yield text


def _new_status_candidates_from_changes(mapping: Mapping[str, Any]) -> Iterable[str]:
    for key in ("changes", "updatedFrom", "updated_from"):
        changes = mapping.get(key)
        if not isinstance(changes, Mapping):
            continue
        for field_name, field_change in changes.items():
            if not _is_status_field(field_name):
                continue
            text = _new_value_text(field_change)
            if text is not None:
                yield text


def _new_status_candidates_from_updated_fields(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        if _updated_fields_include_status_value(value):
            text = _new_value_text(value)
            if text is not None:
                yield text
        return
    if isinstance(value, list):
        for item in value:
            yield from _new_status_candidates_from_updated_fields(item)


def _new_value_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "new", "to", "after", "value"):
            text = _status_text(value.get(key))
            if text is not None:
                return text
        return None
    return _status_text(value)


def _status_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _text(value.get(key))
            if text is not None:
                return text
        return None
    return _text(value)


def _first_text_value(mappings: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    normalized_keys = {_normalize_key(key) for key in keys}
    for mapping in mappings:
        for key, value in mapping.items():
            if _normalize_key(key) in normalized_keys:
                text = _text(value)
                if text is not None:
                    return text
    return None


def _is_status_field(value: Any) -> bool:
    text = _text(value)
    if text is None:
        return False
    normalized = _normalize_key(text)
    return normalized in _STATUS_FIELD_NAMES or normalized.endswith("status") or normalized.endswith("state")


def _is_previous_status_key(value: Any) -> bool:
    normalized = _normalize_key(value)
    return _is_status_field(value) and normalized.startswith(("old", "previous", "from", "before"))


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _normalize_status(value: str) -> str:
    return " ".join(_split_words(value))


def _normalize_key(value: Any) -> str:
    text = _text(value)
    if text is None:
        return ""
    return re.sub(r"[^a-z0-9_]", "", text.lower())


def _normalize_token(value: Any) -> str:
    text = _text(value)
    if text is None:
        return ""
    return "".join(_split_words(text))


def _split_words(value: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return [word for word in re.split(r"[^a-zA-Z0-9]+", spaced.lower()) if word]


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
