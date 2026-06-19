"""Build Linear issue title updates for research-status transitions.

The automation runner is responsible for applying the returned action to
Linear. This module keeps the webhook parsing and title-prefix decision
side-effect free so it can be tested in isolation.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflow status",
    "workflow state",
}
_EVENT_KEYS = ("trigger", "action", "type", "webhookType", "webhook_type", "event")
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "statusName",
    "status_name",
    "toStatus",
    "to_status",
)


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue moves to research.

    The accepted payload shapes intentionally cover Cursor automation trigger
    contexts and common Linear webhook layouts. Invalid, unrelated, or already
    prefixed issues return ``None``.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _collect_contexts(event)

    if not _is_status_change_event(contexts):
        return None

    status = _extract_new_status(contexts)
    if _normalize_label(status) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _collect_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely metadata/issue contexts from outermost to innermost."""

    contexts: list[Mapping[str, Any]] = [event]

    for key in ("triggerContext", "trigger_context", "data", "issue", "node"):
        value = event.get(key)
        if isinstance(value, Mapping):
            contexts.append(value)

    for parent_key in ("triggerContext", "trigger_context", "data"):
        parent = event.get(parent_key)
        if not isinstance(parent, Mapping):
            continue
        for child_key in ("issue", "node", "state", "workflowState", "workflow_state"):
            child = parent.get(child_key)
            if isinstance(child, Mapping):
                contexts.append(child)

    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    saw_generic_update = False

    for context in contexts:
        for key in _EVENT_KEYS:
            marker = context.get(key)
            if _is_status_change_marker(marker):
                return True
            if _is_generic_update_marker(marker):
                saw_generic_update = True

    return saw_generic_update and _updated_status_fields(contexts)


def _is_status_change_marker(value: Any) -> bool:
    normalized = _normalize_label(value)
    if not normalized:
        return False

    words = set(normalized.split())
    if "status" in words and ({"change", "changed"} & words):
        return True
    if "state" in words and ({"change", "changed"} & words):
        return True

    return normalized in {
        "status changed",
        "status change",
        "state changed",
        "state change",
        "workflow state changed",
        "workflow state change",
    }


def _is_generic_update_marker(value: Any) -> bool:
    normalized = _normalize_label(value)
    if not normalized:
        return False

    words = set(normalized.split())
    return "update" in words or "updated" in words


def _updated_status_fields(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        if _contains_status_field(context.get("updatedFields")):
            return True
        if _contains_status_field(context.get("updated_fields")):
            return True

        changes = context.get("changes")
        if isinstance(changes, Mapping) and any(_is_status_field_name(key) for key in changes):
            return True
        if isinstance(changes, Iterable) and not isinstance(changes, (str, bytes, Mapping)):
            if any(_contains_status_field(change) for change in changes):
                return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        candidates = list(value.keys())
        for key in ("field", "name", "fieldName", "field_name"):
            candidates.append(value.get(key))
        return any(_is_status_field_name(candidate) for candidate in candidates)

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_contains_status_field(item) for item in value)

    return _is_status_field_name(value)


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_label(value)
    compact = normalized.replace(" ", "")
    return normalized in _STATUS_FIELD_NAMES or compact in _STATUS_FIELD_NAMES


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    contexts = list(contexts)

    for key in _EXPLICIT_STATUS_KEYS:
        value = _first_text(contexts, (key,))
        if value:
            return value

    changes_status = _status_from_changes(contexts)
    if changes_status:
        return changes_status

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = context.get(key)
            if isinstance(value, Mapping):
                named_value = _first_text((value,), ("name", "title", "label"))
                if named_value:
                    return named_value
            elif _text(value):
                return _text(value)

    return None


def _status_from_changes(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        changes = context.get("changes")
        if isinstance(changes, Mapping):
            value = _status_from_change_mapping(changes)
            if value:
                return value
        elif isinstance(changes, Iterable) and not isinstance(changes, (str, bytes)):
            for change in changes:
                if isinstance(change, Mapping):
                    value = _status_from_change_record(change)
                    if value:
                        return value

    return None


def _status_from_change_mapping(changes: Mapping[str, Any]) -> str | None:
    for key, change in changes.items():
        if not _is_status_field_name(key):
            continue
        if isinstance(change, Mapping):
            value = _status_from_change_value(change)
            if value:
                return value
        if _text(change):
            return _text(change)
    return None


def _status_from_change_record(change: Mapping[str, Any]) -> str | None:
    field = _first_text((change,), ("field", "fieldName", "field_name"))
    if field and not _is_status_field_name(field):
        return None

    return _status_from_change_value(change)


def _status_from_change_value(change: Mapping[str, Any]) -> str | None:
    value = _first_text(
        (change,),
        ("newValue", "new_value", "to", "after", "value", "title", "label"),
    )
    if value:
        return value

    for key in ("newValue", "new_value", "to", "after", "value"):
        nested_value = change.get(key)
        if isinstance(nested_value, Mapping):
            value = _first_text((nested_value,), ("name", "title", "label"))
            if value:
                return value

    value = _first_text((change,), ("name",))
    if value and not _is_status_field_name(value):
        return value

    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _text(context.get(key))
            if value:
                return value
    return None


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _normalize_label(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    if action is not None:
        print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
