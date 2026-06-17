"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflowstatus"}
DIRECT_STATUS_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
    "workflowstatuschanged",
    "workflowstatuschange",
}
GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdated",
    "issueupdate",
    "updatedissue",
}

EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "newWorkflowStateName",
    "newWorkflowStatus",
    "newWorkflowStatusName",
    "statusName",
    "stateName",
    "workflowStateName",
)
CURRENT_STATUS_KEYS = (
    "status",
    "state",
    "workflowState",
    "workflow_state",
    "workflowStatus",
    "workflow_status",
)
ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
TITLE_KEYS = ("title", "issueTitle", "issue_title", "name")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue moves to research."""

    if not isinstance(event, Mapping) or not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(_candidate_mappings(event), ISSUE_ID_KEYS)
    title = _first_text(_candidate_mappings(event), TITLE_KEYS)
    if not issue_id or not title or _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_tokens = {
        _normalize_token(value)
        for mapping in _iter_mappings(event)
        for key, value in mapping.items()
        if key
        in {
            "trigger",
            "action",
            "type",
            "webhookType",
            "webhook_type",
            "event",
            "eventType",
            "event_type",
        }
    }

    if trigger_tokens & DIRECT_STATUS_TRIGGERS:
        return True

    if trigger_tokens & GENERIC_UPDATE_TRIGGERS:
        return _status_field_changed(event)

    return False


def _status_field_changed(event: Mapping[str, Any]) -> bool:
    for mapping in _iter_mappings(event):
        for key, value in mapping.items():
            normalized_key = _normalize_token(key)
            if normalized_key in {
                "updatedfields",
                "changedfields",
                "changedproperties",
                "updatedproperties",
            }:
                if _mentions_status_field(value):
                    return True

            if normalized_key in {"changes", "changed", "diff"}:
                if _changes_include_status(value):
                    return True

    return False


def _mentions_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if not isinstance(value, Iterable) or isinstance(value, (bytes, bytearray, Mapping)):
        return False

    return any(_mentions_status_field(item) for item in value)


def _changes_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_is_status_field_name(field) for field in value)

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
        return any(
            isinstance(item, Mapping)
            and _is_status_field_name(
                _first_raw(item, ("field", "fieldName", "name", "key", "property"))
            )
            for item in value
        )

    return False


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    explicit_status = _first_status_name(_candidate_mappings(event), EXPLICIT_STATUS_KEYS)
    if explicit_status:
        return explicit_status

    changed_status = _status_from_changes(event)
    if changed_status:
        return changed_status

    return _first_status_name(_candidate_mappings(event), CURRENT_STATUS_KEYS)


def _status_from_changes(event: Mapping[str, Any]) -> str | None:
    for mapping in _iter_mappings(event):
        changes = mapping.get("changes")
        if isinstance(changes, Mapping):
            status = _status_from_changes_mapping(changes)
            if status:
                return status
        elif isinstance(changes, Iterable) and not isinstance(
            changes, (str, bytes, bytearray, Mapping)
        ):
            status = _status_from_changes_list(changes)
            if status:
                return status

    return None


def _status_from_changes_mapping(changes: Mapping[str, Any]) -> str | None:
    for field, value in changes.items():
        if not _is_status_field_name(field):
            continue

        status = _changed_status_name(value)
        if status:
            return status

    return None


def _status_from_changes_list(changes: Iterable[Any]) -> str | None:
    for change in changes:
        if not isinstance(change, Mapping):
            continue

        field = _first_raw(change, ("field", "fieldName", "name", "key", "property"))
        if not _is_status_field_name(field):
            continue

        status = _changed_status_name(change)
        if status:
            return status

    return None


def _changed_status_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in (
            "new",
            "to",
            "after",
            "current",
            "newValue",
            "new_value",
            "value",
            "name",
        ):
            status = _status_name(value.get(key))
            if status:
                return status

    return _status_name(value)


def _first_status_name(
    mappings: Iterable[Mapping[str, Any]], keys: Iterable[str]
) -> str | None:
    for mapping in mappings:
        for key in keys:
            status = _status_name(mapping.get(key))
            if status:
                return status

    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "status", "state", "workflowState"):
            status = _status_name(value.get(key))
            if status:
                return status

    return None


def _candidate_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        _append_mapping(candidates, trigger_context)
        _append_mapping(candidates, trigger_context.get("issue"))

    data = event.get("data")
    if isinstance(data, Mapping):
        _append_mapping(candidates, data.get("issue"))
        _append_mapping(candidates, data.get("node"))
        _append_mapping(candidates, data)

    _append_mapping(candidates, event.get("issue"))
    _append_mapping(candidates, event)

    return candidates


def _append_mapping(candidates: list[Mapping[str, Any]], value: Any) -> None:
    if isinstance(value, Mapping) and value not in candidates:
        candidates.append(value)


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _iter_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_mappings(child)


def _first_text(mappings: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for mapping in mappings:
        for key in keys:
            value = mapping.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()

    return None


def _first_raw(mapping: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]

    return None


def _is_status_field_name(value: Any) -> bool:
    return _normalize_token(value) in STATUS_FIELD_NAMES


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value))
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _normalize_token(value: Any) -> str:
    return _normalize_words(value).replace(" ", "")


def _has_title_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(TITLE_PREFIX)}\b", title, re.IGNORECASE) is not None


def main() -> int:
    """Read a JSON event from stdin and print the requested title update."""

    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
