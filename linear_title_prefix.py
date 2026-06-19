"""Build Linear issue title updates for Cursor research automation events."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
TITLE_SEPARATOR = ": "

_TRIGGER_KEYS = {"trigger", "action", "type", "webhookType", "eventType", "webhook_type"}
_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newStatusName",
    "new_status_name",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
)
_CURRENT_STATUS_KEYS = (
    "status",
    "statusName",
    "status_name",
    "state",
    "workflowState",
    "workflow_state",
)
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title", "name")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue moves to research.

    The function intentionally returns a serializable action instead of calling
    Linear directly so it can be used by a workflow step, tested in isolation,
    or invoked from the CLI below.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _event_payload(event)
    if not _is_status_change_event(payload):
        return None

    status = _extract_new_status(payload)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue = _extract_issue(payload)
    if issue is None:
        return None

    issue_id, title = issue
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}{TITLE_SEPARATOR}{title}",
    }


def _event_payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    """Prefer Cursor's trigger context wrapper when present."""

    automation_info = event.get("automation_trigger_info")
    if isinstance(automation_info, Mapping):
        trigger_context = automation_info.get("triggerContext")
        if isinstance(trigger_context, Mapping):
            return trigger_context

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context

    payload = event.get("payload")
    if isinstance(payload, Mapping):
        return payload

    return event


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    triggers = {_normalize(value) for value in _trigger_values(event)}

    direct_status_triggers = {
        "status changed",
        "status change",
        "status updated",
        "state changed",
        "state change",
        "workflow state changed",
        "workflow state change",
    }
    if triggers & direct_status_triggers:
        return True

    update_triggers = {
        "update",
        "updated",
        "issue update",
        "issue updated",
        "updated issue",
    }
    return bool(triggers & update_triggers and _changed_status_fields(event))


def _trigger_values(value: Any) -> Iterable[Any]:
    for mapping in _iter_mappings(value):
        for key, item in mapping.items():
            if key in _TRIGGER_KEYS:
                yield item


def _changed_status_fields(event: Mapping[str, Any]) -> bool:
    field_names: set[str] = set()

    for mapping in _iter_mappings(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            field_names.update(_field_names_from_value(mapping.get(key)))

        changes = mapping.get("changes")
        if isinstance(changes, Mapping):
            field_names.update(_normalize(field) for field in changes.keys())

        change = mapping.get("change")
        if isinstance(change, Mapping):
            field_names.update(_normalize(field) for field in change.keys())

    return any(_is_status_field_name(name) for name in field_names)


def _field_names_from_value(value: Any) -> set[str]:
    if isinstance(value, str):
        return {_normalize(value)}

    if isinstance(value, Mapping):
        return {_normalize(key) for key in value.keys()}

    if isinstance(value, Iterable) and not isinstance(value, (bytes, str)):
        return {_normalize(item) for item in value}

    return set()


def _is_status_field_name(value: str) -> bool:
    compact = value.replace(" ", "")
    return value in _STATUS_FIELD_NAMES or compact in _STATUS_FIELD_NAMES


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for key in _NEW_STATUS_KEYS:
        for mapping in _iter_mappings(event):
            status = _status_name(mapping.get(key))
            if status:
                return status

    status_from_changes = _status_from_changes(event)
    if status_from_changes:
        return status_from_changes

    for key in _CURRENT_STATUS_KEYS:
        for mapping in _iter_mappings(event):
            status = _status_name(mapping.get(key))
            if status:
                return status

    return None


def _status_from_changes(event: Mapping[str, Any]) -> str | None:
    for mapping in _iter_mappings(event):
        for changes_key in ("changes", "change"):
            changes = mapping.get(changes_key)
            if not isinstance(changes, Mapping):
                continue

            for field, value in changes.items():
                if not _is_status_field_name(_normalize(field)):
                    continue

                status = _new_value_from_change(value)
                if status:
                    return status

    return None


def _new_value_from_change(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "after", "newValue", "new_value", "new", "current", "name"):
            status = _status_name(value.get(key))
            if status:
                return status
    elif isinstance(value, list) and value:
        return _status_name(value[-1])
    else:
        return _status_name(value)

    return None


def _status_name(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state", "workflowState", "workflow_state"):
            status = _status_name(value.get(key))
            if status:
                return status

    return None


def _extract_issue(event: Mapping[str, Any]) -> tuple[str, str] | None:
    candidates: list[tuple[float, Mapping[str, Any]]] = []

    for path, mapping in _iter_mappings_with_path(event):
        title = _text_from_keys(mapping, _TITLE_KEYS)
        issue_id = _text_from_keys(mapping, _ISSUE_ID_KEYS)
        if not title or not issue_id:
            continue

        score = 4.0
        if any(part in {"issue", "data", "triggerContext"} for part in path):
            score += 2.0
        if _text_from_keys(mapping, ("issueId", "issue_id", "identifier", "key")):
            score += 2.0
        if "id" in mapping:
            score += 0.5
        score += min(len(path), 10) / 10
        candidates.append((score, mapping))

    if not candidates:
        return None

    _, issue = max(candidates, key=lambda candidate: candidate[0])
    issue_id = _text_from_keys(issue, _ISSUE_ID_KEYS)
    title = _text_from_keys(issue, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    return issue_id, title


def _text_from_keys(mapping: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _has_research_prefix(title: str) -> bool:
    return _normalize(title).startswith(PREFIX.lower())


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    for _, mapping in _iter_mappings_with_path(value):
        yield mapping


def _iter_mappings_with_path(value: Any, path: tuple[str, ...] = ()) -> Iterable[tuple[tuple[str, ...], Mapping[str, Any]]]:
    if isinstance(value, Mapping):
        yield path, value
        for key, item in value.items():
            if isinstance(item, Mapping):
                yield from _iter_mappings_with_path(item, (*path, str(key)))
            elif isinstance(item, list):
                for index, child in enumerate(item):
                    yield from _iter_mappings_with_path(child, (*path, str(key), str(index)))


def main() -> None:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))


if __name__ == "__main__":
    main()
