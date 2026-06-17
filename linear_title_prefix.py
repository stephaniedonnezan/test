"""Build Linear issue title updates for research status changes.

The automation runtime can pass either a flat Cursor trigger context or a
nested Linear webhook payload.  This module keeps the decision logic isolated:
return an update action when an issue moved to "to research", otherwise return
``None``.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflowstatus"}
STATUS_TRIGGER_NAMES = {
    "statuschanged",
    "statuschange",
    "statusupdated",
    "statechanged",
    "statechange",
    "stateupdated",
    "workflowstatechanged",
    "workflowstatechange",
    "workflowstateupdated",
}
GENERIC_UPDATE_NAMES = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action for issues moved to "to research".

    The returned dict is intentionally simple so callers can translate it into
    their Linear API client call:

    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``
    """

    if not isinstance(event, Mapping):
        return None

    payloads = _candidate_payloads(event)
    if not _is_status_change_event(payloads):
        return None

    new_status = _extract_new_status(payloads)
    if _normalize_status(new_status) != RESEARCH_STATUS:
        return None

    issue_id = _extract_issue_id(payloads)
    title = _extract_title(payloads)
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _candidate_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return relevant payload mappings from outermost to innermost."""

    payloads: list[Mapping[str, Any]] = [event]
    for key in ("triggerContext", "webhook", "payload", "data", "issue"):
        for payload in list(payloads):
            value = payload.get(key)
            if isinstance(value, Mapping) and value not in payloads:
                payloads.append(value)

    # Common Linear webhooks keep issue fields at data.issue.
    for payload in list(payloads):
        data = payload.get("data")
        if isinstance(data, Mapping):
            issue = data.get("issue")
            if isinstance(issue, Mapping) and issue not in payloads:
                payloads.append(issue)

    return payloads


def _is_status_change_event(payloads: list[Mapping[str, Any]]) -> bool:
    event_names = [
        value
        for payload in payloads
        for key in ("trigger", "action", "type", "webhookType", "eventType")
        for value in [payload.get(key)]
        if value is not None
    ]

    normalized_names = {_normalize_token(name) for name in event_names}
    if normalized_names & STATUS_TRIGGER_NAMES:
        return True

    updated_fields = _updated_field_names(payloads)
    if updated_fields & STATUS_FIELD_NAMES:
        return True

    if normalized_names & GENERIC_UPDATE_NAMES:
        return bool(updated_fields & STATUS_FIELD_NAMES)

    # Cursor's automation trigger can provide a newStatus value directly.
    return _extract_new_status(payloads) is not None and not normalized_names


def _updated_field_names(payloads: list[Mapping[str, Any]]) -> set[str]:
    fields: set[str] = set()
    for payload in payloads:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields.update(_normalize_field_name(value) for value in _as_list(payload.get(key)))

        changes = payload.get("changes")
        if isinstance(changes, Mapping):
            fields.update(_normalize_field_name(key) for key in changes.keys())
        elif isinstance(changes, list):
            for change in changes:
                if isinstance(change, Mapping):
                    for key in ("field", "fieldName", "name", "property"):
                        if change.get(key) is not None:
                            fields.add(_normalize_field_name(change[key]))
                            break
                elif change is not None:
                    fields.add(_normalize_field_name(change))

    return {field for field in fields if field}


def _extract_new_status(payloads: list[Mapping[str, Any]]) -> str | None:
    direct_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "status",
        "state",
        "workflowState",
        "workflowStatus",
    )

    for payload in payloads:
        for key in direct_keys:
            status = _coerce_name(payload.get(key))
            if status:
                return status

        changes = payload.get("changes")
        if isinstance(changes, Mapping):
            for key in ("status", "state", "workflowState", "workflowStatus"):
                status = _status_from_change(changes.get(key))
                if status:
                    return status
        elif isinstance(changes, list):
            for change in changes:
                if not isinstance(change, Mapping):
                    continue
                field = _normalize_field_name(
                    change.get("field")
                    or change.get("fieldName")
                    or change.get("name")
                    or change.get("property")
                )
                if field in STATUS_FIELD_NAMES:
                    status = _status_from_change(change)
                    if status:
                        return status

    return None


def _extract_issue_id(payloads: list[Mapping[str, Any]]) -> str | None:
    for payload in payloads:
        for key in ("issueId", "issue_id", "identifier", "key", "id"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _extract_title(payloads: list[Mapping[str, Any]]) -> str | None:
    for payload in payloads:
        value = payload.get("title")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _status_from_change(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("newValue", "new_value", "to", "after", "current", "value", "name"):
            status = _coerce_name(change.get(key))
            if status:
                return status
    return _coerce_name(change)


def _coerce_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()
    return None


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", normalized).strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized or None


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    split_camel = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-zA-Z0-9]+", "", split_camel).lower()


def _normalize_field_name(value: Any) -> str:
    return _normalize_token(value)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    """Read a JSON event from stdin and print the title update action."""

    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is None:
        return 0
    print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
