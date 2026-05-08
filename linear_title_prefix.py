"""Build Linear issue title updates for Cursor research automations."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any


PREFIX = "Cursor researching"
_CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_SEPARATORS = re.compile(r"[_\-/]+")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update when a Linear issue moves to To Research.

    The automation host passes status-change metadata in ``triggerContext``,
    while raw Linear webhooks usually place issue data under ``data``. This
    function accepts both shapes and returns a small command object that a
    caller can use to update the issue title.
    """

    if not isinstance(event, Mapping):
        return None

    issue = _issue_context(event)
    if not _is_status_change_event(issue):
        return None

    if _normalise_text(_new_status(issue)) != "to research":
        return None

    issue_id = _first_text(issue, ("issueId", "issue_id", "id", "identifier"))
    title = _first_text(issue, ("title",))
    if not issue_id or not title:
        return None

    if _normalise_text(title).startswith(_normalise_text(PREFIX)):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _issue_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common automation and Linear webhook issue payload shapes."""

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
        "workflow status changed",
        "workflow state changed",
    }

    if any(_normalise_text(issue.get(name)) in status_change_names for name in trigger_names):
        return True

    update_names = {
        "update",
        "updated",
        "issue updated",
        "updated issue",
        "update issue",
        "issue update",
    }
    has_issue_update_name = any(
        _normalise_text(issue.get(name)) in update_names for name in trigger_names
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
        updated_from = issue.get("updatedFrom", issue.get("updated_from"))
        if not isinstance(updated_from, Mapping):
            return False
        fields = updated_from.keys()

    status_fields = {"status", "status id", "state", "state id", "workflow state"}
    return any(_normalise_text(field) in status_fields for field in fields)


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


def _normalise_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = _CAMEL_CASE_BOUNDARY.sub(" ", text)
    text = _SEPARATORS.sub(" ", text)
    return " ".join(text.casefold().split())
