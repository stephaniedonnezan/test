"""Build Linear issue title updates for research-status automations.

The automation runtime can pass either Cursor's flat ``triggerContext`` payload
or a nested Linear webhook payload.  This module keeps the behavior limited to a
presentation update: when an issue moves to "to research", prefix its title with
"Cursor researching" without changing any issue data.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflowstatus"}
_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statuschangedissue",
    "issuestatuschanged",
    "workflowstatechanged",
    "statechanged",
}
_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdated",
    "updatedissue",
    "statuschanged",
    "statuschangedissue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update action for matching Linear status changes."""
    if not isinstance(event, Mapping):
        return None

    maps = list(_candidate_maps(event))

    if not _is_status_change_event(maps):
        return None

    new_status = _extract_new_status(maps)
    if _normalize_label(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(maps, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _extract_first_text(maps, ("title", "name"))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {stripped_title}",
    }


def _candidate_maps(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return relevant payload maps from most to least specific."""
    candidates: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in candidates:
            candidates.append(value)

    add(event.get("triggerContext"))
    automation_info = event.get("automation_trigger_info") or event.get("automationTriggerInfo")
    if isinstance(automation_info, Mapping):
        add(automation_info.get("triggerContext"))
    trigger_context = event.get("trigger_context")
    add(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data)

    add(event.get("issue"))
    payload = event.get("payload")
    if isinstance(payload, Mapping):
        add(payload.get("issue"))
        add(payload.get("data"))
        add(payload)

    add(event)
    return candidates


def _is_status_change_event(maps: Sequence[Mapping[str, Any]]) -> bool:
    trigger_names = [
        _normalize_token(value)
        for mapping in maps
        for value in (
            mapping.get("trigger"),
            mapping.get("webhookType"),
            mapping.get("action"),
            mapping.get("type"),
        )
        if isinstance(value, str)
    ]
    if any(name in _DIRECT_STATUS_CHANGE_TRIGGERS for name in trigger_names):
        return True

    if _updated_fields_include_status(maps) or _changes_include_status(maps):
        return any(name in _GENERIC_UPDATE_TRIGGERS for name in trigger_names) or not trigger_names

    return False


def _extract_new_status(maps: Sequence[Mapping[str, Any]]) -> str | None:
    for mapping in maps:
        value = _text_from_value(
            _get_any(
                mapping,
                (
                    "newStatus",
                    "new_status",
                    "newState",
                    "new_state",
                    "newWorkflowState",
                    "new_workflow_state",
                    "statusName",
                    "stateName",
                ),
            )
        )
        if value:
            return value

    changed_status = _status_from_changes(maps)
    if changed_status:
        return changed_status

    for mapping in maps:
        value = _text_from_value(_get_any(mapping, ("status", "state", "workflowState", "workflow_status")))
        if value:
            return value

    return None


def _status_from_changes(maps: Sequence[Mapping[str, Any]]) -> str | None:
    for mapping in maps:
        changes = mapping.get("changes") or mapping.get("updatedFields")
        if isinstance(changes, Mapping):
            for key, value in changes.items():
                if _is_status_field_name(key):
                    status = _new_value_from_change(value)
                    if status:
                        return status
        elif isinstance(changes, Sequence) and not isinstance(changes, (str, bytes, bytearray)):
            for change in changes:
                if isinstance(change, Mapping):
                    field_name = _extract_first_text((change,), ("field", "name", "key", "fieldName"))
                    if field_name and _is_status_field_name(field_name):
                        status = _new_value_from_change(change)
                        if status:
                            return status
                elif isinstance(change, str) and _is_status_field_name(change):
                    fallback = _extract_status_from_map(mapping)
                    if fallback:
                        return fallback
    return None


def _new_value_from_change(change: Any) -> str | None:
    if isinstance(change, Mapping):
        value = _get_any(change, ("newValue", "new_value", "to", "after", "value", "name"))
        return _text_from_value(value)
    return _text_from_value(change)


def _extract_status_from_map(mapping: Mapping[str, Any]) -> str | None:
    return _text_from_value(_get_any(mapping, ("newStatus", "new_status", "status", "state", "workflowState")))


def _updated_fields_include_status(maps: Sequence[Mapping[str, Any]]) -> bool:
    for mapping in maps:
        fields = mapping.get("updatedFields") or mapping.get("updated_fields")
        if isinstance(fields, Mapping):
            if any(_is_status_field_name(key) for key in fields):
                return True
        elif isinstance(fields, Sequence) and not isinstance(fields, (str, bytes, bytearray)):
            if any(_is_status_field_name(field) for field in fields):
                return True
        elif isinstance(fields, str) and _is_status_field_name(fields):
            return True
    return False


def _changes_include_status(maps: Sequence[Mapping[str, Any]]) -> bool:
    for mapping in maps:
        changes = mapping.get("changes")
        if isinstance(changes, Mapping):
            if any(_is_status_field_name(key) for key in changes):
                return True
        elif isinstance(changes, Sequence) and not isinstance(changes, (str, bytes, bytearray)):
            for change in changes:
                if isinstance(change, Mapping):
                    field_name = _extract_first_text((change,), ("field", "name", "key", "fieldName"))
                    if field_name and _is_status_field_name(field_name):
                        return True
                elif isinstance(change, str) and _is_status_field_name(change):
                    return True
    return False


def _extract_first_text(maps: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for key in keys:
        for mapping in maps:
            value = _text_from_value(mapping.get(key))
            if value:
                return value
    return None


def _get_any(mapping: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _text_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value"):
            text = _text_from_value(value.get(key))
            if text:
                return text
    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _is_status_field_name(value: Any) -> bool:
    return isinstance(value, str) and _normalize_token(value) in _STATUS_FIELD_NAMES


def _normalize_label(value: str | None) -> str | None:
    if value is None:
        return None
    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value.strip())
    return re.sub(r"[\s_-]+", " ", spaced).casefold()


def _normalize_token(value: str) -> str:
    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value.strip())
    return re.sub(r"[^a-z0-9]+", "", spaced.casefold())


def main() -> int:
    """Read a JSON event from stdin and print the title update action, if any."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is None:
        return 0

    print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
