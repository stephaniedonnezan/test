"""Linear issue title prefix automation for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}
_STATUS_CHANGE_EVENTS = {
    "status change",
    "status changed",
    "state change",
    "state changed",
    "workflow state change",
    "workflow state changed",
}
_ISSUE_UPDATE_EVENTS = {"update", "updated", "issue update", "issue updated", "updated issue"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research.

    The Cursor automation payload exposes issue metadata in ``triggerContext``.
    Linear webhook payloads commonly keep it under ``data`` or ``issue``. This
    helper accepts both shapes so the title-prefix rule stays independent from
    the exact transport that invokes it.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(event, contexts):
        return None

    new_status = _first_status_value(event, contexts)
    if not _is_target_status(new_status):
        return None

    issue_id = _first_text(contexts, ("id", "issueId", "issue_id", "identifier", "key"))
    title = _first_text(contexts, ("title",))
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
    """Return likely issue/trigger dictionaries in lookup-precedence order."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event.get("triggerContext"))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data)

    add(event.get("issue"))
    add(event)
    return contexts


def _is_status_change_event(event: Mapping[str, Any], contexts: Sequence[Mapping[str, Any]]) -> bool:
    event_names = {
        normalized
        for context in contexts
        for normalized in (
            _normalize_words(context.get("trigger")),
            _normalize_words(context.get("action")),
            _normalize_words(context.get("type")),
            _normalize_words(context.get("webhookType")),
        )
        if normalized
    }

    if event_names & _STATUS_CHANGE_EVENTS:
        return True

    return bool(event_names & _ISSUE_UPDATE_EVENTS and _has_status_field_marker(event, contexts))


def _has_status_field_marker(event: Mapping[str, Any], contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "changedFields", "fields"):
            if _sequence_mentions_status_field(context.get(key)):
                return True

        for key in ("changes", "changed", "updates"):
            value = context.get(key)
            if isinstance(value, Mapping) and any(_is_status_field_name(field) for field in value):
                return True

    return _mapping_has_status_change(event)


def _mapping_has_status_change(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            (_is_status_field_name(key) and isinstance(nested, Mapping))
            or _mapping_has_status_change(nested)
            for key, nested in value.items()
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_mapping_has_status_change(item) for item in value)
    return False


def _first_status_value(event: Mapping[str, Any], contexts: Sequence[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        value = _first_text(
            (context,),
            (
                "newStatus",
                "new_status",
                "newState",
                "new_state",
                "toStatus",
                "to_status",
                "statusName",
                "stateName",
                "workflowStateName",
            ),
        )
        if value:
            return value

    changed_value = _first_changed_status_value(event)
    if changed_value:
        return changed_value

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = _status_text(context.get(key))
            if value:
                return value

    return None


def _first_changed_status_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if _is_status_field_name(key):
                status = _change_value_text(nested)
                if status:
                    return status

        for nested in value.values():
            status = _first_changed_status_value(nested)
            if status:
                return status

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            status = _first_changed_status_value(item)
            if status:
                return status

    return None


def _change_value_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "new", "after", "to", "name"):
            status = _status_text(value.get(key))
            if status:
                return status
    return _status_text(value)


def _status_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state", "workflowState"):
            status = _status_text(value.get(key))
            if status:
                return status
        return None

    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _sequence_mentions_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return any(_is_status_field_name(item) for item in value)
    return False


def _is_status_field_name(value: Any) -> bool:
    return _normalize_words(value) in _STATUS_FIELD_NAMES


def _is_target_status(value: Any) -> bool:
    return _normalize_words(_status_text(value)) == TARGET_STATUS


def _has_research_prefix(title: str) -> bool:
    return title.lstrip().casefold().startswith(PREFIX.casefold())


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    words = re.sub(r"[^A-Za-z0-9]+", " ", words)
    return re.sub(r"\s+", " ", words).strip().casefold()


def main() -> int:
    """Read an event payload from stdin and print the requested action."""

    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    print(json.dumps(action, indent=2, sort_keys=True) if action else "null")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
