"""Build Linear issue title updates for research status transitions.

The automation receives slightly different payload shapes depending on whether
it is invoked by Cursor trigger metadata or by a Linear-style webhook. This
module keeps the side effect outside the handler and returns the update that a
caller should apply.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state updated",
    "workflow state changed",
    "workflow state updated",
}
_GENERIC_UPDATE_EVENTS = {
    "issue updated",
    "updated issue",
    "update",
    "updated",
}
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "workflowstate",
    "workflow status",
    "workflowstatus",
    "state id",
    "stateid",
    "status id",
    "statusid",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when the issue moves to research.

    The returned object is intentionally simple so callers can bridge it to the
    Linear API or any surrounding automation runner:

    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _new_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {stripped_title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return relevant mappings ordered from most automation-specific to broad."""

    contexts: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)

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


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    event_labels = {
        _normalize(value)
        for context in contexts
        for key in ("trigger", "webhookType", "webhook_type", "action", "type")
        if (value := context.get(key)) is not None
    }

    if event_labels & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    if event_labels & _GENERIC_UPDATE_EVENTS:
        return _updated_fields_include_status(contexts)

    return False


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
            "changedProperties",
            "changed_properties",
            "updatedProperties",
            "updated_properties",
        ):
            if _field_names_include_status(context.get(key)):
                return True

        for key in ("changes", "changed", "updatedFrom", "updated_from"):
            value = context.get(key)
            if isinstance(value, Mapping) and _field_names_include_status(value.keys()):
                return True

    return False


def _field_names_include_status(value: Any) -> bool:
    if value is None:
        return False

    if isinstance(value, Mapping):
        names: Iterable[Any] = value.keys()
    elif isinstance(value, str):
        names = (value,)
    elif isinstance(value, Iterable):
        names = value
    else:
        return False

    for item in names:
        if isinstance(item, Mapping):
            candidate = _first_text([item], ("field", "name", "key", "property"))
        else:
            candidate = str(item)
        normalized = _normalize(candidate)
        if normalized in _STATUS_FIELD_NAMES:
            return True
    return False


def _new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit_status_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "statusName",
        "status_name",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
    )
    fallback_status_keys = ("status", "state", "workflowState", "workflow_state")

    for key_group in (explicit_status_keys, fallback_status_keys):
        for context in contexts:
            for key in key_group:
                status = _text_from_value(context.get(key))
                if status:
                    return status

    return None


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _text_from_value(context.get(key))
            if value:
                return value
    return None


def _text_from_value(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "identifier", "key", "id"):
            text = _text_from_value(value.get(key))
            if text:
                return text
        return None

    text = str(value).strip()
    return text or None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize(value: Any) -> str:
    text = _text_from_value(value)
    if not text:
        return ""

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def main() -> int:
    """Read an event JSON object from stdin and print the title update action."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
