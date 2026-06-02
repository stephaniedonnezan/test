"""Build Linear issue title updates for issues moved to research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"

_CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_WORD_SEPARATOR = re.compile(r"[^a-z0-9]+")
_PREFIX_PATTERN = re.compile(rf"^\s*{re.escape(TITLE_PREFIX)}\b", re.IGNORECASE)

_STATUS_CHANGE_FIELDS = {"status", "state", "workflowstate", "workflow state"}
_UPDATE_EVENTS = {"update", "updated", "issue updated", "updated issue"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue enters research."""

    if not isinstance(event, Mapping):
        return None

    payloads = _payload_layers(event)
    if not _is_status_change_event(payloads):
        return None

    status = _find_status(payloads)
    if _normalize_text(status) != "to research":
        return None

    issue_id = _find_first_string(payloads, ("id", "issueId", "issue_id", "identifier"))
    title = _find_first_string(payloads, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _PREFIX_PATTERN.match(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _payload_layers(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload fragments from most issue-specific to broadest context."""

    trigger_context = _mapping_value(event, "triggerContext")
    data = _mapping_value(event, "data")
    data_issue = _mapping_value(data, "issue") if data else None
    issue = _mapping_value(event, "issue")

    layers: list[Mapping[str, Any]] = []
    for layer in (trigger_context, data_issue, issue, data, event):
        if layer is not None and layer not in layers:
            layers.append(layer)
    return layers


def _is_status_change_event(payloads: Iterable[Mapping[str, Any]]) -> bool:
    event_names: list[str] = []
    updated_fields: list[str] = []

    for payload in payloads:
        for key in ("trigger", "action", "type", "webhookType", "eventType"):
            value = payload.get(key)
            if isinstance(value, str):
                event_names.append(_normalize_text(value))

        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            updated_fields.extend(_normalize_sequence(payload.get(key)))

    if "status changed" in event_names or "status change" in event_names:
        return True

    normalized_fields = {_normalize_text(field) for field in updated_fields}
    has_status_field = any(field in _STATUS_CHANGE_FIELDS for field in normalized_fields)
    return has_status_field and any(name in _UPDATE_EVENTS for name in event_names)


def _find_status(payloads: Iterable[Mapping[str, Any]]) -> str | None:
    explicit_status_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "toStatus",
        "to_status",
        "statusName",
        "stateName",
        "workflowStateName",
    )
    fallback_status_keys = ("status", "state", "workflowState")

    for key_group in (explicit_status_keys, fallback_status_keys):
        for payload in payloads:
            for key in key_group:
                value = _string_from_value(payload.get(key))
                if value:
                    return value
    return None


def _find_first_string(payloads: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for payload in payloads:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _mapping_value(payload: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if payload is None:
        return None
    value = payload.get(key)
    return value if isinstance(value, Mapping) else None


def _string_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "displayName"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested
    return None


def _normalize_sequence(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, Mapping)):
        return [item for item in value if isinstance(item, str)]
    return []


def _normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    with_spaces = _CAMEL_CASE_BOUNDARY.sub(" ", value.strip())
    separated = _NON_WORD_SEPARATOR.sub(" ", with_spaces.lower())
    return " ".join(separated.split())


def main() -> int:
    """Read a JSON event from stdin and print the requested title update."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    result = build_issue_title_update(event)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
