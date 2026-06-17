"""Build Linear issue title updates for Cursor research status transitions.

The module is intentionally side-effect free: callers pass a Linear automation
or webhook payload in and receive an action describing the title update to make.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
PREFIXED_TITLE_FORMAT = f"{PREFIX}: {{title}}"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELDS = {"status", "state", "workflowstate", "workflowstatus"}
_DIRECT_STATUS_TRIGGERS = {"statuschanged", "statusupdate", "statusupdated"}
_ISSUE_UPDATE_TRIGGERS = {
    "issueupdated",
    "updatedissue",
    "update",
    "updated",
    "issueupdate",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    payload = _payload(event)
    if not _is_status_change_event(payload):
        return None

    if _normalize_text(_new_status(payload)) != _normalize_text(TARGET_STATUS):
        return None

    issue_id = _issue_id(payload)
    title = _issue_title(payload)
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": PREFIXED_TITLE_FORMAT.format(title=title),
    }


def _payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Cursor automation and Linear webhook shapes."""
    payload: dict[str, Any] = {}

    for key in ("data", "issue"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            payload.update(nested)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            payload.update(issue)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        payload.update(trigger_context)

    # Top-level trigger metadata should win over nested issue data.
    payload.update(event)
    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = (
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    )
    normalized_triggers = {_normalize_text(value) for value in trigger_values if value}

    if normalized_triggers & _DIRECT_STATUS_TRIGGERS:
        return True

    if normalized_triggers & _ISSUE_UPDATE_TRIGGERS:
        return _status_was_updated(payload)

    return False


def _status_was_updated(payload: Mapping[str, Any]) -> bool:
    updated_fields = payload.get("updatedFields")
    if isinstance(updated_fields, Sequence) and not isinstance(updated_fields, (str, bytes)):
        if any(_is_status_field(field) for field in updated_fields):
            return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        return any(_is_status_field(field) for field in changes)

    if isinstance(changes, Sequence) and not isinstance(changes, (str, bytes)):
        for change in changes:
            if isinstance(change, Mapping):
                field = change.get("field") or change.get("name") or change.get("key")
                if _is_status_field(field):
                    return True

    return False


def _new_status(payload: Mapping[str, Any]) -> Any:
    for key in ("newStatus", "new_status", "toStatus", "statusName", "stateName"):
        value = payload.get(key)
        if value:
            return _name(value)

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        for field, change in changes.items():
            if _is_status_field(field):
                if isinstance(change, Mapping):
                    return _name(
                        change.get("newValue")
                        or change.get("new")
                        or change.get("to")
                        or change.get("after")
                    )
                return _name(change)

    if isinstance(changes, Sequence) and not isinstance(changes, (str, bytes)):
        for change in changes:
            if not isinstance(change, Mapping):
                continue
            field = change.get("field") or change.get("name") or change.get("key")
            if _is_status_field(field):
                return _name(
                    change.get("newValue")
                    or change.get("new")
                    or change.get("to")
                    or change.get("after")
                )

    for key in ("status", "state", "workflowState"):
        value = payload.get(key)
        if value:
            return _name(value)

    return None


def _issue_id(payload: Mapping[str, Any]) -> str | None:
    # Prefer human-readable Linear identifiers over UUID-style ids when present.
    for key in ("identifier", "key", "issueId", "issue_id", "id"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _issue_title(payload: Mapping[str, Any]) -> str | None:
    value = payload.get("title")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _name(value: Any) -> Any:
    if isinstance(value, Mapping):
        return value.get("name") or value.get("title") or value.get("label")
    return value


def _is_status_field(field: Any) -> bool:
    return _normalize_text(field) in _STATUS_FIELDS


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split()).replace(" ", "")


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
