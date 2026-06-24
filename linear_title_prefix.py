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
TITLE_PREFIX_RE = re.compile(rf"^\s*{re.escape(TITLE_PREFIX)}\b", re.IGNORECASE)


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title update action for matching research events."""
    if not isinstance(event, Mapping):
        return None

    context = _flatten_event_context(event)
    if not _is_status_change_event(context):
        return None

    new_status = _extract_status(context)
    if _normalize_label(new_status) != _normalize_label(RESEARCH_STATUS):
        return None

    issue_id = _first_text(context, "issueId", "issue_id", "id", "identifier", "key")
    title = _first_text(context, "title", "name")
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or TITLE_PREFIX_RE.match(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _flatten_event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor and Linear payload locations into one lookup map."""
    sources: list[Mapping[str, Any]] = []

    def collect(value: Any, depth: int = 0) -> None:
        if not isinstance(value, Mapping) or depth > 6:
            return

        for key in (
            "issue",
            "data",
            "payload",
            "triggerContext",
            "automation_trigger_info",
        ):
            collect(value.get(key), depth + 1)

        sources.append(value)

    collect(event)

    context: dict[str, Any] = {}
    for source in sources:
        context.update(source)
    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = (
        context.get("trigger"),
        context.get("webhookType"),
        context.get("webhook_type"),
        context.get("action"),
        context.get("type"),
    )
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
        if _fields_mention_status(context.get(key)):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_token(key) in STATUS_FIELD_NAMES for key in changes)

    if _is_non_text_sequence(changes):
        return any(_change_mentions_status(change) for change in changes)

    return False


def _fields_mention_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_token(value) in STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(_normalize_token(key) in STATUS_FIELD_NAMES for key in value)

    if _is_non_text_sequence(value):
        return any(_normalize_token(item) in STATUS_FIELD_NAMES for item in value)

    return False


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
        text = _status_text(context.get(key))
        if text:
            return text

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _normalize_token(key) in STATUS_FIELD_NAMES:
                text = _status_text_from_change(value)
                if text:
                    return text

    if _is_non_text_sequence(changes):
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


def _is_non_text_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


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
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
