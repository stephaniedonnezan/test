"""Build Linear issue title update actions for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_EVENT_KEYS = ("trigger", "webhookType", "webhook_type", "action", "type", "event")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title", "name")
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "newState",
    "new_state",
    "toState",
    "to_state",
    "newWorkflowState",
    "new_workflow_state",
    "toWorkflowState",
    "to_workflow_state",
)
_FALLBACK_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_CHANGE_KEYS = ("updatedFields", "updated_fields", "changedFields", "changed_fields", "changes", "updatedFrom")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action when an issue moves to research.

    The automation payloads can arrive as flat Cursor trigger contexts or nested
    Linear webhook payloads. This function only describes the update to make; the
    caller remains responsible for applying it to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_new_status(event)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_issue_title(event)
    if not issue_id or not title:
        return None

    if title.casefold().startswith(TITLE_PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_names = [
        _normalize_text(value)
        for candidate in _metadata_maps(event)
        for key in _EVENT_KEYS
        if (value := _get_case_insensitive(candidate, key)) is not None
    ]

    if any(_is_direct_status_change_name(name) for name in event_names):
        return True

    return any(_is_update_event_name(name) for name in event_names) and _has_status_change_metadata(event)


def _is_direct_status_change_name(name: str) -> bool:
    words = set(name.split())
    return bool(
        ({"status", "changed"} <= words)
        or ({"status", "change"} <= words)
        or ({"state", "changed"} <= words)
        or ({"state", "change"} <= words)
        or ({"workflow", "state", "changed"} <= words)
        or ({"workflow", "state", "change"} <= words)
    )


def _is_update_event_name(name: str) -> bool:
    words = set(name.split())
    return bool("update" in words or "updated" in words)


def _has_status_change_metadata(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            normalized_key = _normalize_text(key)
            if normalized_key in {_normalize_text(change_key) for change_key in _CHANGE_KEYS}:
                if _change_value_mentions_status(nested_value):
                    return True
            if _has_status_change_metadata(nested_value):
                return True
    elif isinstance(value, list):
        return any(_has_status_change_metadata(item) for item in value)

    return False


def _change_value_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) or _change_value_mentions_status(nested) for key, nested in value.items())
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_change_value_mentions_status(item) for item in value)
    return False


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_text(value)
    words = set(normalized.split())
    return bool("status" in words or "state" in words or ({"workflow", "state"} <= words))


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for candidate in _status_maps(event):
        for key in _EXPLICIT_STATUS_KEYS:
            status = _value_to_name(_get_case_insensitive(candidate, key))
            if status:
                return status

    status_from_changes = _extract_status_from_changes(event)
    if status_from_changes:
        return status_from_changes

    for candidate in _status_maps(event):
        for key in _FALLBACK_STATUS_KEYS:
            status = _value_to_name(_get_case_insensitive(candidate, key))
            if status:
                return status

    return None


def _extract_status_from_changes(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            normalized_key = _normalize_text(key)
            if normalized_key in {"updated from", "previous", "old"}:
                continue
            if _is_status_field_name(key):
                status = _value_to_new_name(nested_value)
                if status:
                    return status
            if normalized_key in {_normalize_text(change_key) for change_key in _CHANGE_KEYS}:
                status = _extract_status_from_changes(nested_value)
                if status:
                    return status
            else:
                status = _extract_status_from_changes(nested_value)
                if status:
                    return status
    elif isinstance(value, list):
        for item in value:
            status = _extract_status_from_changes(item)
            if status:
                return status

    return None


def _value_to_new_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("new", "to", "after", "current", "value", "name"):
            status = _value_to_name(_get_case_insensitive(value, key))
            if status:
                return status
    return _value_to_name(value)


def _value_to_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "status", "state", "workflowState", "workflow_state"):
            name = _value_to_name(_get_case_insensitive(value, key))
            if name:
                return name
    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    return _extract_string_from_candidates(_issue_maps(event), _ISSUE_ID_KEYS)


def _extract_issue_title(event: Mapping[str, Any]) -> str | None:
    return _extract_string_from_candidates(_issue_maps(event), _TITLE_KEYS)


def _extract_string_from_candidates(candidates: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for candidate in candidates:
        for key in keys:
            value = _get_case_insensitive(candidate, key)
            if isinstance(value, str):
                stripped = value.strip()
                if stripped:
                    return stripped
    return None


def _metadata_maps(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _dedupe_mappings(
        [
            event,
            _nested_mapping(event, "automation_trigger_info", "triggerContext"),
            _nested_mapping(event, "triggerContext"),
            _nested_mapping(event, "data"),
            _nested_mapping(event, "issue"),
        ]
    )


def _issue_maps(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _dedupe_mappings(
        [
            _nested_mapping(event, "automation_trigger_info", "triggerContext"),
            _nested_mapping(event, "triggerContext"),
            _nested_mapping(event, "data", "issue"),
            _nested_mapping(event, "issue"),
            _nested_mapping(event, "data"),
            event,
        ]
    )


def _status_maps(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _dedupe_mappings(
        [
            event,
            _nested_mapping(event, "automation_trigger_info", "triggerContext"),
            _nested_mapping(event, "triggerContext"),
            _nested_mapping(event, "data"),
            _nested_mapping(event, "data", "issue"),
            _nested_mapping(event, "issue"),
        ]
    )


def _nested_mapping(value: Mapping[str, Any], *path: str) -> Mapping[str, Any] | None:
    current: Any = value
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = _get_case_insensitive(current, key)
    return current if isinstance(current, Mapping) else None


def _dedupe_mappings(candidates: Iterable[Mapping[str, Any] | None]) -> list[Mapping[str, Any]]:
    mappings: list[Mapping[str, Any]] = []
    seen: set[int] = set()
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        marker = id(candidate)
        if marker in seen:
            continue
        seen.add(marker)
        mappings.append(candidate)
    return mappings


def _get_case_insensitive(mapping: Mapping[str, Any], key: str) -> Any:
    if key in mapping:
        return mapping[key]

    normalized_key = _normalize_text(key)
    for candidate_key, value in mapping.items():
        if _normalize_text(candidate_key) == normalized_key:
            return value
    return None


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    json.dump(action, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
