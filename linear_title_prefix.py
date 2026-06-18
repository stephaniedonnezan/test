"""Build title-update actions for Linear issues moved to research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_TRIGGER_KEYS = ("trigger", "event", "eventType", "webhookType", "action", "type")
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "newState",
    "new_state",
    "toState",
    "to_state",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_FALLBACK_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_ID_KEYS = ("issueId", "issue_id", "id", "identifier", "key")
_TITLE_KEYS = ("title", "name")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
)
_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to To Research.

    The Cursor automation payload is flat under ``triggerContext`` while Linear
    webhooks are often nested under ``data`` or ``data.issue``. This function
    accepts both shapes and returns ``None`` for unrelated events.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _extract_status(contexts)
    if _normalize_label(status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_string(contexts, _ID_KEYS)
    title = _extract_first_string(contexts, _TITLE_KEYS)
    if issue_id is None or title is None:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event)
    add(event.get("triggerContext"))
    add(event.get("issue"))

    data = event.get("data")
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("node"))

    webhook = event.get("webhook")
    if isinstance(webhook, Mapping):
        add(webhook.get("data"))

    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    update_event_seen = False

    for context in contexts:
        for key in _TRIGGER_KEYS:
            normalized = _normalize_label(context.get(key))
            compact = normalized.replace(" ", "")
            if compact in {"statuschanged", "statuschange", "statechanged", "statechange"}:
                return True
            if normalized in {"issue updated", "updated issue", "update", "updated"}:
                update_event_seen = True

    return update_event_seen and _changed_fields_include_status(contexts)


def _changed_fields_include_status(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _UPDATED_FIELD_KEYS:
            if _field_collection_mentions_status(context.get(key)):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            for changed_key in changes:
                if _is_status_field(changed_key):
                    return True

    return False


def _field_collection_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value)

    if isinstance(value, Iterable):
        return any(_is_status_field(item) for item in value)

    return False


def _extract_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        value = _extract_first_present(context, _EXPLICIT_STATUS_KEYS)
        status = _string_from_status_value(value)
        if status is not None:
            return status

    for context in contexts:
        status = _status_from_changes(context.get("changes"))
        if status is not None:
            return status

    for context in contexts:
        value = _extract_first_present(context, _FALLBACK_STATUS_KEYS)
        status = _string_from_status_value(value)
        if status is not None:
            return status

    return None


def _status_from_changes(changes: Any) -> str | None:
    if not isinstance(changes, Mapping):
        return None

    for key, value in changes.items():
        if not _is_status_field(key):
            continue

        status = _status_to_value(value)
        if status is not None:
            return status

    return None


def _status_to_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "new", "after", "current", "value"):
            status = _string_from_status_value(value.get(key))
            if status is not None:
                return status
        return _string_from_status_value(value)

    return _string_from_status_value(value)


def _string_from_status_value(value: Any) -> str | None:
    if isinstance(value, str):
        value = value.strip()
        return value or None

    if isinstance(value, Mapping):
        return _extract_first_string([value], ("name", "title", "label"))

    return None


def _extract_first_present(context: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in context:
            return context[key]
    return None


def _extract_first_string(
    contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]
) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str):
                value = value.strip()
                if value:
                    return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.strip().lower().startswith(PREFIX.lower())


def _is_status_field(value: Any) -> bool:
    return _normalize_label(value) in _STATUS_FIELD_NAMES


def _normalize_label(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return " ".join(value.casefold().split())


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
