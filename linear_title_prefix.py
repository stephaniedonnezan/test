"""Build Linear issue title updates for research status transitions.

The public entry point is ``build_issue_title_update``. It accepts a Linear or
Cursor automation event payload and returns an update action when an issue moves
to the "to research" status.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_ISSUE_TITLE_KEYS = ("title", "issueTitle", "issue_title")
_TRIGGER_KEYS = ("trigger", "webhookType", "webhook_type", "action", "type", "eventType", "event_type")
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "newState",
    "new_state",
    "toState",
    "to_state",
    "newWorkflowState",
    "new_workflow_state",
    "newWorkflowStateName",
    "new_workflow_state_name",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_CURRENT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_UPDATED_FIELD_KEYS = ("updatedFields", "updated_fields", "changedFields", "changed_fields")
_CHANGE_KEYS = ("changes", "change", "changed")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action for issues transitioning to "to research".

    The returned action has this shape::

        {
            "action": "update_issue_title",
            "issueId": "POI-123",
            "title": "Cursor researching: Original title",
        }

    ``None`` is returned for payloads that do not represent a status change to
    the target status, are missing required issue data, or are already prefixed.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if not _status_changed_to_target(event):
        return None

    issue_id = _first_text(_issue_contexts(event), _ISSUE_ID_KEYS)
    title = _first_text(_issue_contexts(event), _ISSUE_TITLE_KEYS)

    if not issue_id or not title:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    if _has_status_change_trigger(event):
        return True

    if _has_explicit_status_destination(event):
        return True

    if _updated_fields_include_status(event):
        return True

    return _changes_include_status(event)


def _status_changed_to_target(event: Mapping[str, Any]) -> bool:
    for status in _status_destinations(event):
        if _normalize_phrase(status) == TARGET_STATUS:
            return True
    return False


def _status_destinations(event: Mapping[str, Any]) -> Iterable[str]:
    for context in _status_contexts(event):
        for key in _EXPLICIT_STATUS_KEYS:
            if key in context:
                value = _text_from_value(context[key])
                if value:
                    yield value

    yield from _status_destinations_from_changes(event)

    for context in _issue_contexts(event):
        for key in _CURRENT_STATUS_KEYS:
            if key in context:
                value = _text_from_value(context[key])
                if value:
                    yield value


def _has_status_change_trigger(event: Mapping[str, Any]) -> bool:
    for context in _status_contexts(event):
        for key in _TRIGGER_KEYS:
            if key not in context:
                continue

            trigger = _normalize_phrase(context[key])
            if trigger in {"status changed", "state changed", "workflow state changed"}:
                return True

            if "status changed" in trigger or "state changed" in trigger or "workflow state changed" in trigger:
                return True

    return False


def _has_explicit_status_destination(event: Mapping[str, Any]) -> bool:
    return any(key in context for context in _status_contexts(event) for key in _EXPLICIT_STATUS_KEYS)


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for context in _status_contexts(event):
        for key in _UPDATED_FIELD_KEYS:
            fields = context.get(key)
            if fields is None:
                continue
            if any(_is_status_field(field) for field in _as_iterable(fields)):
                return True
    return False


def _changes_include_status(event: Mapping[str, Any]) -> bool:
    for context in _status_contexts(event):
        for key in _CHANGE_KEYS:
            if _change_payload_includes_status(context.get(key)):
                return True
    return False


def _change_payload_includes_status(change_payload: Any) -> bool:
    if isinstance(change_payload, Mapping):
        for key, value in change_payload.items():
            if _is_status_field(key):
                return True

            if isinstance(value, Mapping):
                field = value.get("field") or value.get("name") or value.get("key")
                if _is_status_field(field):
                    return True

        return False

    if isinstance(change_payload, list | tuple):
        for item in change_payload:
            if isinstance(item, Mapping):
                field = item.get("field") or item.get("name") or item.get("key")
                if _is_status_field(field):
                    return True
            elif _is_status_field(item):
                return True

    return False


def _status_destinations_from_changes(event: Mapping[str, Any]) -> Iterable[str]:
    for context in _status_contexts(event):
        for key in _CHANGE_KEYS:
            change_payload = context.get(key)
            if change_payload is None:
                continue

            if isinstance(change_payload, Mapping):
                for field, change in change_payload.items():
                    if _is_status_field(field):
                        value = _destination_from_change(change)
                        if value:
                            yield value
                    elif isinstance(change, Mapping):
                        field_name = change.get("field") or change.get("name") or change.get("key")
                        if _is_status_field(field_name):
                            value = _destination_from_change(change)
                            if value:
                                yield value

            elif isinstance(change_payload, list | tuple):
                for change in change_payload:
                    if not isinstance(change, Mapping):
                        continue
                    field = change.get("field") or change.get("name") or change.get("key")
                    if _is_status_field(field):
                        value = _destination_from_change(change)
                        if value:
                            yield value


def _destination_from_change(change: Any) -> str | None:
    if not isinstance(change, Mapping):
        return _text_from_value(change)

    for key in ("to", "new", "after", "value", "newValue", "new_value", "toString", "to_string", "toName", "to_name"):
        if key in change:
            value = _text_from_value(change[key])
            if value:
                return value

    return _text_from_value(change)


def _issue_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext") or event.get("trigger_context")
    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)
        issue = trigger_context.get("issue")
        if isinstance(issue, Mapping):
            contexts.append(issue)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            contexts.append(issue)
        contexts.append(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        contexts.append(issue)

    contexts.append(event)
    return contexts


def _status_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts = [event]

    trigger_context = event.get("triggerContext") or event.get("trigger_context")
    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        contexts.append(data)
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            contexts.append(issue)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        contexts.append(issue)

    return contexts


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            if key not in context:
                continue

            text = _text_from_value(context[key])
            if text:
                return text

    return None


def _text_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "value", "label"):
            if key in value:
                text = _text_from_value(value[key])
                if text:
                    return text

        return None

    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _as_iterable(value: Any) -> Iterable[Any]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Mapping):
        return value.keys()
    if isinstance(value, Iterable):
        return value
    return (value,)


def _is_status_field(value: Any) -> bool:
    field = _normalize_phrase(value)
    return (
        field in {"status", "state", "workflow state", "status id", "state id", "workflow state id"}
        or field.endswith(" status")
        or field.endswith(" state")
        or field.endswith(" status id")
        or field.endswith(" state id")
    )


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_phrase(value: Any) -> str:
    text = _text_from_value(value)
    if not text:
        return ""

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    """Read an event from stdin and print the matching title-update action."""

    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
