"""Build Linear issue title updates for research status transitions.

The automation receives Linear issue status-change events and emits a small
action object that the surrounding runner can use to update the issue title.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_CHANGE_MARKERS = {
    "status changed",
    "status change",
    "statuschanged",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}

_ISSUE_UPDATE_MARKERS = {
    "issue updated",
    "updated issue",
    "update",
    "updated",
}

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflow state",
    "workflow_status",
    "workflow status",
}


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a Linear title update action when the event enters research.

    The handler accepts both the Cursor automation trigger shape
    (``triggerContext`` at the top level) and common Linear webhook shapes where
    issue data is nested under ``data`` or ``issue``.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_candidate_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_phrase(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_string(contexts, ("id", "issueId", "issue_id", "identifier"))
    title = _extract_first_string(contexts, ("title",))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if _has_research_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield payload fragments from most issue-specific to least specific."""

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield trigger_context

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            yield issue
        yield data

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue

    yield event


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "webhookType", "triggerType", "eventType"):
            if _normalize_phrase(context.get(key)) in _STATUS_CHANGE_MARKERS:
                return True

    for context in contexts:
        for key in ("action", "type", "webhookType", "eventType"):
            if _normalize_phrase(context.get(key)) in _ISSUE_UPDATE_MARKERS:
                return _updated_fields_include_status(contexts)

    return False


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = context.get(key)
            if isinstance(fields, str):
                field_names = [fields]
            elif isinstance(fields, Iterable) and not isinstance(fields, (bytes, bytearray, str)):
                field_names = [field for field in fields if isinstance(field, str)]
            else:
                continue

            if any(_normalize_phrase(field) in _STATUS_FIELD_NAMES for field in field_names):
                return True

    return False


def _extract_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "toStatus",
        "to_status",
        "toState",
        "to_state",
        "statusName",
        "stateName",
        "workflowStateName",
    )
    status_keys = ("status", "state", "workflowState")

    for key_group in (explicit_keys, status_keys):
        for context in contexts:
            status = _extract_value_name(context, key_group)
            if status:
                return status

    return None


def _extract_value_name(context: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, Mapping):
            name = _extract_first_string([value], ("name", "title"))
            if name:
                return name

    return None


def _extract_first_string(
    contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]
) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value

    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_phrase(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", normalized) or None


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
