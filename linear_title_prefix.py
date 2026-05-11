"""Build Linear issue-title updates for Cursor research automation."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research.

    The Cursor automation payload has varied across triggers, so this accepts
    both flat payloads and nested Linear webhook-style shapes.
    """

    if not isinstance(event, Mapping):
        return None

    trigger_context = _trigger_context(event)
    issue = _issue_payload(event)
    if not _is_status_change_event(event):
        return None

    status = _first_text(
        trigger_context.get("newStatus"),
        trigger_context.get("new_status"),
        trigger_context.get("status"),
        _nested_name(trigger_context.get("state")),
        _nested_name(trigger_context.get("workflowState")),
        event.get("newStatus"),
        event.get("new_status"),
        event.get("status"),
        _nested_name(event.get("state")),
        _nested_name(event.get("workflowState")),
        issue.get("newStatus"),
        issue.get("new_status"),
        issue.get("status"),
        _nested_name(issue.get("state")),
        _nested_name(issue.get("workflowState")),
    )
    if _normalize_status(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(
        issue.get("id"),
        issue.get("issueId"),
        issue.get("issue_id"),
        issue.get("identifier"),
        event.get("id"),
        event.get("issueId"),
        event.get("issue_id"),
        event.get("identifier"),
    )
    title = _first_text(issue.get("title"), event.get("title"))

    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {stripped_title}",
    }


def _issue_payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    trigger_context = _trigger_context(event)
    data = event.get("data")
    issue = event.get("issue")

    data = trigger_context.get("data", data)
    issue = trigger_context.get("issue", issue)

    if isinstance(data, Mapping):
        issue = data.get("issue", issue)

    if isinstance(issue, Mapping):
        merged = dict(issue)
        for key in (
            "id",
            "issueId",
            "issue_id",
            "identifier",
            "title",
            "newStatus",
            "new_status",
            "status",
            "state",
            "workflowState",
        ):
            if key in trigger_context:
                merged[key] = trigger_context[key]
        for key in (
            "id",
            "issueId",
            "issue_id",
            "identifier",
            "title",
            "newStatus",
            "new_status",
            "status",
            "state",
            "workflowState",
        ):
            if key in event:
                merged[key] = event[key]
        return merged

    return event


def _trigger_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context
    return {}


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    candidates = [
        event.get("trigger"),
        event.get("webhookType"),
        event.get("action"),
        event.get("type"),
    ]
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        candidates.extend(
            [
                trigger_context.get("trigger"),
                trigger_context.get("webhookType"),
                trigger_context.get("action"),
                trigger_context.get("type"),
            ]
        )

    normalized_candidates = {_normalize_event_name(value) for value in candidates if value}
    if "statuschanged" in normalized_candidates:
        return True

    issue_updated_names = {"issueupdated", "updatedissue"}
    if normalized_candidates.intersection(issue_updated_names):
        return _updated_fields_include_status(event)

    return False


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    fields = event.get("updatedFields")
    trigger_context = event.get("triggerContext")
    if not fields and isinstance(trigger_context, Mapping):
        fields = trigger_context.get("updatedFields")

    if isinstance(fields, str):
        return _normalize_event_name(fields) in {"status", "state", "workflowstate"}

    if isinstance(fields, Sequence) and not isinstance(fields, (str, bytes, bytearray)):
        return any(
            _normalize_event_name(field) in {"status", "state", "workflowstate"}
            for field in fields
        )

    return False


def _first_text(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value
    return None


def _nested_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _first_text(value.get("name"), value.get("title"))
    if isinstance(value, str):
        return value
    return None


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    return re.sub(r"[\W_]+", " ", spaced).casefold().strip()


def _normalize_event_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[\W_]+", "", value).casefold()


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())
