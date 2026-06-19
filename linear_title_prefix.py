"""Build Linear issue-title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status change",
    "status changed",
    "state change",
    "state changed",
    "workflow state change",
    "workflow state changed",
    "workflow status change",
    "workflow status changed",
}

_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "workflow status",
    "workflowstate",
}

_EVENT_FIELD_KEYS = (
    "trigger",
    "webhookType",
    "webhook_type",
    "event",
    "eventType",
    "event_type",
    "action",
    "type",
)

_EXPLICIT_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "toStatus",
    "to_status",
    "toState",
    "to_state",
)

_CURRENT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title", "issueTitle", "issue_title", "name")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to To Research.

    The automation payloads used by Cursor and Linear vary: some are flat
    ``triggerContext`` dictionaries, while others are nested webhook objects.
    This function accepts both and returns a small action object for the caller
    to apply through the Linear API.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_research_status_change(event):
        return None

    issue_id = _first_text(_ISSUE_ID_KEYS, _issue_candidates(event))
    title = _first_text(_TITLE_KEYS, _issue_candidates(event))

    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_research_status_change(event: Mapping[str, Any]) -> bool:
    return _is_status_change_event(event) and _normalize_text(_new_status(event)) == TARGET_STATUS


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_names = {
        normalized
        for mapping in _iter_mappings(event)
        for key in _EVENT_FIELD_KEYS
        if (normalized := _normalize_text(mapping.get(key)))
    }

    if event_names & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    return bool(event_names & _GENERIC_UPDATE_EVENTS) and _has_status_change_marker(event)


def _has_status_change_marker(event: Mapping[str, Any]) -> bool:
    for mapping in _iter_mappings(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(mapping.get(key)):
                return True

        for key in ("changes", "change", "changed", "updatedFrom", "updated_from"):
            if _contains_status_field(mapping.get(key)):
                return True

        if _normalize_text(mapping.get("field")) in _STATUS_FIELD_NAMES:
            return True

    return False


def _new_status(event: Mapping[str, Any]) -> str | None:
    candidates = tuple(_issue_candidates(event))

    for key in _EXPLICIT_NEW_STATUS_KEYS:
        value = _first_value(key, candidates)
        status = _status_text(value)
        if status:
            return status

    changed_status = _new_status_from_change_metadata(event)
    if changed_status:
        return changed_status

    for key in _CURRENT_STATUS_KEYS:
        value = _first_value(key, candidates)
        status = _status_text(value)
        if status:
            return status

    return None


def _new_status_from_change_metadata(event: Mapping[str, Any]) -> str | None:
    for mapping in _iter_mappings(event):
        for key in ("changes", "change", "changed"):
            status = _new_status_from_change_value(mapping.get(key))
            if status:
                return status
    return None


def _new_status_from_change_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        field = _normalize_text(value.get("field") or value.get("name"))
        if field in _STATUS_FIELD_NAMES:
            for key in ("to", "new", "newValue", "new_value", "after"):
                status = _status_text(value.get(key))
                if status:
                    return status

        for key, nested in value.items():
            if _normalize_text(key) in _STATUS_FIELD_NAMES:
                status = (
                    _new_status_from_change_value(nested)
                    or _status_text(_change_new_value(nested))
                    or _status_text(nested)
                )
                if status:
                    return status

        for nested in value.values():
            status = _new_status_from_change_value(nested)
            if status:
                return status

    if _is_sequence(value):
        for item in value:
            status = _new_status_from_change_value(item)
            if status:
                return status

    return None


def _change_new_value(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return None

    for key in ("to", "new", "newValue", "new_value", "after"):
        if key in value:
            return value[key]
    return None


def _issue_candidates(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []

    for value in (
        event.get("triggerContext"),
        event.get("trigger_context"),
        event,
        event.get("issue"),
        event.get("data"),
    ):
        _append_mapping_candidate(candidates, value)

    data = event.get("data")
    if isinstance(data, Mapping):
        _append_mapping_candidate(candidates, data.get("issue"))
        _append_mapping_candidate(candidates, data.get("node"))

    return candidates


def _append_mapping_candidate(candidates: list[Mapping[str, Any]], value: Any) -> None:
    if isinstance(value, Mapping) and value not in candidates:
        candidates.append(value)


def _first_text(keys: Sequence[str], candidates: Sequence[Mapping[str, Any]]) -> str | None:
    for key in keys:
        value = _first_value(key, candidates)
        text = _coerce_text(value)
        if text:
            return text
    return None


def _first_value(key: str, candidates: Sequence[Mapping[str, Any]]) -> Any:
    for mapping in candidates:
        if key in mapping:
            return mapping[key]
    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _first_text(("name", "title", "value", "label", "status"), (value,))
    return _coerce_text(value)


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if _normalize_text(key) in _STATUS_FIELD_NAMES:
                return True
            if _contains_status_field(nested):
                return True
        return False

    if _is_sequence(value):
        return any(_contains_status_field(item) for item in value)

    return _normalize_text(value) in _STATUS_FIELD_NAMES


def _iter_mappings(value: Any) -> Any:
    if isinstance(value, Mapping):
        yield value
        for nested in value.values():
            yield from _iter_mappings(nested)
    elif _is_sequence(value):
        for item in value:
            yield from _iter_mappings(item)


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (str, int, float)):
        text = str(value).strip()
        return text or None
    return None


def _normalize_text(value: Any) -> str:
    text = _coerce_text(value)
    if not text:
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _has_research_prefix(title: str) -> bool:
    return title.strip().lower().startswith(PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
