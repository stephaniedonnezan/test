"""Build Linear issue title update actions for Cursor research automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_status"}
STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "state changed",
    "workflow state changed",
    "workflow status changed",
}
ISSUE_UPDATE_TRIGGERS = {
    "issue updated",
    "updated issue",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters To Research."""

    if not isinstance(event, Mapping):
        return None

    candidates = _candidate_contexts(event)
    if not candidates:
        return None

    if not _is_status_change_event(candidates):
        return None

    new_status = _first_text(_new_status_values(candidates))
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(_field_values(candidates, ("issueId", "issue_id", "identifier", "key", "id")))
    title = _first_text(_field_values(candidates, ("title", "name")))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if _has_research_prefix(clean_title):
        prefixed_title = clean_title
    else:
        prefixed_title = f"{PREFIX}: {clean_title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": prefixed_title,
    }


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect likely trigger and issue objects from flat and nested payloads."""

    contexts: list[Mapping[str, Any]] = []

    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            contexts.append(value)
            for key in ("triggerContext", "data", "issue", "state", "workflowState", "workflowStatus"):
                nested = value.get(key)
                if isinstance(nested, Mapping):
                    visit(nested)

    visit(event)
    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    trigger_values = list(
        _field_values(contexts, ("trigger", "webhookType", "action", "type", "event", "eventType"))
    )
    normalized_triggers = {_normalize_text(value) for value in trigger_values}

    if normalized_triggers & STATUS_CHANGE_TRIGGERS:
        return True

    if normalized_triggers & ISSUE_UPDATE_TRIGGERS:
        return _has_changed_status_field(contexts)

    return False


def _has_changed_status_field(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "changedFields", "changed_fields"):
            fields = context.get(key)
            if _contains_status_field(fields):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            for field_name in changes:
                if _normalize_field_name(field_name) in STATUS_FIELDS:
                    return True
        elif isinstance(changes, Iterable) and not isinstance(changes, (str, bytes)):
            for change in changes:
                if isinstance(change, Mapping):
                    field_name = change.get("field") or change.get("fieldName") or change.get("name")
                    if _normalize_field_name(field_name) in STATUS_FIELDS:
                        return True

    return False


def _contains_status_field(fields: Any) -> bool:
    if isinstance(fields, Mapping):
        return any(_normalize_field_name(field) in STATUS_FIELDS for field in fields)

    if isinstance(fields, str):
        return _normalize_field_name(fields) in STATUS_FIELDS

    if isinstance(fields, Iterable):
        return any(_normalize_field_name(field) in STATUS_FIELDS for field in fields)

    return False


def _new_status_values(contexts: Iterable[Mapping[str, Any]]) -> Iterable[Any]:
    explicit_keys = (
        "newStatus",
        "new_status",
        "statusName",
        "stateName",
        "workflowStateName",
        "workflowStatusName",
    )

    yield from _field_values(contexts, explicit_keys)

    for context in contexts:
        changes = context.get("changes")
        if isinstance(changes, Mapping):
            for field_name, change in changes.items():
                if _normalize_field_name(field_name) in STATUS_FIELDS:
                    yield from _change_new_values(change)
        elif isinstance(changes, Iterable) and not isinstance(changes, (str, bytes)):
            for change in changes:
                if isinstance(change, Mapping):
                    field_name = change.get("field") or change.get("fieldName") or change.get("name")
                    if _normalize_field_name(field_name) in STATUS_FIELDS:
                        yield from _change_new_values(change)

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflowStatus"):
            value = context.get(key)
            if isinstance(value, Mapping):
                yield from _field_values((value,), ("name", "title"))
            else:
                yield value


def _change_new_values(change: Any) -> Iterable[Any]:
    if isinstance(change, Mapping):
        for key in ("newValue", "new_value", "to", "after", "value", "name"):
            value = change.get(key)
            if isinstance(value, Mapping):
                yield from _field_values((value,), ("name", "title"))
            else:
                yield value
    else:
        yield change


def _field_values(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> Iterable[Any]:
    key_lookup = {_normalize_field_name(key) for key in keys}
    for context in contexts:
        for key, value in context.items():
            if _normalize_field_name(key) in key_lookup:
                yield value


def _first_text(values: Iterable[Any]) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value
    return None


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    spaced = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return re.sub(r"\s+", " ", spaced).strip().lower()


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _has_research_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(PREFIX)}\b", title, flags=re.IGNORECASE) is not None


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    if action is None:
        return 0

    json.dump(action, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
