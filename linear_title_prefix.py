"""Build Linear issue title updates for Cursor research automation triggers."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_TRIGGER_FIELDS = (
    "trigger",
    "webhookType",
    "webhook_type",
    "action",
    "type",
    "eventType",
    "event_type",
)
_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "issue status changed",
    "state changed",
    "workflow state changed",
}
_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_STATUS_FIELD_NAMES = {
    "status",
    "statusId",
    "status_id",
    "state",
    "stateId",
    "state_id",
    "workflowState",
    "workflow_state",
    "workflowStateId",
    "workflow_state_id",
}
_NEW_STATUS_FIELDS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "status",
    "state",
    "workflowState",
    "workflow_state",
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to To Research.

    The function is intentionally side-effect free. Callers can use the returned
    action to perform the Linear mutation in their own integration layer.
    """

    if not isinstance(event, Mapping):
        return None

    context = _automation_context(event)
    issue = _issue_payload(context)

    if not _is_status_change_event(event, context):
        return None

    if _normalize_phrase(_new_status(event, context, issue)) != TARGET_STATUS:
        return None

    issue_id = _first_text(issue, context, keys=("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(issue, context, keys=("title",))
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


def _automation_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    automation_info = _mapping_value(event, "automation_trigger_info") or _mapping_value(
        event, "automationTriggerInfo"
    )
    if automation_info:
        trigger_context = _mapping_value(automation_info, "triggerContext") or _mapping_value(
            automation_info, "trigger_context"
        )
        if trigger_context:
            return trigger_context

    return _mapping_value(event, "triggerContext") or _mapping_value(event, "trigger_context") or event


def _issue_payload(context: Mapping[str, Any]) -> Mapping[str, Any]:
    issue = _mapping_value(context, "issue")
    if issue:
        return issue

    data = _mapping_value(context, "data")
    if data:
        nested_issue = _mapping_value(data, "issue")
        return nested_issue or data

    return context


def _is_status_change_event(event: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    trigger_values = [_normalize_phrase(value) for value in _trigger_values(event, context)]
    if any(value in _DIRECT_STATUS_CHANGE_TRIGGERS for value in trigger_values):
        return True

    if any(value in _GENERIC_UPDATE_TRIGGERS for value in trigger_values):
        return _updated_status_fields_present(event) or _updated_status_fields_present(context)

    return False


def _trigger_values(*payloads: Mapping[str, Any]) -> list[Any]:
    values: list[Any] = []
    for payload in payloads:
        for key in _TRIGGER_FIELDS:
            if key in payload:
                values.append(payload[key])

        automation_info = _mapping_value(payload, "automation_trigger_info") or _mapping_value(
            payload, "automationTriggerInfo"
        )
        if automation_info:
            values.extend(_trigger_values(automation_info))

    return values


def _updated_status_fields_present(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields"):
        fields = payload.get(key)
        if _sequence_contains_status_field(fields):
            return True

    for key in ("changes", "changedFields", "changed_fields", "updatedFrom"):
        changes = payload.get(key)
        if isinstance(changes, Mapping) and any(_is_status_field_name(name) for name in changes):
            return True
        if _sequence_contains_status_field(changes):
            return True

    data = _mapping_value(payload, "data")
    return bool(data and _updated_status_fields_present(data))


def _new_status(
    event: Mapping[str, Any],
    context: Mapping[str, Any],
    issue: Mapping[str, Any],
) -> Any:
    for payload in (context, event):
        for key in _NEW_STATUS_FIELDS:
            value = _named_value(payload.get(key))
            if value:
                return value

    changed_status = _changed_status_value(event) or _changed_status_value(context)
    if changed_status:
        return changed_status

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _named_value(issue.get(key))
        if value:
            return value

    return None


def _changed_status_value(payload: Mapping[str, Any]) -> Any:
    for changes_key in ("changes", "changedFields", "changed_fields"):
        changes = payload.get(changes_key)
        if not isinstance(changes, Mapping):
            continue

        for field_name, change in changes.items():
            if not _is_status_field_name(field_name):
                continue

            if isinstance(change, Mapping):
                for key in ("to", "new", "newValue", "new_value", "after"):
                    value = _named_value(change.get(key))
                    if value:
                        return value

            value = _named_value(change)
            if value:
                return value

    data = _mapping_value(payload, "data")
    return _changed_status_value(data) if data else None


def _sequence_contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        return False
    return any(_is_status_field_name(item) for item in value)


def _is_status_field_name(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = _normalize_key(value)
    return any(normalized == _normalize_key(field_name) for field_name in _STATUS_FIELD_NAMES)


def _first_text(*payloads: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for payload in payloads:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, (str, int, float)) and str(value).strip():
                return str(value)
    return None


def _mapping_value(payload: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    value = payload.get(key)
    return value if isinstance(value, Mapping) else None


def _named_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "status"):
            nested_value = value.get(key)
            if isinstance(nested_value, (str, int, float)) and str(nested_value).strip():
                return nested_value
        return None
    return value


def _has_title_prefix(title: str) -> bool:
    return bool(re.match(r"^\s*cursor\s+researching\b", title, flags=re.IGNORECASE))


def _normalize_key(value: str) -> str:
    return _normalize_phrase(value).replace(" ", "")


def _normalize_phrase(value: Any) -> str:
    if value is None:
        return ""
    text = str(_named_value(value) or "").strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
