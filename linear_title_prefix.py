"""Build title update actions for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"

_STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}
_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_ISSUE_UPDATE_TRIGGERS = {
    "issue updated",
    "updated issue",
    "update",
    "updated",
}


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change(payload):
        return None

    if _normalize(_new_status(payload)) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(payload, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(payload, ("title", "issueTitle", "issue_title"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Linear automation nesting layers into one lookup mapping."""
    nested_issue = _mapping_at(event, "issue")
    data = _mapping_at(event, "data")
    data_issue = _mapping_at(data, "issue") if data else {}
    trigger_context = _mapping_at(event, "triggerContext")

    payload: dict[str, Any] = {}
    for layer in (nested_issue, data_issue, data, trigger_context, event):
        payload.update(layer)

    if "state" not in payload:
        payload["state"] = _first_mapping_value(
            nested_issue,
            data_issue,
            data,
            trigger_context,
            event,
            key="state",
        )
    if "workflowState" not in payload:
        payload["workflowState"] = _first_mapping_value(
            nested_issue,
            data_issue,
            data,
            trigger_context,
            event,
            key="workflowState",
        )

    return payload


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    event_markers = (
        payload.get("trigger"),
        payload.get("action"),
        payload.get("type"),
        payload.get("webhookType"),
    )
    normalized_markers = {_normalize(marker) for marker in event_markers if marker}

    if normalized_markers & _STATUS_CHANGE_TRIGGERS:
        return True

    if normalized_markers & _ISSUE_UPDATE_TRIGGERS:
        updated_fields = _updated_fields(payload.get("updatedFields"))
        return bool(updated_fields & _STATUS_FIELDS)

    return False


def _new_status(payload: Mapping[str, Any]) -> Any:
    for key in ("newStatus", "new_status", "status"):
        if _has_text(payload.get(key)):
            return payload[key]

    for key in ("state", "workflowState"):
        status = _name_from_mapping(payload.get(key))
        if status:
            return status

    return None


def _mapping_at(mapping: Mapping[str, Any] | None, key: str) -> dict[str, Any]:
    if not isinstance(mapping, Mapping):
        return {}

    value = mapping.get(key)
    return dict(value) if isinstance(value, Mapping) else {}


def _first_mapping_value(*mappings: Mapping[str, Any], key: str) -> Any:
    for mapping in mappings:
        if key in mapping:
            return mapping[key]
    return None


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if _has_text(value):
            return value
    return None


def _name_from_mapping(value: Any) -> str | None:
    if isinstance(value, Mapping):
        name = value.get("name")
        if _has_text(name):
            return name

    return value if _has_text(value) else None


def _updated_fields(value: Any) -> set[str]:
    if isinstance(value, str):
        return {_normalize(value)}

    if isinstance(value, Mapping):
        return {_normalize(key) for key in value}

    if isinstance(value, (list, tuple, set)):
        return {_normalize(item) for item in value}

    return set()


def _has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_title_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    words = re.sub(r"[^A-Za-z0-9]+", " ", words)
    return " ".join(words.lower().split())


def main() -> int:
    """Read a Linear payload from stdin and print the requested title update."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print(f"Invalid JSON input: {error}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    if action is None:
        return 0

    print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
