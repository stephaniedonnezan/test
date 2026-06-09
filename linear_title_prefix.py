"""Build Linear issue title update actions for research status changes.

The automation runtime passes Linear issue webhooks as JSON-like dictionaries.
When an issue moves to "to research", this module returns an action describing
the title update that should be applied by the caller.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowState",
    "workflow_state",
    "workflowStatus",
    "workflow_status",
}
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "status",
    "state",
    "workflowState",
    "workflow_state",
    "workflowStatus",
    "workflow_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
)


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue-title update action, or None when not applicable."""

    if not isinstance(event, Mapping):
        return None

    contexts = _collect_contexts(event)
    if not _is_status_change(contexts):
        return None

    status_name = _find_status_name(contexts)
    if _normalize(status_name) != TARGET_STATUS:
        return None

    issue_id = _clean_string(_first_value(contexts, ("id", "issueId", "issue_id", "identifier", "key")))
    title = _clean_string(_first_value(contexts, ("title", "name")))
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _collect_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect likely payload layers from most issue-specific to broadest."""

    trigger_context = _mapping_value(event.get("triggerContext"))
    data = _mapping_value(event.get("data"))
    issue = _mapping_value(event.get("issue"))
    data_issue = _mapping_value(data.get("issue")) if data else None
    node = _mapping_value(event.get("node"))

    contexts: list[Mapping[str, Any]] = []
    for candidate in (data_issue, issue, node, data, trigger_context, event):
        if candidate is not None and candidate not in contexts:
            contexts.append(candidate)
    return contexts


def _is_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    """Return whether the event represents a status/state transition."""

    trigger_values = []
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            value = _clean_string(context.get(key))
            if value:
                trigger_values.append(_normalize(value))

    if any(value in {"status changed", "status change", "status updated"} for value in trigger_values):
        return True

    # Linear's generic issue update webhooks need an updated field to confirm
    # this is a status/state transition rather than an unrelated issue edit.
    has_issue_update = any(value in {"issue updated", "updated issue", "update", "issue"} for value in trigger_values)
    return has_issue_update and _updated_fields_include_status(contexts)


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields"):
            fields = context.get(key)
            if isinstance(fields, str):
                fields = [fields]
            if isinstance(fields, list) or isinstance(fields, tuple):
                for field in fields:
                    if _status_field_matches(field):
                        return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            for field in changes:
                if _status_field_matches(field):
                    return True

        updated_from = context.get("updatedFrom")
        if isinstance(updated_from, Mapping):
            for field in updated_from:
                if _status_field_matches(field):
                    return True

    return False


def _find_status_name(contexts: list[Mapping[str, Any]]) -> str | None:
    """Find the new status name, prioritizing explicit new-status fields."""

    for key in _NEW_STATUS_KEYS:
        value = _first_value(contexts, (key,))
        status_name = _status_name(value)
        if status_name:
            return status_name

    changes_status = _status_from_changes(contexts)
    if changes_status:
        return changes_status

    return None


def _status_from_changes(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        changes = context.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for field, change in changes.items():
            if not _status_field_matches(field):
                continue
            if isinstance(change, Mapping):
                for key in ("newValue", "new_value", "to", "after", "name"):
                    status_name = _status_name(change.get(key))
                    if status_name:
                        return status_name
            else:
                status_name = _status_name(change)
                if status_name:
                    return status_name

    return None


def _first_value(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> Any:
    for context in contexts:
        for key in keys:
            if key in context:
                return context[key]
    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            status_name = _clean_string(value.get(key))
            if status_name:
                return status_name
        return None

    return _clean_string(value)


def _status_field_matches(field: Any) -> bool:
    normalized = _normalize(_clean_string(field))
    return normalized in {_normalize(field_name) for field_name in _STATUS_FIELD_NAMES}


def _mapping_value(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _clean_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-.]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def main() -> int:
    """Read a JSON event from stdin and print the title update action."""

    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
