"""Build Linear issue title updates for research status changes.

The automation runner can pass the Linear trigger payload to
``build_issue_title_update``. When the issue has just moved to "to research",
the function returns a small action payload describing the title update to make.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflow status"}
_STATUS_CHANGE_EVENT_NAMES = {"status changed", "status change"}
_ISSUE_UPDATE_EVENT_NAMES = {"issue updated", "updated issue", "update", "updated"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action for matching Linear webhook payloads.

    The function intentionally accepts both the flat automation trigger context
    shape and common nested Linear webhook shapes so the rule stays stable if the
    surrounding runner changes how it forwards payloads.
    """

    if not isinstance(event, Mapping):
        return None

    context = _collect_context(event)
    if not _is_status_change_event(context):
        return None

    status = _new_status(context)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(context, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(context, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _collect_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge useful nested payload sections, with outer fields taking priority."""

    context: dict[str, Any] = {}
    for key in ("triggerContext", "data", "issue"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            context.update(_collect_context(nested))
            context.update(nested)

    context.update(event)
    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    event_names = {
        _normalize_text(value)
        for key in ("trigger", "webhookType", "action", "type")
        if (value := context.get(key)) is not None
    }

    if event_names & _STATUS_CHANGE_EVENT_NAMES:
        return True

    if event_names & _ISSUE_UPDATE_EVENT_NAMES:
        return _updated_fields_include_status(context.get("updatedFields"))

    return False


def _updated_fields_include_status(updated_fields: Any) -> bool:
    if updated_fields is None:
        return False

    if isinstance(updated_fields, str):
        candidates = re.split(r"[,;]", updated_fields)
    elif isinstance(updated_fields, Mapping):
        candidates = updated_fields.keys()
    elif isinstance(updated_fields, list | tuple | set):
        candidates = updated_fields
    else:
        return False

    return any(_normalize_text(field) in _STATUS_FIELD_NAMES for field in candidates)


def _new_status(context: Mapping[str, Any]) -> str | None:
    explicit = _first_text(
        context,
        (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "newWorkflowState",
            "new_workflow_state",
            "status",
        ),
    )
    if explicit:
        return explicit

    for key in ("state", "workflowState", "workflowStatus"):
        value = context.get(key)
        if isinstance(value, Mapping):
            nested = _first_text(value, ("name", "title", "status"))
            if nested:
                return nested
        elif isinstance(value, str) and value.strip():
            return value

    return None


def _first_text(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    separated = re.sub(r"[_\-/]+", " ", spaced)
    return re.sub(r"\s+", " ", separated).casefold()


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        json.dump(action, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
