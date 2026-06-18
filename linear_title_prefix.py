"""Build Linear issue-title updates for research status transitions.

The automation that calls this module is expected to apply the returned action
to Linear. Keeping this module pure makes the status/title decision easy to
test and safe to run for non-matching webhooks.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "statusname",
    "state",
    "stateid",
    "statename",
    "workflowstate",
    "workflowstateid",
    "workflowstatename",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    The handler accepts the flat Cursor automation payload shape and common
    nested Linear webhook shapes. It intentionally returns ``None`` for
    irrelevant events so callers can safely run it for every webhook.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _event_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    if _normalize_status(_first_status(contexts)) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(contexts, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _event_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add_context(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add_context(event)
    add_context(event.get("triggerContext"))
    add_context(event.get("issue"))

    data = event.get("data")
    add_context(data)
    if isinstance(data, Mapping):
        add_context(data.get("issue"))

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        add_context(trigger_context.get("issue"))
        nested_data = trigger_context.get("data")
        add_context(nested_data)
        if isinstance(nested_data, Mapping):
            add_context(nested_data.get("issue"))

    return contexts


def _is_status_change_event(contexts: Sequence[Mapping[str, Any]]) -> bool:
    event_markers = [
        _normalize_event_name(value)
        for context in contexts
        for key in ("trigger", "webhookType", "action", "type", "event", "eventType")
        for value in (context.get(key),)
        if isinstance(value, str)
    ]

    if any(marker in {"status changed", "state changed", "workflow state changed"} for marker in event_markers):
        return True

    if any(marker in {"update", "updated", "issue update", "issue updated", "updated issue"} for marker in event_markers):
        return _has_status_update_marker(contexts)

    return False


def _has_status_update_marker(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "changedFields"):
            if _contains_status_field(context.get(key)):
                return True

        for key in ("updatedFrom", "changes", "changed", "previousValues"):
            value = context.get(key)
            if isinstance(value, Mapping) and any(_is_status_field_name(field) for field in value):
                return True
            if _contains_status_field(value):
                return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) for key in value)

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_status_field(item) for item in value)

    return False


def _is_status_field_name(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = re.sub(r"[^a-z0-9]", "", _split_camel_case(value).lower())
    return normalized in _STATUS_FIELD_NAMES


def _first_status(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    status_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
        "status",
        "state",
        "workflowState",
    )

    for context in contexts:
        for key in status_keys:
            value = context.get(key)
            text = _status_text(value)
            if text:
                return text

    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str):
                return nested
    return None


def _first_text(contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_status(status: str | None) -> str | None:
    if not status:
        return None
    return _normalize_event_name(status)


def _normalize_event_name(value: str) -> str:
    value = _split_camel_case(value)
    value = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return re.sub(r"\s+", " ", value).strip()


def _split_camel_case(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", value)


def _main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
