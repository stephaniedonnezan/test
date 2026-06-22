"""Build title update actions for Linear issues moving to research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research.

    The Cursor automation payload is usually a flat ``triggerContext`` object,
    while Linear webhooks commonly nest issue data under ``data`` or ``issue``.
    This function accepts both shapes and returns a side-effect-free action for
    the caller to apply through its Linear client.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change_event(payload):
        return None

    new_status = _new_status(payload)
    if _normalize_label(new_status) != _normalize_label(TARGET_STATUS):
        return None

    issue_id = _first_text(payload, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(payload, ("title", "name"))
    if issue_id is None or title is None:
        return None

    trimmed_title = title.strip()
    if not trimmed_title or _has_prefix(trimmed_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {trimmed_title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge useful nested Linear/Cursor payload levels into one dictionary."""

    payload: dict[str, Any] = {}
    for path in (
        ("data", "issue"),
        ("issue",),
        ("data",),
        ("triggerContext",),
        ("trigger_context",),
        (),
    ):
        nested = _get_path(event, path)
        if isinstance(nested, Mapping):
            payload.update(nested)

    return payload


def _get_path(value: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = value
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_names = [
        text
        for key in ("trigger", "webhookType", "webhook_type", "action", "type")
        if (text := _text(payload.get(key))) is not None
    ]

    if any(_is_direct_status_change_name(name) for name in event_names):
        return True

    if any(_is_issue_update_name(name) for name in event_names):
        return _mentions_status_field(payload)

    return False


def _is_direct_status_change_name(value: str) -> bool:
    normalized = _normalize_label(value)
    return normalized in {
        "status changed",
        "status change",
        "state changed",
        "state change",
        "workflow state changed",
        "workflow state change",
    }


def _is_issue_update_name(value: str) -> bool:
    return _normalize_label(value) in {
        "update",
        "updated",
        "issue update",
        "issue updated",
        "updated issue",
    }


def _mentions_status_field(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields"):
        if _contains_status_field(payload.get(key)):
            return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        return any(_field_name_is_status(key) for key in changes)

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _field_name_is_status(value)
    if isinstance(value, Mapping):
        return any(_field_name_is_status(key) for key in value)
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _field_name_is_status(value: Any) -> bool:
    text = _text(value)
    if text is None:
        return False
    return _normalize_key(text) in STATUS_FIELDS


def _new_status(payload: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "status",
        "state",
        "workflowState",
        "workflow_state",
    ):
        value = payload.get(key)
        if isinstance(value, Mapping):
            value = value.get("name") or value.get("title") or value.get("key")
        if (text := _text(value)) is not None:
            return text

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if not _field_name_is_status(key):
                continue
            if isinstance(value, Mapping):
                for nested_key in ("to", "new", "after"):
                    nested_value = value.get(nested_key)
                    if isinstance(nested_value, Mapping):
                        nested_value = nested_value.get("name")
                    if (text := _text(nested_value)) is not None:
                        return text
            if (text := _text(value)) is not None:
                return text

    return None


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        if (text := _text(payload.get(key))) is not None:
            return text
    return None


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_label(value: str | None) -> str:
    if value is None:
        return ""
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", separated.casefold()).strip()


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _normalize_label(value))


def main() -> int:
    """Read a JSON event from stdin and print the requested title update."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is None:
        return 0

    print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
