"""Build Linear issue-title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}
UPDATED_FIELDS_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
)
CHANGE_KEYS = ("changes", "changed", "previousValues", "previous_values")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    context = _issue_context(event)
    if not context:
        return None

    if not _is_status_change_event(event, context):
        return None

    status = _extract_new_status(event, context)
    if _normalize_text(status) != RESEARCH_STATUS:
        return None

    issue_id = _string_value(_first_present(context, ("issueId", "issue_id", "id", "identifier", "key")))
    title = _string_value(_first_present(context, ("title", "name")))
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _issue_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor/Linear payload layers into one lookup context."""

    context: dict[str, Any] = {}
    for candidate in _candidate_mappings(event):
        context.update(candidate)
    return context


def _candidate_mappings(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, Mapping):
        return []

    candidates: list[Mapping[str, Any]] = []
    for key in ("triggerContext", "webhook", "data", "issue", "node"):
        nested = value.get(key)
        if isinstance(nested, Mapping):
            candidates.extend(_candidate_mappings(nested))

    candidates.append(value)
    return candidates


def _is_status_change_event(event: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    event_names = [
        value
        for mapping in _candidate_mappings(event)
        for value in _values_for_keys(mapping, ("trigger", "webhookType", "action", "type"))
    ]

    normalized_names = {_normalize_text(value) for value in event_names if value is not None}
    if any(name in {"status changed", "status change", "status updated"} for name in normalized_names):
        return True

    if any(name in {"issue updated", "updated issue", "update"} for name in normalized_names):
        return _updated_fields_include_status(event) or _changes_include_status(event)

    if _updated_fields_include_status(event) or _changes_include_status(event):
        return True

    # Cursor's flat trigger payload for this automation includes a dedicated
    # status-change trigger, but some tests and local invocations only provide
    # the new status field. Treat that as a status change when no event name is
    # available.
    return not normalized_names and _extract_new_status(event, context) is not None


def _extract_new_status(event: Mapping[str, Any], context: Mapping[str, Any]) -> str | None:
    explicit_status = _first_present(
        context,
        (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "newWorkflowState",
            "new_workflow_state",
        ),
    )
    if explicit_status is not None:
        return _status_name(explicit_status)

    change_status = _status_from_changes(event)
    if change_status is not None:
        return change_status

    for key in ("status", "state", "workflowState", "workflow_state"):
        status = _status_name(context.get(key))
        if status is not None:
            return status

    return None


def _status_from_changes(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in CHANGE_KEYS:
            changes = value.get(key)
            if isinstance(changes, Mapping):
                for field, change in changes.items():
                    if not _is_status_field(field):
                        continue
                    status = _status_name(_new_change_value(change))
                    if status is not None:
                        return status

        for nested in value.values():
            status = _status_from_changes(nested)
            if status is not None:
                return status

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            status = _status_from_changes(item)
            if status is not None:
                return status

    return None


def _new_change_value(change: Any) -> Any:
    if not isinstance(change, Mapping):
        return change

    for key in ("newValue", "new_value", "to", "after", "new", "value"):
        if key in change:
            return change[key]
    return change


def _updated_fields_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key in UPDATED_FIELDS_KEYS:
            fields = value.get(key)
            if _fields_include_status(fields):
                return True
        return any(_updated_fields_include_status(nested) for nested in value.values())

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_updated_fields_include_status(item) for item in value)

    return False


def _changes_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key in CHANGE_KEYS:
            changes = value.get(key)
            if isinstance(changes, Mapping) and any(_is_status_field(field) for field in changes):
                return True
            if _fields_include_status(changes):
                return True
        return any(_changes_include_status(nested) for nested in value.values())

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_changes_include_status(item) for item in value)

    return False


def _fields_include_status(fields: Any) -> bool:
    if fields is None:
        return False
    if isinstance(fields, str):
        return _is_status_field(fields)
    if isinstance(fields, Mapping):
        return any(_is_status_field(key) for key in fields)
    if isinstance(fields, Sequence):
        return any(_fields_include_status(field) for field in fields)
    return False


def _is_status_field(field: Any) -> bool:
    return _normalize_text(field) in STATUS_FIELDS


def _status_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            status = _string_value(value.get(key))
            if status:
                return status
        return None
    return _string_value(value)


def _values_for_keys(mapping: Mapping[str, Any], keys: Sequence[str]) -> list[Any]:
    values: list[Any] = []
    for key in keys:
        if key in mapping:
            values.append(mapping[key])
    return values


def _first_present(mapping: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _string_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
