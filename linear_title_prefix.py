"""Build Linear issue title updates for research-status automation triggers."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to "to research"."""
    if not isinstance(event, Mapping):
        return None

    contexts = list(_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    status = _new_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(contexts, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely metadata and issue objects from flat or nested webhook payloads."""
    yield event

    trigger_context = _mapping_value(event, "triggerContext", "trigger_context")
    if trigger_context:
        yield trigger_context

    issue = _mapping_value(event, "issue")
    if issue:
        yield issue

    data = _mapping_value(event, "data")
    if data:
        yield data
        data_issue = _mapping_value(data, "issue")
        if data_issue:
            yield data_issue

    changes = _mapping_value(event, "changes", "updatedFrom")
    if changes:
        yield changes


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    event_names = _event_names(contexts)
    if any(name in {"status changed", "state changed", "workflow state changed"} for name in event_names):
        return True

    if any(name in {"update", "updated", "issue updated", "updated issue"} for name in event_names):
        return _has_status_updated_field(contexts)

    return False


def _event_names(contexts: Iterable[Mapping[str, Any]]) -> set[str]:
    names: set[str] = set()
    for context in contexts:
        for key in ("trigger", "webhookType", "webhook_type", "action", "type", "event"):
            value = context.get(key)
            if isinstance(value, str):
                names.add(_normalize(value))
    return names


def _has_status_updated_field(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = context.get(key)
            if _field_collection_contains_status(fields):
                return True

        changes = _mapping_value(context, "changes", "updatedFrom")
        if changes and any(_normalize_field_name(field) in STATUS_FIELDS for field in changes):
            return True

    return False


def _field_collection_contains_status(fields: Any) -> bool:
    if isinstance(fields, str):
        return _normalize_field_name(fields) in STATUS_FIELDS

    if isinstance(fields, Mapping):
        return any(_normalize_field_name(field) in STATUS_FIELDS for field in fields)

    if isinstance(fields, Iterable):
        return any(_normalize_field_name(field) in STATUS_FIELDS for field in fields)

    return False


def _new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    explicit = _first_text(
        contexts,
        (
            "newStatus",
            "new_status",
            "statusName",
            "status_name",
            "newState",
            "new_state",
            "stateName",
            "state_name",
            "workflowStateName",
            "workflow_state_name",
        ),
    )
    if explicit:
        return explicit

    changed_status = _status_from_changes(contexts)
    if changed_status:
        return changed_status

    return _first_text(contexts, ("status", "state", "workflowState", "workflow_state"))


def _status_from_changes(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        changes = _mapping_value(context, "changes", "updatedFrom")
        if not changes:
            continue

        for key, change in changes.items():
            if _normalize_field_name(key) not in STATUS_FIELDS:
                continue

            text = _text_from_change(change)
            if text:
                return text

    return None


def _text_from_change(change: Any) -> str | None:
    if isinstance(change, str):
        return change

    if not isinstance(change, Mapping):
        return None

    for key in ("to", "after", "new", "newValue", "new_value"):
        text = _text_value(change.get(key))
        if text:
            return text

    return _text_value(change)


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            text = _text_value(context.get(key))
            if text:
                return text
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _text_value(value.get(key))
            if text:
                return text

    return None


def _mapping_value(mapping: Mapping[str, Any], *keys: str) -> Mapping[str, Any] | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, Mapping):
            return value
    return None


def _normalize(value: str | None) -> str:
    if not value:
        return ""

    with_camel_boundaries = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", with_camel_boundaries)
    return re.sub(r"\s+", " ", normalized).strip().lower()


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _normalize(value).replace(" ", "")


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
