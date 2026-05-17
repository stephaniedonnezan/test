"""Build Linear issue title updates for research status changes.

The automation platform passes Linear webhook data in slightly different shapes
depending on the trigger source.  This module keeps the behavior pure and easy
to test: callers pass the event payload and receive either an update action or
``None`` when no title change is needed.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    The returned shape is intentionally small so the automation runner can map
    it to its Linear client call:
    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    if not _is_status_change_event(payload):
        return None

    status = _extract_new_status(payload)
    if _normalize_phrase(status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_string(payload, ("id", "issueId", "issue_id", "identifier"))
    title = _extract_first_string(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common nested Linear/automation payload containers.

    Nested issue data is applied first, then trigger metadata, then top-level
    values.  That gives explicit trigger fields such as ``newStatus`` priority
    over stale issue state values that can also appear in webhook payloads.
    """

    result: dict[str, Any] = {}

    def merge_mapping(value: Any) -> None:
        if isinstance(value, Mapping):
            result.update(value)

    for key in ("issue", "data", "node"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            for issue_key in ("issue", "data", "node"):
                merge_mapping(nested.get(issue_key))
            merge_mapping(nested)

    merge_mapping(event.get("triggerContext"))
    result.update(event)
    return result


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_markers = [
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    ]

    if any(_normalize_token(marker) in {"statuschanged", "statuschange"} for marker in event_markers):
        return True

    if any(_normalize_phrase(marker) in {"issue updated", "updated issue", "update"} for marker in event_markers):
        updated_fields = payload.get("updatedFields") or payload.get("updated_fields")
        if isinstance(updated_fields, str):
            updated_fields = [updated_fields]
        if isinstance(updated_fields, list):
            return any(_normalize_token(field) in STATUS_FIELDS for field in updated_fields)

    return False


def _extract_new_status(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "toStatus", "to_status"):
        value = _string_or_name(payload.get(key))
        if value:
            return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _string_or_name(payload.get(key))
        if value:
            return value

    return None


def _extract_first_string(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _string_or_name(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, Mapping):
        name = value.get("name")
        if isinstance(name, str) and name.strip():
            return name
    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_phrase(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    words = re.sub(r"[_\-\s]+", " ", words).strip().lower()
    return words or None


def _normalize_token(value: Any) -> str | None:
    phrase = _normalize_phrase(value)
    if phrase is None:
        return None
    return phrase.replace(" ", "")


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
