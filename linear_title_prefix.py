"""Build Linear issue title updates for Cursor research automations."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_SEPARATORS = re.compile(r"[^A-Za-z0-9]+")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update when a Linear issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    issue = _issue_context(event)
    if not _is_status_change_event(issue):
        return None

    if _normalize_words(_new_status(issue)) != TARGET_STATUS:
        return None

    issue_id = _first_text(issue, ("issueId", "issue_id", "id", "identifier"))
    title = _first_text(issue, ("title",))
    if not issue_id or not title:
        return None

    if _normalize_words(title).startswith(_normalize_words(PREFIX)):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _issue_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Cursor automation and Linear webhook issue payload shapes."""
    context: dict[str, Any] = {}

    def merge(mapping: Mapping[str, Any] | None) -> None:
        if isinstance(mapping, Mapping):
            context.update(mapping)

    issue = event.get("issue")
    merge(issue if isinstance(issue, Mapping) else None)

    data = event.get("data")
    if isinstance(data, Mapping):
        nested_issue = data.get("issue")
        merge(nested_issue if isinstance(nested_issue, Mapping) else None)
        merge(data)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        nested_data = trigger_context.get("data")
        if isinstance(nested_data, Mapping):
            nested_issue = nested_data.get("issue")
            merge(nested_issue if isinstance(nested_issue, Mapping) else None)
            merge(nested_data)

        nested_issue = trigger_context.get("issue")
        merge(nested_issue if isinstance(nested_issue, Mapping) else None)
        merge(trigger_context)

    for key, value in event.items():
        if key in {"data", "issue", "triggerContext"}:
            continue
        context.setdefault(key, value)

    return context


def _is_status_change_event(issue: Mapping[str, Any]) -> bool:
    trigger_names = (
        "trigger",
        "action",
        "type",
        "event",
        "webhookType",
        "webhook_type",
    )
    status_change_names = {
        "status changed",
        "status change",
        "state changed",
        "state change",
        "issue status changed",
        "workflow status changed",
        "workflow state changed",
    }

    if any(_normalize_words(issue.get(name)) in status_change_names for name in trigger_names):
        return True

    update_names = {
        "issue updated",
        "updated issue",
        "update issue",
        "issue update",
    }
    has_issue_update_name = any(
        _normalize_words(issue.get(name)) in update_names for name in trigger_names
    )
    return has_issue_update_name and _updated_fields_include_status(issue)


def _updated_fields_include_status(issue: Mapping[str, Any]) -> bool:
    updated_fields = issue.get("updatedFields", issue.get("updated_fields"))
    if isinstance(updated_fields, str):
        fields = [updated_fields]
    elif isinstance(updated_fields, Mapping):
        fields = updated_fields.keys()
    elif isinstance(updated_fields, (list, tuple, set)):
        fields = updated_fields
    else:
        return False

    return any(_normalize_words(field) in {"status", "state"} for field in fields)


def _new_status(issue: Mapping[str, Any]) -> Any:
    for key in ("newStatus", "new_status", "newState", "new_state", "status"):
        value = issue.get(key)
        if value:
            return _state_name(value)

    return _state_name(issue.get("state"))


def _state_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        return value.get("name")
    return value


def _first_text(issue: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = issue.get(key)
        if value is None:
            continue

        text = str(value).strip()
        if text:
            return text

    return None


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = _CAMEL_CASE_BOUNDARY.sub(" ", text)
    text = _SEPARATORS.sub(" ", text)
    return " ".join(text.casefold().split())
