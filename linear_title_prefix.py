"""Build Linear issue title updates for research-status automations.

The automation receives webhook-like payloads from Cursor/Linear.  When a
Linear issue moves to "to research", this module returns an action describing
the title update that should be applied by the caller.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_KEYS = {"status", "state", "workflowstate"}
_DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_ISSUE_UPDATE_TRIGGERS = {
    "issue updated",
    "updated issue",
    "issue update",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue-title update action for research transitions.

    The return value is intentionally small so it can be handed to the
    integration layer that performs the Linear mutation:

    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_research_status_change(contexts):
        return None

    issue_id = _first_string(contexts, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_string(contexts, ("title", "name", "summary"))
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely metadata/issue dictionaries in precedence order."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event)
    for key in ("triggerContext", "data", "issue", "node"):
        add(event.get(key))

    for parent_key in ("triggerContext", "data"):
        parent = event.get(parent_key)
        if isinstance(parent, Mapping):
            for child_key in ("issue", "node", "data"):
                add(parent.get(child_key))

    data = event.get("data")
    if isinstance(data, Mapping):
        node = data.get("node")
        if isinstance(node, Mapping):
            add(node.get("issue"))

    return contexts


def _is_research_status_change(contexts: Iterable[Mapping[str, Any]]) -> bool:
    context_list = list(contexts)
    if _status_from_explicit_fields(context_list) != TARGET_STATUS:
        return False

    if _has_direct_status_trigger(context_list):
        return True

    return _has_changed_status_field(context_list)


def _status_from_explicit_fields(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    context_list = list(contexts)

    for context in context_list:
        for key in ("newStatus", "new_status", "statusName", "stateName", "workflowStateName"):
            status = _normalize_status_value(context.get(key))
            if status:
                return status

    for context in context_list:
        for field_key in ("changes", "changedFields", "updatedFields"):
            status = _status_from_change_metadata(context.get(field_key))
            if status:
                return status

    for context in context_list:
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _normalize_status_value(context.get(key))
            if status:
                return status

    return None


def _has_direct_status_trigger(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type", "eventType"):
            trigger = _normalize_words(context.get(key))
            if trigger in _DIRECT_STATUS_TRIGGERS:
                return True
    return False


def _has_changed_status_field(contexts: Iterable[Mapping[str, Any]]) -> bool:
    saw_issue_update = False
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type", "eventType"):
            trigger = _normalize_words(context.get(key))
            if trigger in _ISSUE_UPDATE_TRIGGERS:
                saw_issue_update = True

    if not saw_issue_update:
        return False

    for context in contexts:
        for key in ("updatedFields", "changedFields", "changes"):
            if _metadata_mentions_status_field(context.get(key)):
                return True

    return False


def _status_from_change_metadata(value: Any) -> str | None:
    if isinstance(value, Mapping):
        if any(_is_status_key(value.get(key)) for key in ("field", "name", "key", "property")):
            status = _normalize_status_value(
                {
                    key: value.get(key)
                    for key in ("newValue", "new_value", "to", "after", "new", "current")
                }
            )
            if status:
                return status

        for key, nested_value in value.items():
            if _is_status_key(key):
                status = _normalize_status_value(nested_value)
                if status:
                    return status
            status = _status_from_change_metadata(nested_value)
            if status:
                return status
        return None

    if isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                continue
            status = _status_from_change_metadata(item)
            if status:
                return status
        return None

    return None


def _metadata_mentions_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_key(value)

    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if _is_status_key(key):
                return True
            if isinstance(nested_value, str) and _is_status_key(nested_value):
                return True
            if _metadata_mentions_status_field(nested_value):
                return True
        return False

    if isinstance(value, list):
        return any(_metadata_mentions_status_field(item) for item in value)

    return False


def _normalize_status_value(value: Any) -> str | None:
    if isinstance(value, str):
        normalized = _normalize_words(value)
        return normalized or None

    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "to", "after", "new", "current", "name", "title"):
            normalized = _normalize_status_value(value.get(key))
            if normalized:
                return normalized

    return None


def _first_string(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    normalized_keys = {_normalize_key(key) for key in keys}
    for context in contexts:
        for key, value in context.items():
            if _normalize_key(key) in normalized_keys and isinstance(value, str):
                stripped = value.strip()
                if stripped:
                    return stripped
    return None


def _has_prefix(title: str) -> bool:
    return title.strip().lower().startswith(PREFIX.lower())


def _is_status_key(value: Any) -> bool:
    return _normalize_key(value) in _STATUS_FIELD_KEYS


def _normalize_key(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    with_camel_spaces = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", with_camel_spaces).strip().lower()
    return re.sub(r"\s+", " ", words)


def main() -> int:
    """Read a JSON event from stdin and print the update action, if any."""

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
