"""Build Linear issue title updates for research status changes.

The automation platform is responsible for applying the returned action to
Linear. This module only decides whether a webhook payload should update the
issue title.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_PREFIX_RE = re.compile(r"^\s*cursor researching\b", re.IGNORECASE)

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}

_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}

_STATUS_FIELD_NAMES = {
    "status",
    "status id",
    "status name",
    "state",
    "state id",
    "state name",
    "workflow state",
    "workflow state id",
    "workflow state name",
    "new status",
    "new status id",
    "new status name",
    "new state",
    "new state id",
    "new state name",
}

_TRIGGER_KEYS = ("trigger", "action", "type", "webhookType", "event", "eventType")
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newStatusName",
    "new_status_name",
    "newState",
    "new_state",
    "newStateName",
    "new_state_name",
    "toStatus",
    "to_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_CURRENT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
    "changes",
    "changed",
    "updatedFrom",
    "updated_from",
)
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title", "issueTitle", "issue_title")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action for Linear research status changes.

    The accepted input can be a flat Cursor automation trigger context, a full
    automation wrapper containing ``triggerContext``, or a nested Linear webhook
    payload with issue data under ``data`` or ``issue``.
    """

    if not isinstance(event, Mapping):
        return None

    payload_maps = _payload_maps(event)
    if not _is_status_change_event(payload_maps):
        return None

    new_status = _lookup_status(payload_maps)
    if _normalize_phrase(new_status) != TARGET_STATUS:
        return None

    title = _lookup_text(payload_maps, _TITLE_KEYS)
    issue_id = _lookup_text(payload_maps, _ISSUE_ID_KEYS)
    if not title or not issue_id or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _payload_maps(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return useful payload maps in lookup-priority order."""

    prioritized: list[Mapping[str, Any]] = []
    for path in (
        ("automation_trigger_info", "triggerContext"),
        ("triggerContext",),
        ("data", "issue"),
        ("issue",),
        ("data",),
    ):
        value = _lookup_path(event, path)
        if isinstance(value, Mapping):
            prioritized.append(value)

    prioritized.append(event)

    for mapping in _iter_mappings(event):
        prioritized.append(mapping)

    deduped: list[Mapping[str, Any]] = []
    seen: set[int] = set()
    for mapping in prioritized:
        marker = id(mapping)
        if marker not in seen:
            deduped.append(mapping)
            seen.add(marker)
    return deduped


def _lookup_path(mapping: Mapping[str, Any], path: Sequence[str]) -> Any:
    value: Any = mapping
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested in value.values():
            yield from _iter_mappings(nested)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            yield from _iter_mappings(nested)


def _is_status_change_event(payload_maps: Sequence[Mapping[str, Any]]) -> bool:
    trigger_names = {
        _normalize_phrase(mapping[key])
        for mapping in payload_maps
        for key in _TRIGGER_KEYS
        if key in mapping
    }

    if trigger_names & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    if trigger_names & _GENERIC_UPDATE_EVENTS:
        return _has_status_field_marker(payload_maps)

    return False


def _has_status_field_marker(payload_maps: Sequence[Mapping[str, Any]]) -> bool:
    if any(any(key in mapping for key in _EXPLICIT_STATUS_KEYS) for mapping in payload_maps):
        return True

    for mapping in payload_maps:
        for key in _UPDATED_FIELD_KEYS:
            if key in mapping and _contains_status_field(mapping[key]):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) for key in value.keys())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_status_field(item) for item in value)
    return _is_status_field_name(value)


def _is_status_field_name(value: Any) -> bool:
    return _normalize_phrase(value) in _STATUS_FIELD_NAMES


def _lookup_status(payload_maps: Sequence[Mapping[str, Any]]) -> str | None:
    explicit_status = _lookup_value(payload_maps, _EXPLICIT_STATUS_KEYS)
    if explicit_status is not None:
        return _string_or_named_value(explicit_status)

    current_status = _lookup_value(payload_maps, _CURRENT_STATUS_KEYS)
    if current_status is not None:
        return _string_or_named_value(current_status)

    return None


def _lookup_text(payload_maps: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    value = _lookup_value(payload_maps, keys)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _lookup_value(payload_maps: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> Any:
    for key in keys:
        for mapping in payload_maps:
            if key in mapping and mapping[key] is not None:
                return mapping[key]
    return None


def _string_or_named_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if key in value and value[key] is not None:
                return str(value[key]).strip()
        return None

    text = str(value).strip()
    return text or None


def _normalize_phrase(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = _CAMEL_BOUNDARY_RE.sub(" ", text)
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _has_research_prefix(title: str) -> bool:
    return bool(_PREFIX_RE.match(title))


def main() -> int:
    raw_input = sys.stdin.read()
    event = json.loads(raw_input) if raw_input.strip() else {}
    action = build_issue_title_update(event)
    if action is not None:
        json.dump(action, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
