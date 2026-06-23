"""Build Linear issue title updates for Cursor research status changes.

The automation runner can call ``build_issue_title_update`` with either the
flat Cursor trigger context or a nested Linear webhook payload. When an issue is
moved to the "to research" status, the function returns the title update action
needed to add the Cursor research marker.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
PREFIXED_TITLE_RE = re.compile(r"^\s*cursor\s+researching\b", re.IGNORECASE)

STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflowstatus",
}

NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "status",
    "state",
    "workflowState",
    "workflow_status",
)

PREFERRED_ISSUE_ID_KEYS = (
    "issueId",
    "issue_id",
    "identifier",
    "key",
)

TITLE_KEYS = (
    "title",
    "name",
)


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters research status."""
    if not isinstance(event, Mapping):
        return None

    contexts = _collect_contexts(event)
    if not _is_relevant_status_change(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_label(new_status) != "to research":
        return None

    issue_id = _first_issue_id(contexts)
    title = _first_text_value(contexts, TITLE_KEYS)
    if not issue_id or not title:
        return None

    if PREFIXED_TITLE_RE.match(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _collect_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely metadata/issue dictionaries, with outer values first."""
    contexts: list[Mapping[str, Any]] = [event]
    for key in ("triggerContext", "webhook", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            contexts.extend(_collect_contexts(value))

    data = event.get("data")
    if isinstance(data, Mapping):
        for key in ("issue", "state", "workflowState"):
            value = data.get(key)
            if isinstance(value, Mapping):
                contexts.extend(_collect_contexts(value))

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        for key in ("state", "workflowState"):
            value = issue.get(key)
            if isinstance(value, Mapping):
                contexts.extend(_collect_contexts(value))

    return _dedupe_mappings(contexts)


def _dedupe_mappings(contexts: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    seen: set[int] = set()
    unique: list[Mapping[str, Any]] = []
    for context in contexts:
        identity = id(context)
        if identity in seen:
            continue
        seen.add(identity)
        unique.append(context)
    return unique


def _is_relevant_status_change(contexts: Sequence[Mapping[str, Any]]) -> bool:
    trigger_values = [
        value
        for context in contexts
        for key in ("trigger", "webhookType", "action", "type")
        for value in [_string_value(context.get(key))]
        if value
    ]
    normalized_triggers = {_normalize_label(value) for value in trigger_values}

    if any(_is_direct_status_trigger(trigger) for trigger in normalized_triggers):
        return True

    if not any(_is_generic_update_trigger(trigger) for trigger in normalized_triggers):
        return False

    return _has_status_changed_field(contexts)


def _is_direct_status_trigger(trigger: str) -> bool:
    return trigger in {
        "status changed",
        "state changed",
        "workflow state changed",
        "workflow status changed",
    }


def _is_generic_update_trigger(trigger: str) -> bool:
    return trigger in {
        "update",
        "updated",
        "issue update",
        "issue updated",
        "updated issue",
    }


def _has_status_changed_field(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "changedFields", "changed_fields"):
            if _sequence_mentions_status(context.get(key)):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            if any(_is_status_field(key) for key in changes):
                return True
        elif isinstance(changes, Sequence) and not isinstance(changes, (str, bytes)):
            for change in changes:
                if not isinstance(change, Mapping):
                    continue
                field = (
                    change.get("field")
                    or change.get("name")
                    or change.get("key")
                    or change.get("property")
                )
                if _is_status_field(field):
                    return True

    return False


def _sequence_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return any(_is_status_field(item) for item in value)

    return False


def _is_status_field(value: Any) -> bool:
    normalized = _normalize_key(_string_value(value))
    return normalized in STATUS_FIELD_NAMES


def _extract_new_status(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        value = _first_text_from_mapping(context, ("newStatus", "new_status"))
        if value:
            return value

    value = _extract_status_from_changes(contexts)
    if value:
        return value

    for context in contexts:
        value = _first_text_from_mapping(context, NEW_STATUS_KEYS)
        if value:
            return value

    return None


def _extract_status_from_changes(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        changes = context.get("changes")
        if isinstance(changes, Mapping):
            for key, change in changes.items():
                if not _is_status_field(key):
                    continue
                value = _new_change_value(change)
                if value:
                    return value

        if isinstance(changes, Sequence) and not isinstance(changes, (str, bytes)):
            for change in changes:
                if not isinstance(change, Mapping):
                    continue
                field = (
                    change.get("field")
                    or change.get("name")
                    or change.get("key")
                    or change.get("property")
                )
                if not _is_status_field(field):
                    continue
                value = _new_change_value(change)
                if value:
                    return value

    return None


def _new_change_value(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("newValue", "new_value", "to", "after", "value"):
            value = _string_value(change.get(key))
            if value:
                return value
        return _string_value(change.get("name"))

    return _string_value(change)


def _first_text_value(
    contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]
) -> str | None:
    for context in contexts:
        value = _first_text_from_mapping(context, keys)
        if value:
            return value
    return None


def _first_issue_id(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    issue_id = _first_text_value(contexts, PREFERRED_ISSUE_ID_KEYS)
    if issue_id:
        return issue_id

    for context in contexts:
        if _looks_like_issue_context(context):
            issue_id = _first_text_from_mapping(context, ("id",))
            if issue_id:
                return issue_id

    return _first_text_value(contexts, ("id",))


def _looks_like_issue_context(context: Mapping[str, Any]) -> bool:
    return any(key in context for key in ("title", "state", "workflowState", "status"))


def _first_text_from_mapping(
    context: Mapping[str, Any], keys: Sequence[str]
) -> str | None:
    for key in keys:
        value = _string_value(context.get(key))
        if value:
            return value

    return None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "id"):
            nested_value = _string_value(value.get(key))
            if nested_value:
                return nested_value

    return None


def _normalize_label(value: str | None) -> str:
    if not value:
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()


def _normalize_key(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", _normalize_label(value))


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
