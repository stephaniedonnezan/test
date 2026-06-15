"""Build Linear issue title updates for research status changes.

The automation runner can pass either a flat Cursor trigger context or a
Linear-style nested issue webhook. This module keeps the matching logic small
and deterministic so callers can apply the returned action with their Linear
client of choice.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflow_status",
    "workflowstatus",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when an issue moves to ``to research``.

    The returned dictionary intentionally contains only serializable primitives:

    ``{"action": "update_issue_title", "issueId": "<id>", "title": "<title>"}``

    ``None`` means the event is not a qualifying status change or there is not
    enough issue data to safely construct an update.
    """

    if not isinstance(event, Mapping):
        return None

    context = _build_context(event)
    if not _is_status_change_event(context):
        return None

    status = _extract_new_status(context)
    if _normalize_status(status) != _normalize_status(TARGET_STATUS):
        return None

    issue_id = _extract_issue_id(context)
    title = _clean_string(_first_value(context, ("title", "name")))
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _build_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common flat and nested event shapes into one lookup dictionary."""

    context: dict[str, Any] = {}
    _merge_mapping(context, _as_mapping(event.get("triggerContext")))
    _merge_mapping(context, _as_mapping(event.get("issue")))

    data = _as_mapping(event.get("data"))
    _merge_mapping(context, data)
    _merge_mapping(context, _as_mapping(data.get("issue")))

    # Top-level webhook metadata should win over nested issue fields such as
    # Linear's ``type: "Issue"`` value, which is not the event action.
    _merge_mapping(context, event)
    return context


def _merge_mapping(target: dict[str, Any], source: Mapping[str, Any] | None) -> None:
    if source:
        target.update(source)


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    event_tokens = [
        _clean_string(context.get("trigger")),
        _clean_string(context.get("webhookType")),
        _clean_string(context.get("action")),
        _clean_string(context.get("type")),
    ]

    normalized_tokens = {_normalize_event_token(token) for token in event_tokens if token}
    if normalized_tokens & {
        "statuschanged",
        "statuschange",
        "statusupdated",
        "statechanged",
        "statechange",
        "workflowstatechanged",
    }:
        return True

    if normalized_tokens & {"update", "updated", "issueupdated", "updatedissue"}:
        return _updated_fields_include_status(context)

    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields"):
        if _sequence_includes_status(context.get(key)):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_is_status_field_name(key) for key in changes)

    updated_from = context.get("updatedFrom")
    if isinstance(updated_from, Mapping):
        return any(_is_status_field_name(key) for key in updated_from)

    return False


def _sequence_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return any(_is_status_field_name(item) for item in value)
    return False


def _is_status_field_name(value: Any) -> bool:
    return _normalize_key(value) in _STATUS_FIELD_NAMES


def _extract_new_status(context: Mapping[str, Any]) -> str | None:
    explicit = _first_value(
        context,
        (
            "newStatus",
            "new_status",
            "statusName",
            "status_name",
            "newState",
            "new_state",
            "stateName",
            "state_name",
            "workflowStateName",
            "workflow_state_name",
        ),
    )
    if explicit is not None:
        return _clean_string(_status_name(explicit))

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _is_status_field_name(key):
                changed_to = _changed_to_value(value)
                if changed_to is not None:
                    return _clean_string(_status_name(changed_to))

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = context.get(key)
        if value is not None:
            return _clean_string(_status_name(value))

    return None


def _changed_to_value(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value

    for key in ("to", "new", "after", "value", "name"):
        if key in value:
            return value[key]
    return None


def _status_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if key in value:
                return value[key]
    return value


def _extract_issue_id(context: Mapping[str, Any]) -> str | None:
    return _clean_string(
        _first_value(context, ("id", "issueId", "issue_id", "identifier", "key"))
    )


def _first_value(context: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        value = context.get(key)
        if value is not None:
            return value
    return None


def _clean_string(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_status(value: Any) -> str | None:
    if value is None:
        return None

    text = _split_camel_case(str(value))
    text = re.sub(r"[_\-\s]+", " ", text).strip().casefold()
    return text or None


def _normalize_event_token(value: Any) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r"[^a-z0-9]+", "", _split_camel_case(str(value)).casefold())
    return normalized or None


def _normalize_key(value: Any) -> str | None:
    if value is None:
        return None
    return re.sub(r"[^a-z0-9_]+", "", str(value).strip().casefold()) or None


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    """Read a JSON event from stdin and print the computed action, if any."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON input: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
