"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "state changed",
    "workflow state changed",
}
_ISSUE_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to "to research".

    The automation trigger can arrive either as the flat Cursor automation
    `triggerContext` payload or as a nested Linear-style webhook payload.
    """

    if not isinstance(event, Mapping):
        return None

    sources = _payload_sources(event)
    if not _is_status_change_event(sources):
        return None

    if _normalize_status(_extract_status(sources)) != TARGET_STATUS:
        return None

    issue_id = _first_text(sources, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(sources, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _payload_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return useful payload objects in issue-first order for field lookup."""

    trigger_context = _mapping_value(event.get("triggerContext"))
    data = _mapping_value(event.get("data"))
    issue = _mapping_value(event.get("issue"))
    if issue is None and data:
        issue = _mapping_value(data.get("issue"))
    trigger_issue = _mapping_value(trigger_context.get("issue")) if trigger_context else None

    sources: list[Mapping[str, Any]] = []
    for source in (issue, trigger_issue, data, trigger_context, event):
        if source and source not in sources:
            sources.append(source)
    return sources


def _is_status_change_event(sources: Sequence[Mapping[str, Any]]) -> bool:
    for source in sources:
        for key in ("trigger", "event", "eventType", "webhookType"):
            value = _normalize_status(source.get(key))
            if value in _STATUS_CHANGE_TRIGGERS:
                return True

    if not _updated_fields_include_status(sources):
        return False

    for source in sources:
        for key in ("action", "type", "trigger"):
            value = _normalize_status(source.get(key))
            if value in _ISSUE_UPDATE_EVENTS:
                return True

    return False


def _updated_fields_include_status(sources: Sequence[Mapping[str, Any]]) -> bool:
    for source in sources:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = source.get(key)
            if isinstance(fields, Mapping):
                values = fields.keys()
            elif isinstance(fields, Sequence) and not isinstance(fields, (str, bytes, bytearray)):
                values = fields
            else:
                continue

            for field in values:
                name = field.get("name") if isinstance(field, Mapping) else field
                if _normalize_status(name) in _STATUS_FIELD_NAMES:
                    return True
    return False


def _extract_status(sources: Sequence[Mapping[str, Any]]) -> str | None:
    explicit_status_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "statusName",
        "stateName",
        "workflowStateName",
    )
    status_keys = ("status", "state", "workflowState", "workflow_state")

    explicit = _first_text(sources, explicit_status_keys)
    if explicit:
        return explicit

    for source in sources:
        for key in status_keys:
            value = source.get(key)
            if isinstance(value, Mapping):
                name = _text_value(value.get("name"))
                if name:
                    return name
            else:
                text = _text_value(value)
                if text:
                    return text
    return None


def _first_text(sources: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for source in sources:
        for key in keys:
            text = _text_value(source.get(key))
            if text:
                return text
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _mapping_value(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _normalize_status(value: Any) -> str:
    text = _text_value(value)
    if not text:
        return ""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def _has_research_prefix(title: str) -> bool:
    return title.lstrip().casefold().startswith(PREFIX.casefold())


def main() -> int:
    payload = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(payload), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
