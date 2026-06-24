"""Build Linear issue title update actions for research status changes.

The automation runner can pass either Cursor's flattened trigger context or a
more native Linear webhook shape. This module keeps the decision local and
side-effect free: callers receive an update action to apply, or ``None`` when
the event should be ignored.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}
STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statusupdated",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}
GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action for matching research events."""
    if not isinstance(event, Mapping):
        return None

    context = _flatten_event_context(event)
    if not _is_status_change_event(context):
        return None

    new_status = _extract_status(context)
    if _normalize_label(new_status) != _normalize_label(RESEARCH_STATUS):
        return None

    issue_id = _first_text(context, "issueId", "issue_id", "identifier", "key", "id")
    title = _first_text(context, "title", "name")
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _flatten_event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor and Linear payload locations into one lookup map."""
    context: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if isinstance(value, Mapping):
            context.update(value)

    trigger_context = event.get("automation_trigger_info")
    if isinstance(trigger_context, Mapping):
        trigger_context = trigger_context.get("triggerContext", trigger_context)

    nested_locations = (
        event.get("data"),
        event.get("issue"),
        event.get("payload"),
        trigger_context,
    )
    for location in nested_locations:
        if isinstance(location, Mapping):
            merge(location.get("issue"))
            merge(location.get("data"))
            merge(location)

    # Top-level fields should win over nested issue fields because Cursor's
    # trigger context often carries the freshest status metadata.
    merge(event)
    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        context.get("trigger"),
        context.get("webhookType"),
        context.get("action"),
        context.get("type"),
    ]
    normalized_triggers = {
        normalized
        for value in trigger_values
        if (normalized := _normalize_token(value))
    }

    if normalized_triggers & STATUS_CHANGE_TRIGGERS:
        return True

    if normalized_triggers & GENERIC_UPDATE_TRIGGERS:
        return _updated_fields_include_status(context)

    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields"):
        if _sequence_mentions_status(context.get(key)):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_token(key) in STATUS_FIELD_NAMES for key in changes)

    if isinstance(changes, Sequence) and not isinstance(changes, (str, bytes)):
        return any(_change_mentions_status(change) for change in changes)

    return False


def _sequence_mentions_status(value: Any) -> bool:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return False
    return any(_normalize_token(item) in STATUS_FIELD_NAMES for item in value)


def _change_mentions_status(change: Any) -> bool:
    if isinstance(change, Mapping):
        field = change.get("field") or change.get("name") or change.get("key")
        return _normalize_token(field) in STATUS_FIELD_NAMES
    return _normalize_token(change) in STATUS_FIELD_NAMES


def _extract_status(context: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "status",
        "state",
        "workflowState",
        "workflow_state",
    ):
        value = context.get(key)
        text = _status_text(value)
        if text:
            return text

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _normalize_token(key) in STATUS_FIELD_NAMES:
                text = _status_text_from_change(value)
                if text:
                    return text

    if isinstance(changes, Sequence) and not isinstance(changes, (str, bytes)):
        for change in changes:
            if _change_mentions_status(change):
                text = _status_text_from_change(change)
                if text:
                    return text

    return None


def _status_text_from_change(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "new", "after", "value", "name"):
            text = _status_text(value.get(key))
            if text:
                return text
    return _status_text(value)


def _status_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return _first_text(value, "name", "title", "label")
    return None


def _first_text(mapping: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_label(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(_split_words(value))


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return "".join(_split_words(value))


def _split_words(value: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.findall(r"[a-z0-9]+", spaced.lower())


def main() -> int:
    """Read an event JSON object from stdin and print the requested action."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
