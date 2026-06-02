"""Build Linear issue title updates for research-status automation triggers."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow status"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research.

    The automation receives either a flattened trigger context or a nested
    Linear webhook payload. This function keeps side effects outside the module
    and returns the update command that the automation runner can apply.
    """
    if not isinstance(event, Mapping):
        return None

    contexts = list(_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    status = _new_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    title = _string_value(_first_value(contexts, ("title", "name")))
    issue_id = _string_value(
        _first_value(contexts, ("id", "issueId", "issue_id", "identifier"))
    )
    if not title or not issue_id:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely payload containers, from most specific to broadest."""
    yield event

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield trigger_context

    data = event.get("data")
    if isinstance(data, Mapping):
        yield data

        issue = data.get("issue")
        if isinstance(issue, Mapping):
            yield issue

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = []
    updated_fields: Any = None

    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            value = _string_value(context.get(key))
            if value:
                trigger_values.append(_normalize(value))

        if updated_fields is None:
            updated_fields = context.get("updatedFields") or context.get("updated_fields")

    if any(value == "status changed" for value in trigger_values):
        return True

    if any(value in {"issue updated", "updated issue", "update"} for value in trigger_values):
        return _includes_status_field(updated_fields)

    return False


def _includes_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize(value) in STATUS_FIELDS

    if isinstance(value, Mapping):
        return any(_normalize(key) in STATUS_FIELDS for key in value)

    if isinstance(value, Iterable):
        return any(_includes_status_field(item) for item in value)

    return False


def _new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    explicit = _string_value(_first_value(contexts, explicit_keys))
    if explicit:
        return explicit

    status = _status_name(_first_value(contexts, ("status", "state", "workflowState")))
    if status:
        return status

    return _string_value(_first_value(contexts, ("status",)))


def _status_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _string_value(value.get("name") or value.get("title"))

    return _string_value(value)


def _first_value(contexts: list[Mapping[str, Any]], keys: Iterable[str]) -> Any:
    for context in contexts:
        for key in keys:
            if key in context and context[key] is not None:
                return context[key]

    return None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", words)


def main() -> int:
    """Read an event JSON document from stdin and print the update action."""
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
