"""Build Linear issue title updates for issues entering research."""

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
    """Return a title update action when a Linear issue moves to research.

    The automation trigger can provide a flat ``triggerContext`` payload or a
    nested Linear webhook-style payload. This function accepts both shapes and
    returns a small action object for the caller to apply through the Linear API.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change(payload):
        return None

    status = _extract_new_status(payload)
    if _normalize(status) != _normalize(TARGET_STATUS):
        return None

    issue_id = _first_string(payload, ("id", "issueId", "issue_id", "identifier"))
    title = _first_string(payload, ("title", "name"))
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


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Linear automation nesting levels into one lookup dict."""

    payload: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if not isinstance(value, Mapping):
            return

        # Preserve nested issue data while allowing outer trigger metadata such
        # as ``newStatus`` to override stale nested status values.
        for nested_key in ("issue", "data", "triggerContext"):
            nested = value.get(nested_key)
            if isinstance(nested, Mapping):
                merge(nested)

        for key, item in value.items():
            payload[key] = item

    merge(event)
    return payload


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    event_markers = [
        payload.get(key)
        for key in ("trigger", "webhookType", "action", "type")
        if key in payload
    ]
    normalized_markers = {_normalize(marker) for marker in event_markers}

    if any(marker in {"status changed", "status change", "statuschanged"} for marker in normalized_markers):
        return True

    if any(marker in {"issue updated", "updated issue", "update", "updated"} for marker in normalized_markers):
        return _updated_fields_include_status(payload)

    return False


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    updated_fields = payload.get("updatedFields") or payload.get("updated_fields")

    if isinstance(updated_fields, str):
        candidates = re.split(r"[\s,;]+", updated_fields)
    elif isinstance(updated_fields, Mapping):
        candidates = updated_fields.keys()
    elif isinstance(updated_fields, list | tuple | set):
        candidates = updated_fields
    else:
        return False

    return any(_normalize_field_name(field) in STATUS_FIELDS for field in candidates)


def _extract_new_status(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "status_name"):
        value = _string_or_name(payload.get(key))
        if value:
            return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _string_or_name(payload.get(key))
        if value:
            return value

    return None


def _first_string(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _string_or_name(payload.get(key))
        if value:
            return value
    return None


def _string_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        for key in ("name", "title"):
            nested = _string_or_name(value.get(key))
            if nested:
                return nested
    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = text.replace("_", " ").replace("-", " ")
    return " ".join(text.strip().lower().split())


def _normalize_field_name(value: Any) -> str:
    return _normalize(value).replace(" ", "")


def main() -> int:
    """Read a JSON event from stdin and print the resulting action, if any."""

    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
