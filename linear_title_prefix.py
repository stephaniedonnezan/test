"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TITLE_SEPARATOR = ": "
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change_event(payload):
        return None

    if _normalize(_new_status(payload)) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(payload, ("title", "name"))
    if issue_id is None or title is None:
        return None

    title = title.strip()
    issue_id = issue_id.strip()
    if not title or not issue_id or _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}{TITLE_SEPARATOR}{title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor automation and Linear webhook wrappers."""
    payload: dict[str, Any] = {}

    # Start with deeply nested issue data, then let outer trigger metadata win.
    for source in _payload_layers(event):
        payload.update(source)

    return payload


def _payload_layers(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    for key in ("data", "issue"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            yield from _payload_layers(nested)
            yield nested

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        for key in ("data", "issue"):
            nested = trigger_context.get(key)
            if isinstance(nested, Mapping):
                yield from _payload_layers(nested)
                yield nested
        yield trigger_context

    yield event


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    for value in _event_markers(payload):
        normalized = _normalize(value)
        if normalized in {"status changed", "status change", "state changed"}:
            return True
        if "status changed" in normalized or "state changed" in normalized:
            return True

    action = _normalize(payload.get("action"))
    if action in {"update", "updated", "issue updated", "updated issue"}:
        return _updated_fields_include_status(payload)

    return False


def _event_markers(payload: Mapping[str, Any]) -> Iterable[Any]:
    for key in ("trigger", "event", "eventType", "webhookType", "type", "action"):
        yield payload.get(key)


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    status_fields = {"status", "state", "workflow state", "workflowstate", "state id"}

    updated_fields = payload.get("updatedFields")
    if isinstance(updated_fields, str):
        return _normalize(updated_fields) in status_fields

    if isinstance(updated_fields, Mapping):
        return any(_normalize(key) in status_fields for key in updated_fields)

    if isinstance(updated_fields, list | tuple | set):
        return any(_normalize(field) in status_fields for field in updated_fields)

    updated_from = payload.get("updatedFrom")
    if isinstance(updated_from, Mapping):
        return any(_normalize(key) in status_fields for key in updated_from)

    return False


def _new_status(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "status"):
        value = _first_text(payload, (key,))
        if value is not None:
            return value

    for key in ("state", "workflowState"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            name = _first_text(value, ("name", "title"))
            if name is not None:
                return name
        elif isinstance(value, str):
            return value

    return None


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_title_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"[_\-/]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip().lower()


def main() -> int:
    """Read a JSON payload from stdin and print the requested update, if any."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
