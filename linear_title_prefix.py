"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}
DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "state changed",
    "workflow state changed",
    "workflow status changed",
}
GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return the issue-title update action for a matching Linear event.

    The automation should only update titles when a Linear issue status changes
    to "to research". The function is intentionally side-effect free so callers
    can decide how to apply the returned action.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize(_extract_new_status(event)) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if not issue_id or not title:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": _prefixed_title(title),
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    normalized_event_names = {
        _normalize(value)
        for payload in _payloads(event)
        for key in ("trigger", "webhookType", "action", "type", "event", "eventType")
        if (value := payload.get(key)) is not None
    }

    if normalized_event_names & DIRECT_STATUS_TRIGGERS:
        return True

    if normalized_event_names & GENERIC_UPDATE_TRIGGERS:
        return _changed_fields_include_status(event)

    return False


def _changed_fields_include_status(event: Mapping[str, Any]) -> bool:
    for payload in _payloads(event):
        for key in ("updatedFields", "changedFields"):
            if _field_collection_mentions_status(payload.get(key)):
                return True

        changes = payload.get("changes")
        if isinstance(changes, Mapping):
            if any(_is_status_field_name(key) for key in changes):
                return True
        elif _field_collection_mentions_status(changes):
            return True

    return False


def _field_collection_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) for key in value)

    if isinstance(value, Iterable):
        return any(_field_collection_mentions_status(item) for item in value)

    return False


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize(value)
    return normalized in STATUS_FIELD_NAMES


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for payload in _payloads(event):
        for key in (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "toStatus",
            "to_status",
            "statusName",
            "stateName",
        ):
            if (status := _string_or_name(payload.get(key))) is not None:
                return status

        changes = payload.get("changes")
        if isinstance(changes, Mapping):
            for key, change in changes.items():
                if _is_status_field_name(key):
                    if (status := _extract_changed_value(change)) is not None:
                        return status

    for payload in _payloads(event):
        for key in ("status", "state", "workflowState"):
            if (status := _string_or_name(payload.get(key))) is not None:
                return status

    return None


def _extract_changed_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("new", "to", "newValue", "toValue", "after", "current"):
            if (status := _string_or_name(value.get(key))) is not None:
                return status
    return _string_or_name(value)


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for key in ("issueId", "issue_id", "identifier", "key"):
        for payload in _payloads(event):
            if (issue_id := _clean_string(payload.get(key))) is not None:
                return issue_id

    for payload in _payloads(event):
        if (issue_id := _clean_string(payload.get("id"))) is not None:
            return issue_id

    return None


def _extract_title(event: Mapping[str, Any]) -> str | None:
    for payload in _payloads(event):
        if (title := _clean_string(payload.get("title"))) is not None:
            return title
    return None


def _payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    payloads: list[Mapping[str, Any]] = [event]

    for key in ("triggerContext", "data", "issue"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            payloads.append(nested)

    data = event.get("data")
    if isinstance(data, Mapping):
        for key in ("issue", "state", "workflowState"):
            nested = data.get(key)
            if isinstance(nested, Mapping):
                payloads.append(nested)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        nested_issue = trigger_context.get("issue")
        if isinstance(nested_issue, Mapping):
            payloads.append(nested_issue)

    return payloads


def _string_or_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if (text := _clean_string(value.get(key))) is not None:
                return text
        return None
    return _clean_string(value)


def _clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    value = value.strip()
    return value or None


def _prefixed_title(title: str) -> str:
    title = title.strip()
    if title.lower().startswith(PREFIX.lower()):
        return title
    return f"{PREFIX}: {title}"


def _normalize(value: Any) -> str:
    text = _string_or_name(value)
    if text is None:
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    if result is not None:
        json.dump(result, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
