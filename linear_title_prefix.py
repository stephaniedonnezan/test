"""Build Linear issue title update actions for Cursor research automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflow status",
    "workflow_status",
    "workflow-state",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue enters research."""
    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change(contexts):
        return None

    new_status = _find_new_status(contexts)
    if _normalize_status(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("id", "issueId", "issue_id", "identifier", "key"))
    title = _first_text(contexts, ("title", "name"))
    if issue_id is None or title is None:
        return None

    title = title.strip()
    if not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def collect(value: Any) -> None:
        if not isinstance(value, Mapping):
            return

        contexts.append(value)
        for key in ("triggerContext", "data", "issue", "state", "workflowState", "status"):
            nested = value.get(key)
            if isinstance(nested, Mapping) and nested not in contexts:
                collect(nested)

    collect(event)
    return contexts


def _is_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    event_markers = _all_text(contexts, ("trigger", "webhookType", "action", "type"))
    if any(_normalize_marker(marker) in {"statuschanged", "statuschange"} for marker in event_markers):
        return True

    if any(_normalize_marker(marker) in {"issueupdated", "updatedissue", "update"} for marker in event_markers):
        return _updated_fields_include_status(contexts)

    return False


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "changedFields"):
            if _field_list_mentions_status(context.get(key)):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            if any(_is_status_field_name(key) for key in changes):
                return True
        elif _field_list_mentions_status(changes):
            return True

    return False


def _field_list_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) for key in value)

    if isinstance(value, list | tuple | set):
        for item in value:
            if isinstance(item, Mapping):
                names = _all_text([item], ("name", "field", "fieldName", "key"))
                if any(_is_status_field_name(name) for name in names):
                    return True
            elif _is_status_field_name(item):
                return True

    return False


def _is_status_field_name(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return _normalize_field_name(value) in {_normalize_field_name(name) for name in STATUS_FIELD_NAMES}


def _find_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit = _first_text(
        contexts,
        (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "toStatus",
            "to_status",
            "statusName",
            "stateName",
            "workflowStateName",
        ),
    )
    if explicit is not None:
        return explicit

    for context in contexts:
        changes = context.get("changes")
        changed_status = _status_from_changes(changes)
        if changed_status is not None:
            return changed_status

    return _first_text(contexts, ("status", "state", "workflowState", "name"))


def _status_from_changes(changes: Any) -> str | None:
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if not _is_status_field_name(key):
                continue
            if isinstance(value, Mapping):
                status = _first_text([value], ("to", "new", "newValue", "after", "name"))
                if status is not None:
                    return status
            elif isinstance(value, str):
                return value

    if isinstance(changes, list | tuple):
        for change in changes:
            if not isinstance(change, Mapping):
                continue
            names = _all_text([change], ("field", "fieldName", "name", "key"))
            if not any(_is_status_field_name(name) for name in names):
                continue
            status = _first_text([change], ("to", "new", "newValue", "after", "value"))
            if status is not None:
                return status

    return None


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, Mapping):
                nested_name = _first_text([value], ("name", "title"))
                if nested_name is not None:
                    return nested_name
    return None


def _all_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> list[str]:
    values: list[str] = []
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str):
                values.append(value)
    return values


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"[^a-z0-9]+", " ", _split_camel_case(value).lower()).strip()


def _normalize_marker(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _split_camel_case(value).lower())


def _normalize_field_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _split_camel_case(value).lower())


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
