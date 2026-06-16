"""Build Linear issue title updates for research-status transitions.

The automation runner can invoke this module with a Linear webhook payload.
When an issue moves to "to research", the handler returns the issue-title
update needed to add the Cursor research marker.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflowstatus"}
STATUS_TRIGGER_VALUES = {"statuschanged", "statuschange", "statusupdated"}
ISSUE_UPDATE_VALUES = {"update", "updated", "issueupdated", "updatedissue"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action for research status changes.

    The function is intentionally side-effect free. It validates the incoming
    event, extracts the issue id/title and target status, then returns the
    update action expected by the automation layer.
    """

    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    status = _new_status(context)
    if _normalize_text(status) != _normalize_text(RESEARCH_STATUS):
        return None

    issue_id = _issue_id(context)
    title = _issue_title(context)
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{RESEARCH_PREFIX}: {title.strip()}",
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Linear/automation nesting layers into a flat context."""

    context: dict[str, Any] = {}

    for key in ("triggerContext", "data", "issue"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            context.update(nested)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            context.update(issue)

    # Top-level automation metadata should win over nested issue fields for
    # trigger and new-status data.
    context.update(event)
    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        context.get("trigger"),
        context.get("webhookType"),
        context.get("action"),
        context.get("type"),
    ]
    normalized = {_normalize_text(value) for value in trigger_values if value}

    if normalized & STATUS_TRIGGER_VALUES:
        return True

    if normalized & ISSUE_UPDATE_VALUES:
        return _updated_status_field(context)

    return False


def _updated_status_field(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields")
    if isinstance(updated_fields, str):
        updated_fields = [updated_fields]

    if isinstance(updated_fields, list):
        for field in updated_fields:
            if _normalize_text(field) in STATUS_FIELD_NAMES:
                return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_text(field) in STATUS_FIELD_NAMES for field in changes)

    return False


def _new_status(context: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
    ):
        value = context.get(key)
        status = _status_name(value)
        if status:
            return status

    changed_status = _changed_status(context)
    if changed_status:
        return changed_status

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = context.get(key)
        status = _status_name(value)
        if status:
            return status

    return None


def _changed_status(context: Mapping[str, Any]) -> str | None:
    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key, change in changes.items():
            if _normalize_text(key) not in STATUS_FIELD_NAMES:
                continue
            if isinstance(change, Mapping):
                status = _status_name(
                    change.get("to")
                    or change.get("new")
                    or change.get("newValue")
                    or change.get("after")
                )
                if status:
                    return status

    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "status"):
            nested = value.get(key)
            if isinstance(nested, str):
                return nested
    return None


def _issue_id(context: Mapping[str, Any]) -> str | None:
    data = context.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        nested_issue_id = _issue_id_from_mapping(issue)
        if nested_issue_id:
            return nested_issue_id

    nested_issue_id = _issue_id_from_mapping(context.get("issue"))
    if nested_issue_id:
        return nested_issue_id

    return _issue_id_from_mapping(context)


def _issue_id_from_mapping(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for key in ("issueId", "issue_id", "identifier", "key", "id"):
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


def _issue_title(context: Mapping[str, Any]) -> str | None:
    value = context.get("title")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _has_research_prefix(title: str) -> bool:
    return title.strip().lower().startswith(RESEARCH_PREFIX.lower())


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    with_spaces = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    return re.sub(r"[^a-z0-9]+", "", with_spaces.lower())


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    if action is not None:
        print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
