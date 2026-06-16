"""Build title-update actions for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any

TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {
    "status",
    "status_name",
    "statusname",
    "state",
    "state_name",
    "statename",
    "workflow_state",
    "workflowstate",
    "workflow_state_name",
    "workflowstatename",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action when the event enters research."""
    if not isinstance(event, Mapping):
        return None

    candidates = _candidate_payloads(event)
    if not _is_status_change_event(candidates):
        return None

    new_status = _new_status(candidates)
    if _normalize_label(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(candidates, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(candidates, ("title", "issueTitle", "issue_title"))
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _candidate_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = [event]
    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            candidates.extend(_candidate_payloads(value))
    return candidates


def _is_status_change_event(candidates: list[Mapping[str, Any]]) -> bool:
    for payload in candidates:
        for key in ("trigger", "webhookType", "action", "type"):
            event_type = _normalize_label(payload.get(key))
            if event_type in {"status changed", "status change", "statuschanged"}:
                return True

    if not _is_issue_update(candidates):
        return False

    for payload in candidates:
        if _updated_status_fields(payload):
            return True
    return False


def _is_issue_update(candidates: list[Mapping[str, Any]]) -> bool:
    for payload in candidates:
        for key in ("trigger", "webhookType", "action", "type"):
            event_type = _normalize_label(payload.get(key))
            if event_type in {"update", "updated", "issue updated", "updated issue"}:
                return True
    return False


def _updated_status_fields(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields"):
        fields = payload.get(key)
        if isinstance(fields, str):
            fields = [fields]
        if isinstance(fields, list) and any(_is_status_field(field) for field in fields):
            return True

    for key in ("updatedFrom", "updated_from", "changes"):
        changes = payload.get(key)
        if isinstance(changes, Mapping) and any(_is_status_field(field) for field in changes):
            return True

    return False


def _new_status(candidates: list[Mapping[str, Any]]) -> str | None:
    for payload in candidates:
        status = _first_text(
            [payload],
            (
                "newStatus",
                "new_status",
                "statusName",
                "status_name",
                "stateName",
                "state_name",
                "workflowStateName",
                "workflow_state_name",
            ),
        )
        if status:
            return status

    for payload in candidates:
        status = _first_text([payload], ("status", "state", "workflowState", "workflow_state"))
        if status:
            return status

    return None


def _first_text(candidates: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for payload in candidates:
        for key in keys:
            value = _text_value(payload.get(key))
            if value:
                return value
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "key", "id"):
            text = _text_value(value.get(key))
            if text:
                return text
    return None


def _normalize_label(value: Any) -> str:
    text = _text_value(value)
    if not text:
        return ""
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _is_status_field(field: Any) -> bool:
    normalized = _normalize_label(field).replace(" ", "_")
    return normalized in STATUS_FIELDS or normalized.endswith("_state_id")


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    """Read an event JSON document from stdin and print the update action if any."""
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
