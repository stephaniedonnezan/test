"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
    "workflow",
    "workflowid",
}
_DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title update when the issue moved to to-research."""
    if not isinstance(event, Mapping):
        return None

    contexts = _collect_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _find_new_status(contexts)
    if _normalize_label(status) != TARGET_STATUS:
        return None

    title = _first_text(contexts, ("title", "name"))
    issue_id = _first_text(
        contexts,
        ("issueId", "issue_id", "identifier", "key", "id"),
        prefer_identifier=True,
    )
    if not title or not issue_id:
        return None

    title = title.strip()
    issue_id = issue_id.strip()
    if not title or not issue_id or _has_title_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _collect_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect likely metadata/issue objects from Cursor and Linear payloads."""
    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def add(value: Any) -> None:
        if not isinstance(value, Mapping) or id(value) in seen:
            return
        seen.add(id(value))
        contexts.append(value)

        for key in ("automation_trigger_info", "triggerContext", "data", "issue"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                add(nested)

        data = value.get("data")
        if isinstance(data, Mapping):
            issue = data.get("issue")
            if isinstance(issue, Mapping):
                add(issue)

    add(event)
    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    has_generic_update = False

    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type", "event"):
            value = context.get(key)
            if not _is_text(value):
                continue

            normalized = _normalize_label(value)
            if normalized in _DIRECT_STATUS_TRIGGERS:
                return True
            if normalized in _GENERIC_UPDATE_TRIGGERS:
                has_generic_update = True

    if has_generic_update and _has_status_change_marker(contexts):
        return True

    return _find_explicit_new_status(contexts) is not None and has_generic_update


def _has_status_change_marker(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "changedFields", "updated_fields", "changed_fields"):
            if _field_collection_has_status_marker(context.get(key)):
                return True

        for key in ("changes", "updatedFrom", "updated_from", "previousValues"):
            value = context.get(key)
            if isinstance(value, Mapping) and any(
                _is_status_field(field_name) for field_name in value.keys()
            ):
                return True

    return False


def _field_collection_has_status_marker(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        return any(
            _is_status_field(key) or _field_collection_has_status_marker(item)
            for key, item in value.items()
        )

    if isinstance(value, Iterable):
        for item in value:
            if _is_text(item) and _is_status_field(item):
                return True
            if isinstance(item, Mapping):
                name = _first_text((item,), ("name", "field", "key", "property"))
                if name and _is_status_field(name):
                    return True

    return False


def _is_status_field(value: Any) -> bool:
    if not _is_text(value):
        return False
    return _normalize_field_name(value) in _STATUS_FIELD_NAMES


def _find_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    explicit_status = _find_explicit_new_status(contexts)
    if explicit_status:
        return explicit_status

    changed_status = _find_changed_status(contexts)
    if changed_status:
        return changed_status

    for context in contexts:
        status = _status_from_context(context)
        if status:
            return status

    return None


def _find_explicit_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    status_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "statusName",
        "stateName",
        "workflowStateName",
    )
    return _first_text(contexts, status_keys)


def _find_changed_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        changes = context.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for key, value in changes.items():
            if _is_status_field(key):
                status = _status_from_change(value)
                if status:
                    return status

    return None


def _status_from_change(value: Any) -> str | None:
    if _is_text(value):
        return str(value)

    if not isinstance(value, Mapping):
        return None

    for key in (
        "newValue",
        "new_value",
        "new",
        "to",
        "after",
        "value",
        "name",
    ):
        candidate = value.get(key)
        if _is_text(candidate):
            return str(candidate)
        if isinstance(candidate, Mapping):
            nested_name = _first_text((candidate,), ("name", "title", "label"))
            if nested_name:
                return nested_name

    return None


def _status_from_context(context: Mapping[str, Any]) -> str | None:
    status = context.get("status")
    if _is_text(status):
        return str(status)
    if isinstance(status, Mapping):
        status_name = _first_text((status,), ("name", "title", "label"))
        if status_name:
            return status_name

    for key in ("state", "workflowState", "workflow_state"):
        value = context.get(key)
        if _is_text(value):
            return str(value)
        if isinstance(value, Mapping):
            state_name = _first_text((value,), ("name", "title", "label"))
            if state_name:
                return state_name

    return None


def _first_text(
    contexts: Iterable[Mapping[str, Any]],
    keys: Iterable[str],
    *,
    prefer_identifier: bool = False,
) -> str | None:
    key_list = tuple(keys)
    if prefer_identifier:
        priority_keys = ("issueId", "issue_id", "identifier", "key")
        fallback_keys = tuple(key for key in key_list if key not in priority_keys)
        key_list = priority_keys + fallback_keys

    for key in key_list:
        for context in contexts:
            value = context.get(key)
            if _is_text(value):
                return str(value).strip()

    return None


def _has_title_prefix(title: str) -> bool:
    return title.lstrip().lower().startswith(TITLE_PREFIX.lower())


def _normalize_label(value: Any) -> str:
    if not _is_text(value):
        return ""

    label = str(value).strip()
    label = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", label)
    label = re.sub(r"[_\-/]+", " ", label)
    label = re.sub(r"\s+", " ", label)
    return label.lower()


def _normalize_field_name(value: str) -> str:
    label = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "", value.strip())
    return re.sub(r"[^a-z0-9]", "", label.lower())


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def main() -> int:
    """Read a JSON event from stdin and print the title update, if any."""
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
