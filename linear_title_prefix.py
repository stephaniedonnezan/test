"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
STATUS_CHANGE_TRIGGERS = {"statuschanged", "statuschange", "statusupdated", "statusupdate"}
GENERIC_UPDATE_TRIGGERS = {"update", "updated", "issueupdated", "updatedissue", "issueupdate"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    context = _collect_context(event)
    if not _is_status_change_event(context):
        return None

    status = _new_status(context)
    if _normalize_text(status) != _normalize_text(TARGET_STATUS):
        return None

    issue_id = _first_text(context, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(context, ("title", "name"))
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        prefixed_title = title
    else:
        prefixed_title = f"{PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": prefixed_title,
    }


def _collect_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor and Linear payload locations into a flat lookup context."""

    context: dict[str, Any] = {}
    for path in (
        ("data", "issue"),
        ("issue",),
        ("triggerContext", "issue"),
        ("triggerContext",),
        ("data",),
        (),
    ):
        value = _get_path(event, path)
        if isinstance(value, Mapping):
            context.update(value)
    return context


def _get_path(value: Mapping[str, Any], path: Sequence[str]) -> Any:
    current: Any = value
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    triggers = [
        _normalize_text(value)
        for key in ("trigger", "webhookType", "action", "type", "eventType")
        if (value := context.get(key)) is not None
    ]
    if any(trigger in STATUS_CHANGE_TRIGGERS for trigger in triggers):
        return True
    if any(trigger in GENERIC_UPDATE_TRIGGERS for trigger in triggers):
        return _updated_fields_include_status(context) or _changes_include_status(context)
    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields") or context.get("updated_fields")
    if isinstance(updated_fields, str):
        updated_fields = [updated_fields]
    if not isinstance(updated_fields, Sequence) or isinstance(updated_fields, (bytes, bytearray)):
        return False
    return any(_normalize_field_name(field) in STATUS_FIELDS for field in updated_fields)


def _changes_include_status(context: Mapping[str, Any]) -> bool:
    changes = context.get("changes") or context.get("updated")
    if not isinstance(changes, Mapping):
        return False
    return any(_normalize_field_name(field) in STATUS_FIELDS for field in changes)


def _new_status(context: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "status_name"):
        text = _as_text(context.get(key))
        if text:
            return text

    for key in ("status", "state", "workflowState", "workflow_state"):
        text = _status_text(context.get(key))
        if text:
            return text

    changes = context.get("changes") or context.get("updated")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = changes.get(key)
            if isinstance(value, Mapping):
                text = _status_text(value.get("to") or value.get("new") or value.get("after"))
            else:
                text = _status_text(value)
            if text:
                return text

    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _first_text(value, ("name", "label", "title", "status"))
    return _as_text(value)


def _first_text(context: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        text = _as_text(context.get(key))
        if text:
            return text
    return None


def _as_text(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", value)
    return re.sub(r"[^a-z0-9]+", "", spaced.lower())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
