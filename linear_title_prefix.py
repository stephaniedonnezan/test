"""Build Linear issue title updates for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
PREFIXED_TITLE_TEMPLATE = f"{PREFIX}: {{title}}"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to To Research.

    The automation trigger payload is flat under ``triggerContext`` while
    Linear webhooks commonly nest data under ``data.issue``. This function
    accepts both shapes and returns a small action object for the caller to
    apply through the Linear API.
    """
    if not isinstance(event, Mapping):
        return None

    mappings = list(_walk_mappings(event))
    if not _is_status_change_event(mappings):
        return None

    status = _first_status_value(mappings)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    issue_id = _first_issue_id(event)
    title = _first_title(event)
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        prefixed_title = title
    else:
        prefixed_title = PREFIXED_TITLE_TEMPLATE.format(title=title)

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": prefixed_title,
    }


def _is_status_change_event(mappings: Iterable[Mapping[str, Any]]) -> bool:
    mapping_list = list(mappings)
    for mapping in mapping_list:
        for key in ("trigger", "webhookType", "action", "type", "event"):
            normalized = _normalize_words(mapping.get(key))
            if normalized in {"status changed", "status change"}:
                return True
            if normalized in {"update", "updated", "issue updated", "updated issue"}:
                return _updated_fields_include_status(mapping_list)
    return False


def _updated_fields_include_status(mappings: Iterable[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        for key in ("updatedFields", "updated_fields"):
            if _field_collection_includes_status(mapping.get(key)):
                return True

        changes = mapping.get("changes") or mapping.get("changedFields")
        if isinstance(changes, Mapping):
            if any(_is_status_field(field) for field in changes):
                return True
        elif _field_collection_includes_status(changes):
            return True

    return False


def _field_collection_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        return any(_is_status_field(field) for field in value)
    if isinstance(value, Iterable):
        return any(_is_status_field(field) for field in value)
    return False


def _is_status_field(value: Any) -> bool:
    compact = _normalize_words(value).replace(" ", "")
    return compact in {"status", "state", "workflowstate"}


def _first_status_value(mappings: Iterable[Mapping[str, Any]]) -> str | None:
    mapping_list = list(mappings)

    for key in ("newStatus", "new_status", "newState", "new_state", "toStatus", "to_status"):
        value = _first_value(mapping_list, key)
        status = _status_name(value)
        if status:
            return status

    for mapping in mapping_list:
        changes = mapping.get("changes")
        if not isinstance(changes, Mapping):
            continue
        for field in ("status", "state", "workflowState", "workflow_state"):
            if field not in changes:
                continue
            status = _changed_status_name(changes[field])
            if status:
                return status

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _first_value(mapping_list, key)
        status = _status_name(value)
        if status:
            return status

    return None


def _changed_status_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "new", "after", "current", "name"):
            status = _status_name(value.get(key))
            if status:
                return status
    return _status_name(value)


def _status_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state"):
            status = _status_name(value.get(key))
            if status:
                return status
        return None
    if value is None:
        return None
    status = str(value).strip()
    return status or None


def _first_issue_id(event: Mapping[str, Any]) -> str | None:
    for mapping in _priority_mappings(event):
        for key in ("issueId", "issue_id", "identifier", "key", "id"):
            value = mapping.get(key)
            if value is None:
                continue
            issue_id = str(value).strip()
            if issue_id:
                return issue_id
    return None


def _first_title(event: Mapping[str, Any]) -> str | None:
    for mapping in _priority_mappings(event):
        value = mapping.get("title")
        if value is None:
            continue
        title = str(value).strip()
        if title:
            return title
    return None


def _priority_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    priority: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        priority.append(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            priority.append(issue)
        priority.append(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        priority.append(issue)

    priority.append(event)
    return priority


def _first_value(mappings: Iterable[Mapping[str, Any]], key: str) -> Any:
    for mapping in mappings:
        if key in mapping:
            return mapping[key]
    return None


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested in value.values():
            yield from _walk_mappings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_mappings(nested)


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
