"""Build Linear issue title update actions for research-status changes.

The automation receives slightly different Linear/Cursor payload shapes
depending on the trigger source.  This module keeps the behavior isolated and
returns a small action object that the surrounding automation can execute.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}
DIRECT_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when the event enters research."""

    if not isinstance(event, Mapping):
        return None

    contexts = list(_candidate_mappings(event))
    if not _is_research_status_change(contexts):
        return None

    issue = _merged_issue_data(contexts)
    issue_id = _clean_text(_first_present(issue, ("issueId", "issue_id", "id", "identifier", "key")))
    title = _clean_text(_first_present(issue, ("title", "name")))

    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_research_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    status = _extract_new_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return False

    triggers = {
        normalized
        for context in contexts
        for key in ("trigger", "webhookType", "action", "type", "event")
        if (normalized := _normalize(context.get(key)))
    }
    if triggers & DIRECT_STATUS_CHANGE_TRIGGERS:
        return True

    return bool(triggers & GENERIC_UPDATE_TRIGGERS) and _status_field_was_updated(contexts)


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> Any:
    explicit_status_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )

    for context in contexts:
        value = _first_present(context, explicit_status_keys)
        if value is not None:
            return value

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = context.get(key)
            if isinstance(value, Mapping):
                nested_value = _first_present(value, ("name", "title", "id", "key"))
                if nested_value is not None:
                    return nested_value
            elif value is not None:
                return value

    return None


def _status_field_was_updated(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        updated_fields = context.get("updatedFields") or context.get("updated_fields")
        if _contains_status_field(updated_fields):
            return True

        changes = context.get("changes") or context.get("changed") or context.get("updates")
        if _changes_include_status(changes):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _field_name(value) in STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(_field_name(key) in STATUS_FIELD_NAMES for key in value)

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _changes_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        if _contains_status_field(value):
            return True
        return any(_changes_include_status(item) for item in value.values())

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_changes_include_status(item) for item in value)

    return False


def _candidate_mappings(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield useful nested maps without recursively mixing unrelated objects."""

    seen: set[int] = set()
    queue: list[Mapping[str, Any]] = [event]

    while queue:
        current = queue.pop(0)
        current_id = id(current)
        if current_id in seen:
            continue
        seen.add(current_id)
        yield current

        for key in (
            "automation_trigger_info",
            "triggerContext",
            "trigger_context",
            "data",
            "payload",
            "webhook",
            "issue",
        ):
            nested = current.get(key)
            if isinstance(nested, Mapping):
                queue.append(nested)


def _merged_issue_data(contexts: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    issue: dict[str, Any] = {}
    for context in reversed(list(contexts)):
        issue.update(context)
        for key in ("issue", "data", "payload"):
            nested = context.get(key)
            if isinstance(nested, Mapping):
                issue.update(nested)
    return issue


def _first_present(mapping: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            return value
    return None


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _field_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _normalize(value))


def _normalize(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
