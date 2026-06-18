"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}
DIRECT_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "issue status changed",
    "workflow state changed",
    "state changed",
}
GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action for issues moved to To Research.

    The automation runtime passes compact Cursor trigger payloads, while Linear
    webhooks commonly nest issue data under ``data.issue``. This function accepts
    both shapes and returns ``None`` when the event should not update the title.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_value(event, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _extract_issue_value(event, ("title", "issueTitle", "issue_title"))
    if not issue_id or not title:
        return None

    clean_title = str(title).strip()
    if not clean_title or _has_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": str(issue_id).strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = [
        value
        for context in _metadata_contexts(event)
        for key in ("trigger", "webhookType", "action", "type", "eventType")
        if (value := context.get(key)) is not None
    ]
    normalized = {_normalize_text(value) for value in trigger_values}

    if normalized & DIRECT_STATUS_CHANGE_TRIGGERS:
        return True

    if normalized & GENERIC_UPDATE_TRIGGERS:
        return _has_status_change_metadata(event)

    return False


def _has_status_change_metadata(event: Mapping[str, Any]) -> bool:
    for context in _all_contexts(event):
        updated_fields = context.get("updatedFields")
        if _contains_status_field(updated_fields):
            return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            if any(_is_status_field_name(key) for key in changes):
                return True
        elif _contains_status_field(changes):
            return True

    return False


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "statusName",
        "stateName",
        "workflowStateName",
        "workflow_state_name",
    )
    for context in _issue_contexts(event):
        for key in explicit_keys:
            if key in context:
                value = _name_value(context.get(key))
                if value:
                    return value

    changed_status = _extract_status_from_changes(event)
    if changed_status:
        return changed_status

    for context in _issue_contexts(event):
        for key in ("status", "state", "workflowState", "workflow_state"):
            if key in context:
                value = _name_value(context.get(key))
                if value:
                    return value

    return None


def _extract_status_from_changes(event: Mapping[str, Any]) -> str | None:
    new_value_keys = (
        "newValue",
        "new_value",
        "new",
        "to",
        "after",
        "value",
        "name",
    )
    for context in _all_contexts(event):
        changes = context.get("changes")
        if isinstance(changes, Mapping):
            for field_name, change in changes.items():
                if not _is_status_field_name(field_name):
                    continue
                if isinstance(change, Mapping):
                    for key in new_value_keys:
                        if key in change:
                            value = _name_value(change.get(key))
                            if value:
                                return value
                else:
                    value = _name_value(change)
                    if value:
                        return value
        elif isinstance(changes, list):
            for change in changes:
                if not isinstance(change, Mapping):
                    continue
                field_name = _field_name(change)
                if not _is_status_field_name(field_name):
                    continue
                for key in new_value_keys:
                    if key in change:
                        value = _name_value(change.get(key))
                        if value:
                            return value

        updated_fields = context.get("updatedFields")
        if isinstance(updated_fields, list):
            for updated_field in updated_fields:
                if not isinstance(updated_field, Mapping):
                    continue
                field_name = _field_name(updated_field)
                if not _is_status_field_name(field_name):
                    continue
                for key in new_value_keys:
                    if key in updated_field:
                        value = _name_value(updated_field.get(key))
                        if value:
                            return value

    return None


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        field_name = _field_name(value)
        return _is_status_field_name(field_name) or any(
            _is_status_field_name(key) for key in value
        )
    if isinstance(value, list):
        return any(_contains_status_field(item) for item in value)
    return False


def _field_name(value: Mapping[str, Any]) -> Any:
    for key in ("field", "fieldName", "field_name", "name", "key"):
        if key in value:
            return value.get(key)
    return None


def _is_status_field_name(value: Any) -> bool:
    return _normalize_text(value) in STATUS_FIELD_NAMES


def _extract_issue_value(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for context in _issue_contexts(event):
        for key in keys:
            if key in context:
                value = context.get(key)
                if value is not None and str(value).strip():
                    return str(value).strip()
    return None


def _metadata_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts = [event]
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        contexts.append(data)

    return _dedupe_contexts(contexts)


def _issue_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        contexts.append(issue)

    data = event.get("data")
    if isinstance(data, Mapping):
        nested_issue = data.get("issue")
        if isinstance(nested_issue, Mapping):
            contexts.append(nested_issue)
        contexts.append(data)

    contexts.append(event)
    return _dedupe_contexts(contexts)


def _all_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _dedupe_contexts([*_metadata_contexts(event), *_issue_contexts(event)])


def _dedupe_contexts(contexts: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    seen: set[int] = set()
    unique: list[Mapping[str, Any]] = []
    for context in contexts:
        identity = id(context)
        if identity in seen:
            continue
        seen.add(identity)
        unique.append(context)
    return unique


def _name_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if key in value:
                nested = _name_value(value.get(key))
                if nested:
                    return nested
    return None if value is None else str(value)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _has_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(PREFIX)}\b", title, flags=re.IGNORECASE) is not None


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
