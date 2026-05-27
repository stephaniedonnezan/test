"""Build Linear issue title updates for Cursor research-status automations.

The automation runner can feed this module either a flat Cursor trigger context
or a nested Linear webhook payload.  The public helper returns a small action
object that the caller can translate into the actual Linear title update.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
STATUS_CHANGED_TOKENS = {
    "statuschanged",
    "statuschange",
    "statusupdated",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}
UPDATE_TOKENS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research.

    The function is intentionally side-effect free so the automation runner can
    decide how to apply the returned action.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _coerce_payload(event)
    if not _is_status_change(payload):
        return None

    new_status = _first_text(
        payload.get("newStatus"),
        payload.get("new_status"),
        payload.get("statusName"),
        payload.get("status_name"),
        _nested_name(payload.get("status")),
        _nested_name(payload.get("state")),
        _nested_name(payload.get("workflowState")),
        _nested_name(payload.get("workflow_state")),
        payload.get("status"),
    )
    if _normalize(new_status) != _normalize(TARGET_STATUS):
        return None

    title = _first_text(payload.get("title"), _nested_value(payload.get("issue"), "title"))
    issue_id = _first_text(
        payload.get("issueId"),
        payload.get("issue_id"),
        payload.get("id"),
        payload.get("identifier"),
        _nested_value(payload.get("issue"), "id"),
        _nested_value(payload.get("issue"), "identifier"),
    )
    if not title or not issue_id:
        return None

    title = title.strip()
    if not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _coerce_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common wrapper shapes into a flat payload without losing metadata."""

    payload: dict[str, Any] = {}
    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            payload.update(value)
    payload.update(event)
    return payload


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    ]
    tokens = {_normalize(value) for value in trigger_values if _first_text(value)}

    if tokens & STATUS_CHANGED_TOKENS:
        return True

    if tokens & UPDATE_TOKENS:
        return _mentions_status_field(payload)

    return False


def _mentions_status_field(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if _field_list_mentions_status(payload.get(key)):
            return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize(key) in STATUS_FIELDS for key in changes)

    return False


def _field_list_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize(value) in STATUS_FIELDS

    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, Mapping)):
        return any(_normalize(item) in STATUS_FIELDS for item in value)

    return False


def _first_text(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value
    return None


def _nested_name(value: Any) -> str | None:
    return _nested_value(value, "name")


def _nested_value(value: Any, key: str) -> str | None:
    if isinstance(value, Mapping):
        nested = value.get(key)
        if isinstance(nested, str) and nested.strip():
            return nested
    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize(value: Any) -> str:
    text = _first_text(value)
    if text is None:
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text.strip())
    return re.sub(r"[^a-z0-9]+", "", spaced.lower())


def main() -> int:
    """Read a JSON event from stdin and print the requested title action."""

    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
