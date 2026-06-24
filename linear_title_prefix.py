"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    contexts = list(_event_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    status = _first_status(contexts)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    title = _first_text(contexts, ("title",))
    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    if not title or not issue_id:
        return None

    title = title.strip()
    issue_id = issue_id.strip()
    if not title or not issue_id or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _event_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    yield event

    trigger_context = _mapping_at(event, "triggerContext")
    if trigger_context:
        yield trigger_context

    automation_info = _mapping_at(event, "automation_trigger_info")
    automation_context = _mapping_at(automation_info, "triggerContext") if automation_info else None
    if automation_context:
        yield automation_context

    for source in (event, trigger_context, automation_context):
        if not source:
            continue

        issue = _mapping_at(source, "issue")
        data = _mapping_at(source, "data")
        data_issue = _mapping_at(data, "issue") if data else None

        if issue:
            yield _merged(issue, source)
        if data:
            yield _merged(data, source)
        if data_issue:
            yield _merged(data_issue, data, source)


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    context_list = list(contexts)
    trigger_values = [
        value
        for context in context_list
        for key in ("trigger", "webhookType", "action", "type")
        if (value := _text_value(context.get(key)))
    ]

    normalized_triggers = {_normalize_words(value) for value in trigger_values}
    if normalized_triggers & {"status changed", "status change"}:
        return True

    update_triggers = {"update", "updated", "issue updated", "updated issue", "issue update", "update issue"}
    if normalized_triggers & update_triggers:
        return any(_status_marked_as_changed(context) for context in context_list)

    return False


def _status_marked_as_changed(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields")
    if isinstance(updated_fields, Iterable) and not isinstance(updated_fields, (str, bytes, Mapping)):
        if any(_is_status_field(field) for field in updated_fields):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_is_status_field(key) for key in changes)
    if isinstance(changes, Iterable) and not isinstance(changes, (str, bytes)):
        return any(_is_status_field(change) for change in changes)

    for key in ("changedField", "changed_field", "field"):
        if _is_status_field(context.get(key)):
            return True

    return False


def _first_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    context_list = list(contexts)
    explicit_keys = (
        "newStatus",
        "new_status",
        "newStatusName",
        "new_status_name",
        "statusName",
        "status_name",
    )

    for context in context_list:
        if value := _first_text((context,), explicit_keys):
            return value

    for context in context_list:
        for key in ("status", "state", "workflowState", "workflow_state"):
            if value := _text_value(context.get(key)):
                return value

    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            if value := _text_value(context.get(key)):
                return value
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, Mapping):
        for key in ("name", "title", "displayName", "label", "id", "identifier"):
            if text := _text_value(value.get(key)):
                return text
    return None


def _is_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        value = value.get("field") or value.get("name") or value.get("key")
    normalized = _normalize_words(_text_value(value))
    return normalized in STATUS_FIELD_NAMES


def _normalize_words(value: str | None) -> str | None:
    if not value:
        return None

    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return " ".join(value.casefold().split())


def _has_research_prefix(title: str) -> bool:
    return title.lstrip().casefold().startswith(PREFIX.casefold())


def _mapping_at(mapping: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if not isinstance(mapping, Mapping):
        return None
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else None


def _merged(*mappings: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for mapping in mappings:
        result.update(mapping)
    return result


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
