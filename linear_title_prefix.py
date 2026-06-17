"""Build Linear issue title updates for Cursor research status changes.

The automation receives webhook-like issue payloads and returns a small action
object that a caller can use to update the Linear issue title. It is intentionally
side-effect free so it can be tested without a Linear API token.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {
    "status",
    "state",
    "state id",
    "stateid",
    "workflow state",
    "workflow state id",
    "workflowstate",
    "workflowstateid",
}
DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "state changed",
    "workflow state changed",
}
GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action for target status transitions.

    The returned action has this shape:

    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``

    ``None`` means the payload does not represent an issue moving into the
    "to research" status or the title is already prefixed.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _collect_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_string(contexts, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _extract_first_string(contexts, ("title", "name"))
    if issue_id is None or title is None:
        return None

    clean_title = title.strip()
    if not clean_title or _has_research_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{RESEARCH_PREFIX}: {clean_title}",
    }


def _collect_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely payload contexts in priority order for issue fields."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping):
            contexts.append(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")

    add(trigger_context)
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("issue"))
        add(trigger_context.get("data"))

    if isinstance(data, Mapping):
        add(data.get("issue"))
    add(issue)
    add(data)
    add(event)

    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    values = [
        value
        for context in contexts
        for key in ("trigger", "webhookType", "eventType", "action", "type")
        if (value := context.get(key)) is not None
    ]
    normalized_values = {_normalize_text(value) for value in values}

    if normalized_values & DIRECT_STATUS_TRIGGERS:
        return True

    if normalized_values & GENERIC_UPDATE_EVENTS:
        return any(_mentions_status_change(context) for context in contexts)

    return False


def _mentions_status_change(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = _normalize_text(key)
            if normalized_key in {
                "updated fields",
                "changed fields",
                "changes",
                "updated from",
                "updatedfrom",
            }:
                if _contains_status_field(child):
                    return True
        return False

    if isinstance(value, (list, tuple, set)):
        return any(_mentions_status_change(item) for item in value)

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            _normalize_text(key) in STATUS_FIELD_NAMES or _contains_status_field(child)
            for key, child in value.items()
        )

    if isinstance(value, (list, tuple, set)):
        return any(_contains_status_field(item) for item in value)

    return _normalize_text(value) in STATUS_FIELD_NAMES


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    direct_status_keys = (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    direct = _extract_first_string(contexts, direct_status_keys)
    if direct is not None:
        return direct

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = context.get(key)
            status = _status_name_from_value(value)
            if status is not None:
                return status

    return None


def _status_name_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return _extract_first_string([value], ("name", "title", "label"))
    return None


def _extract_first_string(
    contexts: Iterable[Mapping[str, Any]],
    keys: Iterable[str],
) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _has_research_prefix(title: str) -> bool:
    return re.match(r"^\s*cursor\s+researching\b", title, flags=re.IGNORECASE) is not None


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def main() -> int:
    payload = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(payload), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
