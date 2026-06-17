"""Build Linear issue-title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}
_TRIGGER_KEYS = ("trigger", "event", "action", "type", "webhookType", "webhook_type")
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_FALLBACK_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_CHANGE_CONTAINER_KEYS = ("changes", "change", "updatedFrom", "updated_from", "previousValues")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
    "changedProperties",
    "changed_properties",
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters To Research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_label(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(contexts)
    title = _extract_title(contexts)
    prefixed_title = _prefixed_title(title)
    if not issue_id or prefixed_title is None:
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": prefixed_title,
    }


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    trigger_context = event.get("triggerContext")
    add(trigger_context)
    add(event)

    for source in list(contexts):
        for key in ("data", "issue", "node"):
            nested = source.get(key)
            add(nested)
            if isinstance(nested, Mapping):
                add(nested.get("issue"))
                add(nested.get("node"))

    return contexts


def _is_status_change_event(contexts: Sequence[Mapping[str, Any]]) -> bool:
    trigger_values = [
        _normalize_label(context.get(key))
        for context in contexts
        for key in _TRIGGER_KEYS
        if key in context
    ]

    if any("status changed" in value or "state changed" in value for value in trigger_values):
        return True

    generic_update = any(
        value in {"update", "updated", "issue update", "issue updated", "updated issue"}
        for value in trigger_values
    )
    if generic_update:
        return _has_status_change_marker(contexts)

    return False


def _has_status_change_marker(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _UPDATED_FIELD_KEYS:
            if _field_collection_mentions_status(context.get(key)):
                return True

        for key in _CHANGE_CONTAINER_KEYS:
            changes = context.get(key)
            if isinstance(changes, Mapping) and _mapping_mentions_status(changes):
                return True

    return False


def _extract_new_status(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in _EXPLICIT_STATUS_KEYS:
            value = _status_text(context.get(key))
            if value:
                return value

    changed_value = _extract_status_from_changes(contexts)
    if changed_value:
        return changed_value

    for context in contexts:
        for key in _FALLBACK_STATUS_KEYS:
            value = _status_text(context.get(key))
            if value:
                return value

    return None


def _extract_status_from_changes(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in _CHANGE_CONTAINER_KEYS:
            changes = context.get(key)
            if not isinstance(changes, Mapping):
                continue

            for field_name, change in changes.items():
                if not _is_status_field(field_name):
                    continue

                value = _new_value_from_change(change)
                if value:
                    return value

    return None


def _new_value_from_change(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("new", "to", "after", "newValue", "new_value", "value", "name"):
            value = _status_text(change.get(key))
            if value:
                return value
    return _status_text(change)


def _extract_issue_id(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    for keys in (("identifier", "key"), ("issueId", "issue_id"), ("id",)):
        for context in contexts:
            for key in keys:
                value = _clean_text(context.get(key))
                if value:
                    return value
    return None


def _extract_title(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in ("title", "name"):
            value = _clean_text(context.get(key))
            if value:
                return value
    return None


def _prefixed_title(title: Any) -> str | None:
    clean_title = _clean_text(title)
    if not clean_title:
        return None
    if re.match(rf"^{re.escape(TITLE_PREFIX)}\b", clean_title, re.IGNORECASE):
        return None
    return f"{TITLE_PREFIX}: {clean_title}"


def _mapping_mentions_status(value: Mapping[Any, Any]) -> bool:
    return any(_is_status_field(field_name) for field_name in value)


def _field_collection_mentions_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        return _mapping_mentions_status(value)
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Sequence):
        return any(_field_collection_mentions_status(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    return _normalize_field(value) in _STATUS_FIELD_NAMES


def _status_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _clean_text(value.get(key))
            if text:
                return text
        return None
    return _clean_text(value)


def _clean_text(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


def _normalize_label(value: Any) -> str:
    text = _status_text(value) or ""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _normalize_field(value: Any) -> str:
    return _normalize_label(value).replace(" ", "")


def main() -> int:
    """Read a JSON event from stdin and print the update action, if any."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2

    result = build_issue_title_update(event)
    if result is not None:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
