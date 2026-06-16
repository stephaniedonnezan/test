"""Build Linear issue title updates for research status transitions.

The Cursor automation trigger provides issue data in a few related shapes. This
module keeps the transformation small and deterministic: if an issue status
change moves to "to research", return the title update payload that adds the
Cursor research marker. Otherwise return ``None``.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
STATUS_TO_RESEARCH = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_status"}
STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statusupdated",
    "statusupdate",
}
GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    The returned dictionary is intentionally simple so the caller can map it to
    the Linear API call it uses in production.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    if not _is_status_change_event(payload):
        return None

    new_status = _extract_new_status(payload)
    if _normalize_label(new_status) != _normalize_label(STATUS_TO_RESEARCH):
        return None

    issue_id = _extract_text(payload, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _extract_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common nested payload locations without mutating the input."""

    flattened: dict[str, Any] = {}

    for path in (
        ("data", "issue"),
        ("issue",),
        ("data",),
        ("triggerContext",),
        (),
    ):
        value = _get_path(event, path)
        if isinstance(value, Mapping):
            flattened.update(value)

    # Keep nested objects available for status/name extraction after the merge.
    for key in ("state", "status", "workflowState"):
        value = _first_mapping_at(event, key)
        if value is not None and key not in flattened:
            flattened[key] = value

    return flattened


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    markers = _event_markers(payload)
    if any(marker in STATUS_CHANGE_TRIGGERS for marker in markers):
        return True

    updated_fields = _updated_fields(payload)
    if updated_fields and any(field in STATUS_FIELDS for field in updated_fields):
        return True

    # Some Cursor automation payloads contain only newStatus plus issue data.
    # Do not use this fallback when an explicit non-status marker is present.
    if not markers and _extract_new_status(payload) is not None and "newstatus" in {
        _normalize_key(key) for key in payload.keys()
    }:
        return True

    # Generic issue update events should only count when status/state changed.
    if any(marker in GENERIC_UPDATE_TRIGGERS for marker in markers):
        return bool(updated_fields and any(field in STATUS_FIELDS for field in updated_fields))

    return False


def _event_markers(payload: Mapping[str, Any]) -> set[str]:
    markers: set[str] = set()
    for key in ("trigger", "webhookType", "action", "type", "eventType"):
        value = payload.get(key)
        if isinstance(value, str):
            markers.add(_normalize_key(value))
    return markers


def _updated_fields(payload: Mapping[str, Any]) -> set[str]:
    values: set[str] = set()

    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        raw = payload.get(key)
        if isinstance(raw, str):
            values.add(_normalize_key(raw))
        elif isinstance(raw, list):
            values.update(_normalize_key(item) for item in raw if isinstance(item, str))

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        values.update(_normalize_key(key) for key in changes.keys() if isinstance(key, str))

    return values


def _extract_new_status(payload: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "status",
        "state",
        "workflowState",
    ):
        value = payload.get(key)
        text = _status_text(value)
        if text:
            return text
    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()
    return None


def _extract_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if value is not None and not isinstance(value, (Mapping, list, tuple, set)):
            text = str(value).strip()
            if text:
                return text
    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_label(value: str | None) -> str | None:
    if value is None:
        return None
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return " ".join(re.split(r"[\s_-]+", spaced.strip().casefold()))


def _normalize_key(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _get_path(mapping: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = mapping
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _first_mapping_at(value: Any, key: str) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    nested = value.get(key)
    if isinstance(nested, Mapping):
        return nested
    for child in value.values():
        found = _first_mapping_at(child, key)
        if found is not None:
            return found
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    result = build_issue_title_update(event)
    print(json.dumps(result, sort_keys=True) if result is not None else "null")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
