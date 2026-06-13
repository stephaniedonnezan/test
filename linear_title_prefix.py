"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue enters To Research."""
    if not isinstance(event, Mapping):
        return None

    payload = _merge_payload(event)
    if not _is_status_change_event(payload):
        return None

    new_status = _first_text(
        payload,
        (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "status",
            "state",
            "workflowState",
            "workflow_state",
        ),
    )
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, ("id", "issueId", "issue_id", "identifier", "key"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        prefixed_title = title
    else:
        prefixed_title = f"{PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": prefixed_title,
    }


def _merge_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common automation and Linear webhook wrappers into one payload."""
    payload: dict[str, Any] = {}

    for key in ("triggerContext", "data", "issue"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            payload.update(_merge_payload(nested))

    if isinstance(event.get("data"), Mapping):
        issue = event["data"].get("issue")
        if isinstance(issue, Mapping):
            payload.update(_merge_payload(issue))

    payload.update(event)
    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_markers = _event_markers(payload)
    if any(marker in {"status changed", "status change", "statuschanged"} for marker in event_markers):
        return True

    if any(marker in {"issue updated", "updated issue", "update", "updated"} for marker in event_markers):
        return _mentions_status_field(payload.get("updatedFields")) or _mentions_status_field(
            payload.get("changes")
        )

    return False


def _event_markers(payload: Mapping[str, Any]) -> set[str]:
    markers: set[str] = set()
    for key in ("trigger", "webhookType", "action", "type"):
        value = payload.get(key)
        if isinstance(value, str):
            markers.add(_normalize_text(value))
    return markers


def _mentions_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_text(value) in STATUS_FIELDS

    if isinstance(value, Mapping):
        keys = {_normalize_text(str(key)) for key in value}
        if keys & STATUS_FIELDS:
            return True
        return any(_mentions_status_field(item) for item in value.values())

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_mentions_status_field(item) for item in value)

    return False


def _first_text(payload: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        value = payload.get(key)
        text = _text_value(value)
        if text:
            return text
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "id", "identifier"):
            text = _text_value(value.get(key))
            if text:
                return text

    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""

    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", value)
    return re.sub(r"[\W_]+", " ", spaced).strip().lower()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
