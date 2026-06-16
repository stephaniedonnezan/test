"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
ACTION = "update_issue_title"

_STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}
_DIRECT_STATUS_CHANGE_EVENTS = {"status changed", "status change"}
_ISSUE_UPDATE_EVENTS = {"update", "updated", "issue update", "issue updated", "updated issue"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to "to research"."""
    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _new_status(event)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _issue_id(event)
    title = _issue_title(event)
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_names = {_normalize(value) for value in _event_name_values(event)}
    if event_names & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    return bool(event_names & _ISSUE_UPDATE_EVENTS) and _status_field_changed(event)


def _event_name_values(event: Mapping[str, Any]) -> Iterable[Any]:
    for context in _metadata_contexts(event):
        for key in ("trigger", "webhookType", "action", "type"):
            value = context.get(key)
            if value is not None:
                yield value


def _metadata_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts = [event]
    for key in ("triggerContext", "data", "webhook", "payload"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            contexts.append(nested)
    return contexts


def _status_field_changed(event: Mapping[str, Any]) -> bool:
    for context in _metadata_contexts(event) + _issue_contexts(event):
        if _updated_fields_include_status(context.get("updatedFields")):
            return True
        if _updated_fields_include_status(context.get("updated_fields")):
            return True

        changes = context.get("changes")
        if isinstance(changes, Mapping) and any(_is_status_field(key) for key in changes):
            return True

    return False


def _updated_fields_include_status(updated_fields: Any) -> bool:
    if isinstance(updated_fields, str):
        return _is_status_field(updated_fields)

    if not isinstance(updated_fields, Iterable) or isinstance(updated_fields, (bytes, Mapping)):
        return False

    for field in updated_fields:
        if isinstance(field, Mapping):
            values = field.values()
        else:
            values = (field,)

        if any(_is_status_field(value) for value in values):
            return True

    return False


def _is_status_field(value: Any) -> bool:
    return _normalize(value) in _STATUS_FIELDS


def _new_status(event: Mapping[str, Any]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "statusChangedTo",
        "status_changed_to",
        "newState",
        "new_state",
        "toState",
        "to_state",
        "newWorkflowState",
        "new_workflow_state",
    )

    for context in _metadata_contexts(event) + _issue_contexts(event):
        value = _first_string_value(context, explicit_keys)
        if value:
            return value

    for context in _metadata_contexts(event) + _issue_contexts(event):
        value = _first_string_value(context, ("status", "state", "workflowState", "workflow_state"))
        if value:
            return value

    return None


def _issue_id(event: Mapping[str, Any]) -> str | None:
    return _first_value_from_contexts(
        event,
        ("issueId", "issue_id", "identifier", "key", "id"),
        require_issue_context_for_id=True,
    )


def _issue_title(event: Mapping[str, Any]) -> str | None:
    return _first_value_from_contexts(event, ("title",))


def _first_value_from_contexts(
    event: Mapping[str, Any],
    keys: tuple[str, ...],
    *,
    require_issue_context_for_id: bool = False,
) -> str | None:
    for context in _issue_contexts(event):
        value = _first_string_value(context, keys)
        if value:
            return value

    if require_issue_context_for_id and _has_issue_context(event):
        return None

    return _first_string_value(event, keys)


def _issue_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)

    for path in (
        ("data", "issue"),
        ("payload", "issue"),
        ("issue",),
        ("data",),
    ):
        value = _nested_mapping(event, path)
        if value is not None and value not in contexts:
            contexts.append(value)

    if not contexts:
        contexts.append(event)

    return contexts


def _has_issue_context(event: Mapping[str, Any]) -> bool:
    return any(
        _nested_mapping(event, path) is not None
        for path in (
            ("triggerContext",),
            ("data", "issue"),
            ("payload", "issue"),
            ("issue",),
        )
    )


def _nested_mapping(event: Mapping[str, Any], path: tuple[str, ...]) -> Mapping[str, Any] | None:
    value: Any = event
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)

    return value if isinstance(value, Mapping) else None


def _first_string_value(context: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        if key not in context:
            continue

        value = context[key]
        if isinstance(value, Mapping):
            value = _first_string_value(value, ("name", "title", "status", "state"))

        if value is None:
            continue

        value = str(value).strip()
        if value:
            return value

    return None


def _has_research_prefix(title: str) -> bool:
    return re.match(r"^\s*cursor researching\b", title, re.IGNORECASE) is not None


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        json.dump(action, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
