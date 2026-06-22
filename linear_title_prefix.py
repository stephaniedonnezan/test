"""Build Linear issue title updates for Cursor automation events.

The automation that calls this module can pass either Cursor's flat
``triggerContext`` payload or a nested Linear webhook payload on stdin. When an
issue moves to "to research", the module emits a small action object instructing
the caller to prefix the issue title with "Cursor researching".
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


CURSOR_RESEARCHING_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue enters "to research".

    The returned object is intentionally transport-agnostic so it can be handed
    to whatever automation layer performs the Linear API update.
    """

    context = _event_context(event)
    if not _is_linear_issue_event(context):
        return None
    if not _is_status_change(context):
        return None

    new_status = _new_status(context)
    if _normalize_status(new_status) != TARGET_STATUS:
        return None

    title = _issue_title(context)
    issue_id = _issue_id(context)
    if not title or not issue_id:
        return None
    if _has_cursor_researching_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{CURSOR_RESEARCHING_PREFIX}: {title}",
    }


def _event_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    """Accept a full automation payload or the nested trigger context directly."""

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context
    return event


def _is_linear_issue_event(event: Mapping[str, Any]) -> bool:
    trigger_type = _normalize_token(event.get("triggerType"))
    webhook_type = _normalize_token(event.get("webhookType"))
    linear_type = _normalize_token(event.get("type"))
    data_type = _normalize_token(_nested_get(event, "data", "type"))

    # Cursor trigger contexts identify Linear issue events explicitly. Linear's
    # native webhook payloads often use only type/data.type.
    if trigger_type and trigger_type != "linear":
        return False
    if webhook_type and webhook_type != "issue":
        return False
    if linear_type and linear_type not in {"issue", "issueupdate"}:
        return False
    if data_type and data_type != "issue":
        return False
    return True


def _is_status_change(event: Mapping[str, Any]) -> bool:
    trigger = _normalize_token(event.get("trigger"))
    if trigger in {"statuschanged", "statuschange", "statechanged", "statechange"}:
        return True

    changed_fields = event.get("updatedFields")
    if _contains_status_field(changed_fields):
        return True

    changes = event.get("changes")
    if isinstance(changes, Mapping) and any(
        _is_status_field(field) for field in changes.keys()
    ):
        return True

    updated_from = event.get("updatedFrom")
    if isinstance(updated_from, Mapping) and any(
        _is_status_field(field) for field in updated_from.keys()
    ):
        return True

    # Cursor trigger contexts include newStatus only for status transitions.
    return _new_status(event) is not None and _old_status(event) is not None


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Iterable) and not isinstance(value, (bytes, Mapping)):
        return any(_is_status_field(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    token = _normalize_token(value)
    return token in {
        "state",
        "stateid",
        "status",
        "statusid",
        "workflowstate",
        "workflowstateid",
    }


def _new_status(event: Mapping[str, Any]) -> Any:
    for path in (
        ("newStatus",),
        ("newState",),
        ("status",),
        ("state",),
        ("data", "state", "name"),
        ("data", "status", "name"),
        ("data", "state"),
        ("data", "status"),
        ("issue", "state", "name"),
        ("issue", "status", "name"),
        ("issue", "state"),
        ("issue", "status"),
    ):
        value = _nested_get(event, *path)
        if value is not None:
            return value

    changes = event.get("changes")
    if isinstance(changes, Mapping):
        for key in ("state", "stateId", "status", "statusId"):
            value = _change_new_value(changes.get(key))
            if value is not None:
                return value

    return None


def _old_status(event: Mapping[str, Any]) -> Any:
    for path in (("oldStatus",), ("previousStatus",), ("oldState",), ("previousState",)):
        value = _nested_get(event, *path)
        if value is not None:
            return value
    return None


def _issue_title(event: Mapping[str, Any]) -> str | None:
    for path in (("title",), ("data", "title"), ("issue", "title")):
        value = _nested_get(event, *path)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _issue_id(event: Mapping[str, Any]) -> str | None:
    for path in (
        ("id",),
        ("issueId",),
        ("identifier",),
        ("data", "identifier"),
        ("data", "id"),
        ("issue", "identifier"),
        ("issue", "id"),
    ):
        value = _nested_get(event, *path)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _change_new_value(change: Any) -> Any:
    if isinstance(change, Mapping):
        for key in ("to", "new", "newValue", "after", "name"):
            if key in change:
                return change[key]
    return change


def _nested_get(mapping: Mapping[str, Any], *path: str) -> Any:
    value: Any = mapping
    for key in path:
        if not isinstance(value, Mapping) or key not in value:
            return None
        value = value[key]
    return value


def _has_cursor_researching_prefix(title: str) -> bool:
    return re.match(r"^\s*cursor\s+researching\b", title, re.IGNORECASE) is not None


def _normalize_status(value: Any) -> str:
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state"):
            if key in value:
                return _normalize_status(value[key])
        return ""

    text = str(value or "")
    text = re.sub(r"[_\-.\/]+", " ", text)
    return " ".join(text.casefold().split())


def _normalize_token(value: Any) -> str:
    text = str(value or "")
    return re.sub(r"[^a-z0-9]+", "", text.casefold())


def main() -> int:
    payload = json.load(sys.stdin)
    if not isinstance(payload, Mapping):
        raise TypeError("Expected a JSON object payload")

    update = build_issue_title_update(payload)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
