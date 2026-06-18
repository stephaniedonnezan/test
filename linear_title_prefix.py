"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
    "workflowstatus",
    "workflowstatusid",
}
_STATUS_CHANGED_EVENTS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return the title update action for Linear issues moved to To Research.

    The automation payloads seen by Cursor can be flat ``triggerContext``
    objects, direct flat dictionaries, or nested Linear webhook payloads. This
    helper accepts those shapes and returns ``None`` when no title update should
    be attempted.
    """

    if not isinstance(event, Mapping):
        return None

    candidates = _payload_candidates(event)
    if not _is_status_change_event(candidates):
        return None

    new_status = _extract_new_status(candidates)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(candidates, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _extract_first_text(candidates, ("title",))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if clean_title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _payload_candidates(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        candidates.append(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            candidates.append(issue)
        candidates.append(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        candidates.append(issue)

    candidates.append(event)
    return candidates


def _is_status_change_event(candidates: list[Mapping[str, Any]]) -> bool:
    indicators = []
    for candidate in candidates:
        indicators.extend(
            _normalize_text(candidate.get(key))
            for key in ("trigger", "webhookType", "action", "type", "event", "eventType")
        )

    if any(indicator in _STATUS_CHANGED_EVENTS for indicator in indicators):
        return True

    has_status_field_update = any(_contains_status_field_update(candidate) for candidate in candidates)
    if has_status_field_update:
        return True

    return any(indicator in _GENERIC_UPDATE_EVENTS for indicator in indicators) and has_status_field_update


def _contains_status_field_update(candidate: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "changedFields"):
        fields = candidate.get(key)
        if isinstance(fields, list) and any(_is_status_field(field) for field in fields):
            return True
        if isinstance(fields, Mapping) and any(_is_status_field(field) for field in fields):
            return True

    for key in ("changes", "updatedFrom"):
        fields = candidate.get(key)
        if isinstance(fields, Mapping) and any(_is_status_field(field) for field in fields):
            return True

    return False


def _extract_new_status(candidates: list[Mapping[str, Any]]) -> str | None:
    for candidate in candidates:
        status = _extract_first_text(
            [candidate],
            (
                "newStatus",
                "new_status",
                "newState",
                "new_state",
                "toStatus",
                "to_status",
                "toState",
                "to_state",
            ),
        )
        if status:
            return status

    for candidate in candidates:
        status = _extract_status_from_changes(candidate.get("changes"))
        if status:
            return status

    for candidate in candidates:
        status = _extract_first_text(candidate_values=[candidate], field_names=("status", "state", "workflowState", "workflow_state"))
        if status:
            return status

    return None


def _extract_status_from_changes(changes: Any) -> str | None:
    if not isinstance(changes, Mapping):
        return None

    for field_name, change in changes.items():
        if not _is_status_field(field_name):
            continue

        if isinstance(change, Mapping):
            for key in ("to", "after", "new", "newValue", "toValue"):
                status = _text_from_value(change.get(key))
                if status:
                    return status
        else:
            status = _text_from_value(change)
            if status:
                return status

    return None


def _extract_first_text(candidate_values: list[Mapping[str, Any]], field_names: tuple[str, ...]) -> str | None:
    for candidate in candidate_values:
        for field_name in field_names:
            value = _text_from_value(candidate.get(field_name))
            if value:
                return value
    return None


def _text_from_value(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value", "id", "identifier", "key"):
            text = _text_from_value(value.get(key))
            if text:
                return text
        return None

    text = str(value).strip()
    return text or None


def _is_status_field(field_name: Any) -> bool:
    normalized = _normalize_text(field_name).replace(" ", "")
    return normalized in _STATUS_FIELD_NAMES


def _normalize_text(value: Any) -> str:
    text = _text_from_value(value)
    if not text:
        return ""

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _main() -> int:
    update = build_issue_title_update(json.load(sys.stdin))
    print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
