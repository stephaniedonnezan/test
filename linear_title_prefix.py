"""Build Linear issue title updates for research status changes.

The module is intentionally small and dependency-free so it can be used as a
JSON-in/JSON-out step by webhook automations.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "status update",
    "status updated",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue enters research."""

    if not _is_status_change_event(event):
        return None

    status = _new_status(event)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_value(event, ("id", "issueId", "identifier"))
    title = _first_value(event, ("title", "name"))
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    for context in _candidate_contexts(event):
        triggers = {
            _normalize(value)
            for value in _direct_values(
                context,
                ("trigger", "type", "webhookType", "action"),
            )
        }
        if triggers & STATUS_CHANGE_TRIGGERS:
            return True

        if _status_changed(context):
            return True

    return False


def _new_status(event: Mapping[str, Any]) -> str | None:
    for context in _candidate_contexts(event):
        status = _first_direct_value(
            context,
            ("newStatus", "status", "state", "workflowState"),
        )
        if isinstance(status, Mapping):
            status = _first_direct_value(status, ("name", "title", "label"))
        if status:
            return str(status)

        changes = _get_value(context, ("changes",))
        if isinstance(changes, Mapping):
            for key in ("status", "state", "workflowState"):
                change = changes.get(key)
                if isinstance(change, Mapping):
                    changed_to = _first_direct_value(
                        change,
                        ("newValue", "to", "toValue"),
                    )
                    if isinstance(changed_to, Mapping):
                        changed_to = _first_direct_value(
                            changed_to,
                            ("name", "title", "label"),
                        )
                    if changed_to:
                        return str(changed_to)
                elif change:
                    return str(change)

        issue_state = _get_value(context, ("issue", "state"))
        if isinstance(issue_state, Mapping):
            state_name = _first_direct_value(issue_state, ("name", "title", "label"))
            if state_name:
                return str(state_name)

    return None


def _first_value(event: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for context in _candidate_contexts(event):
        value = _first_direct_value(context, keys)
        if value:
            return str(value)
    return None


def _candidate_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    yield event

    for path in (
        ("triggerContext",),
        ("data",),
        ("data", "issue"),
        ("issue",),
        ("payload",),
        ("payload", "issue"),
    ):
        value = _get_value(event, path)
        if isinstance(value, Mapping):
            yield value


def _status_changed(context: Mapping[str, Any]) -> bool:
    changes = _get_value(context, ("changes",))
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState"):
            if key in changes:
                return True

    updated_from = _get_value(context, ("updatedFrom",))
    if isinstance(updated_from, Mapping):
        for key in ("status", "state", "workflowState"):
            if key in updated_from:
                return True

    return False


def _get_value(context: Mapping[str, Any], keys: Iterable[str]) -> Any:
    current: Any = context
    for key in keys:
        if not isinstance(current, Mapping) or key not in current:
            return None
        current = current[key]
    return current


def _first_direct_value(context: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in context:
            return context[key]
    return None


def _direct_values(context: Mapping[str, Any], keys: Iterable[str]) -> Iterable[Any]:
    for key in keys:
        if key in context:
            yield context[key]


def _normalize(value: Any) -> str | None:
    if value is None:
        return None
    words = re.sub(r"[_-]+", " ", str(value)).strip().lower()
    return re.sub(r"\s+", " ", words)


def _has_prefix(title: str) -> bool:
    return _normalize(title).startswith(_normalize(PREFIX))


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
