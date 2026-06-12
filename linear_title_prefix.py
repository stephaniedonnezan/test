"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELD_NAMES = frozenset(("status", "state", "workflowstate", "workflow_status"))


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue title update when a Linear issue moves to research.

    The function accepts Cursor automation trigger payloads as well as common
    Linear webhook shapes. It does not call Linear itself; callers can execute
    the returned action with their own API client.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _merged_payload(event)
    if not _is_status_change(payload):
        return None

    status = _extract_new_status(payload)
    if _normalize_text(status) != _normalize_text(RESEARCH_STATUS):
        return None

    issue_id = _first_text(payload, "id", "issueId", "issue_id", "identifier", "key")
    title = _first_text(payload, "title", "name")
    if issue_id is None or title is None:
        return None

    if title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _merged_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge likely nested Linear issue data with outer trigger metadata."""

    merged: dict[str, Any] = {}
    for path in (
        ("data", "issue"),
        ("data",),
        ("issue",),
        ("triggerContext",),
    ):
        nested = _get_mapping(event, path)
        if nested is not None:
            merged.update(nested)

    merged.update(event)
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        merged.update(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            for key in ("id", "identifier", "title", "name"):
                if key not in merged and key in issue:
                    merged[key] = issue[key]

    return merged


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    event_names = tuple(_event_names(payload))
    if any(name in {"statuschanged", "statuschange", "statuschanged"} for name in event_names):
        return True
    if any("statuschanged" in name or "statuschange" in name for name in event_names):
        return True

    if any(name in {"issueupdated", "updatedissue", "update", "updated"} for name in event_names):
        return _has_status_update_marker(payload)

    return _has_status_update_marker(payload) and _extract_new_status(payload) is not None


def _event_names(payload: Mapping[str, Any]) -> list[str]:
    names: list[str] = []
    for key in ("trigger", "webhookType", "action", "type", "eventType"):
        value = payload.get(key)
        if isinstance(value, str):
            names.append(_normalize_text(value))
    return names


def _has_status_update_marker(payload: Mapping[str, Any]) -> bool:
    updated_fields = payload.get("updatedFields")
    if isinstance(updated_fields, str):
        updated_fields = [updated_fields]
    if isinstance(updated_fields, list) and any(_is_status_field(field) for field in updated_fields):
        return True

    for key in ("changes", "updated", "changed", "previousValues"):
        changes = payload.get(key)
        if isinstance(changes, Mapping) and any(_is_status_field(field) for field in changes):
            return True

    return False


def _extract_new_status(payload: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "statusName",
        "stateName",
        "workflowStateName",
        "toStatus",
        "to_status",
    ):
        value = _string_or_named_value(payload.get(key))
        if value is not None:
            return value

    for container_key in ("changes", "updated", "changed"):
        changes = payload.get(container_key)
        if isinstance(changes, Mapping):
            for field, change in changes.items():
                if _is_status_field(field):
                    value = _change_new_value(change)
                    if value is not None:
                        return value

    for key in ("status", "state", "workflowState", "workflow_status"):
        value = _string_or_named_value(payload.get(key))
        if value is not None:
            return value

    return None


def _change_new_value(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("newValue", "new_value", "to", "after", "new", "name"):
            value = _string_or_named_value(change.get(key))
            if value is not None:
                return value
    return _string_or_named_value(change)


def _string_or_named_value(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()
    return None


def _first_text(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _get_mapping(payload: Mapping[str, Any], path: tuple[str, ...]) -> Mapping[str, Any] | None:
    value: Any = payload
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value if isinstance(value, Mapping) else None


def _is_status_field(field: Any) -> bool:
    return isinstance(field, str) and _normalize_text(field) in STATUS_FIELD_NAMES


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
