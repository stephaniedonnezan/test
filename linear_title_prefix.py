"""Build title update actions for Linear issue research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_MARKER = "Cursor researching"

_STATUS_FIELD_NAMES = {
    "status",
    "status_id",
    "statusid",
    "state",
    "state_id",
    "stateid",
    "workflow_state",
    "workflow_state_id",
    "workflowstate",
    "workflowstateid",
}
_DIRECT_STATUS_TRIGGERS = {
    "issue_state_changed",
    "issue_status_changed",
    "issue_workflow_state_changed",
    "state_change",
    "state_changed",
    "status_change",
    "status_changed",
    "workflow_state_change",
    "workflow_state_changed",
}
_GENERIC_UPDATE_TRIGGERS = {
    "issue_update",
    "issue_updated",
    "update",
    "updated",
    "updated_issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue enters research."""

    if not isinstance(event, Mapping):
        return None

    sources = _payload_sources(event)
    if not _is_status_change_event(sources):
        return None

    status = _find_new_status(sources)
    if _normalize_text(status) != RESEARCH_STATUS:
        return None

    issue_id = _find_issue_id(sources)
    title = _find_title(sources)
    if not issue_id or not title:
        return None

    if title.lower().startswith(TITLE_MARKER.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_MARKER}: {title}",
    }


def _payload_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping):
            return

        sources.append(value)
        for key in (
            "automation_trigger_info",
            "automationTriggerInfo",
            "triggerContext",
            "data",
            "issue",
        ):
            visit(value.get(key))

    visit(event)
    return sources


def _is_status_change_event(sources: Sequence[Mapping[str, Any]]) -> bool:
    saw_generic_update = False

    for source in sources:
        for key in ("trigger", "webhookType", "webhook_type", "action", "type"):
            signal = _normalize_identifier(source.get(key))
            if not signal:
                continue

            if signal in _DIRECT_STATUS_TRIGGERS:
                return True

            if signal in _GENERIC_UPDATE_TRIGGERS:
                saw_generic_update = True

        if _has_status_change_marker(source):
            return True

    return saw_generic_update and any(_has_status_change_details(source) for source in sources)


def _has_status_change_marker(source: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if _contains_status_field(source.get(key)):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        for key, child_value in value.items():
            if _is_status_field(key) or _contains_status_field(child_value):
                return True
        for key in ("field", "name", "key", "id"):
            if _is_status_field(value.get(key)):
                return True

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_status_field(item) for item in value)

    return False


def _has_status_change_details(source: Mapping[str, Any]) -> bool:
    for key in ("changes", "change", "updatedFrom", "updated_from", "previousValues"):
        value = source.get(key)
        if isinstance(value, Mapping) and any(_is_status_field(changed_key) for changed_key in value):
            return True

    return False


def _find_new_status(sources: Sequence[Mapping[str, Any]]) -> str | None:
    explicit_status_keys = (
        "newStatus",
        "new_status",
        "newStatusName",
        "new_status_name",
        "statusName",
        "status_name",
        "newState",
        "new_state",
        "stateName",
        "state_name",
        "newWorkflowState",
        "new_workflow_state",
        "workflowStateName",
        "workflow_state_name",
    )

    status = _first_stringish(sources, explicit_status_keys)
    if status:
        return status

    status = _status_from_changes(sources)
    if status:
        return status

    for source in sources:
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _string_from_status_value(source.get(key))
            if status:
                return status

    return None


def _status_from_changes(sources: Sequence[Mapping[str, Any]]) -> str | None:
    for source in sources:
        for changes_key in ("changes", "change"):
            changes = source.get(changes_key)
            if not isinstance(changes, Mapping):
                continue

            for key, value in changes.items():
                if _is_status_field(key):
                    status = _string_from_change_value(value)
                    if status:
                        return status

    return None


def _string_from_change_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "new", "after", "value", "newValue", "new_value", "name"):
            result = _string_from_status_value(value.get(key))
            if result:
                return result

    return _string_from_status_value(value)


def _find_issue_id(sources: Sequence[Mapping[str, Any]]) -> str | None:
    issue_id = _first_stringish(sources, ("issueId", "issue_id", "identifier", "key"))
    if issue_id:
        return issue_id

    return _first_stringish(list(reversed(sources)), ("id",))


def _find_title(sources: Sequence[Mapping[str, Any]]) -> str | None:
    return _first_stringish(sources, ("title",))


def _first_stringish(sources: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for source in sources:
        for key in keys:
            value = source.get(key)
            if isinstance(value, str):
                normalized = value.strip()
                if normalized:
                    return normalized

    return None


def _string_from_status_value(value: Any) -> str | None:
    if isinstance(value, str):
        value = value.strip()
        return value or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state", "displayName", "display_name"):
            result = _string_from_status_value(value.get(key))
            if result:
                return result

    return None


def _is_status_field(value: Any) -> bool:
    identifier = _normalize_identifier(value)
    return bool(identifier and identifier in _STATUS_FIELD_NAMES)


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", words)


def _normalize_identifier(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value.strip())
    return re.sub(r"[\s\-]+", "_", spaced).lower()


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(payload)
    json.dump(action, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
