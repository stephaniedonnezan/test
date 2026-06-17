"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_WORD = re.compile(r"[^A-Za-z0-9]+")

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflow status",
    "workflow state",
}

_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type")
_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "status",
    "state",
    "workflowState",
    "workflow_status",
)
_ISSUE_ID_KEYS = ("identifier", "issueId", "issue_id", "key", "id")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    payload = _merge_payload(event)
    if not _is_status_change_event(payload):
        return None

    status = _extract_new_status(payload)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _extract_text(payload, _ISSUE_ID_KEYS)
    title = _extract_text(payload, ("title",))
    if not issue_id or not title:
        return None

    if _title_has_prefix(title):
        new_title = title
    else:
        new_title = f"{TITLE_PREFIX}: {title}"

    return {"action": UPDATE_ACTION, "issueId": issue_id, "title": new_title}


def _merge_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Cursor and Linear webhook envelopes without losing metadata."""
    payload: dict[str, Any] = {}

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        payload.update(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            payload.update(issue)
        payload.update({key: value for key, value in data.items() if key != "issue"})

    payload.update(event)

    if isinstance(trigger_context, Mapping):
        payload.update(trigger_context)

    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            # Prefer Linear's human-readable issue identifier over UUID-like ids.
            for key, value in issue.items():
                if key != "id" or "id" not in payload:
                    payload.setdefault(key, value)
            if issue.get("identifier"):
                payload["identifier"] = issue["identifier"]
            if issue.get("title"):
                payload["title"] = issue["title"]
            if issue.get("state") and "state" not in payload:
                payload["state"] = issue["state"]
            if issue.get("workflowState") and "workflowState" not in payload:
                payload["workflowState"] = issue["workflowState"]

    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        value
        for key in _TRIGGER_KEYS
        for value in _iter_values(payload.get(key))
        if value is not None
    ]
    normalized_triggers = {_normalize(value) for value in trigger_values}

    if any(value in {"status changed", "status change", "state changed"} for value in normalized_triggers):
        return True

    generic_update = any(
        value in {"update", "updated", "issue updated", "updated issue"} for value in normalized_triggers
    )
    if generic_update:
        return _changed_fields_include_status(payload)

    return False


def _changed_fields_include_status(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        for value in _iter_values(payload.get(key)):
            if _normalize(value) in _STATUS_FIELD_NAMES:
                return True

    changes = payload.get("changes") or payload.get("updatedFrom")
    if isinstance(changes, Mapping):
        return any(_normalize(key) in _STATUS_FIELD_NAMES for key in changes)

    return False


def _extract_new_status(payload: Mapping[str, Any]) -> str | None:
    for key in _STATUS_KEYS:
        value = payload.get(key)
        status = _status_text(value)
        if status:
            return status

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _normalize(key) not in _STATUS_FIELD_NAMES:
                continue

            if isinstance(value, Mapping):
                status = _status_text(value.get("to") or value.get("new") or value.get("newValue"))
            else:
                status = _status_text(value)
            if status:
                return status

    return None


def _extract_text(payload: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        if isinstance(value, Mapping):
            value = value.get("name") or value.get("title") or value.get("identifier")
        text = str(value).strip()
        if text:
            return text
    return None


def _status_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state", "workflowState"):
            text = _status_text(value.get(key))
            if text:
                return text
        return None
    text = str(value).strip()
    return text or None


def _iter_values(value: Any) -> Iterable[Any]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Mapping):
        return value.keys()
    if isinstance(value, Iterable):
        return value
    return (value,)


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    text = _CAMEL_BOUNDARY.sub(" ", str(value).strip())
    text = _NON_WORD.sub(" ", text)
    return " ".join(text.lower().split())


def _title_has_prefix(title: str) -> bool:
    return _normalize(title).startswith(_normalize(TITLE_PREFIX))


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
