"""Helpers for prefixing Linear issue titles during research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
STATUS_UPDATE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statusupdated",
    "statechanged",
    "workflowstatechanged",
}
ISSUE_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Build a title update action for Linear issues moved to "to research".

    The automation trigger provides a compact payload, while Linear webhooks can
    nest issue data under ``data`` or ``issue``. This function accepts both
    shapes and returns a serializable action for the caller to apply.
    """

    if not isinstance(event, Mapping):
        return None

    context = _payload_context(event)
    if not _is_status_change_event(context):
        return None

    status = _new_status(context)
    if _normalize_label(status) != _normalize_label(RESEARCH_STATUS):
        return None

    issue_id = _first_text(context, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(context, ("title", "name"))
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _payload_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common automation and Linear webhook containers.

    Later sources intentionally override earlier sources so outer trigger
    metadata (for example, ``triggerContext.newStatus``) wins over stale nested
    issue status values.
    """

    context: dict[str, Any] = {}

    for key in ("data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            context.update(value)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            context.update(issue)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        context.update(trigger_context)

    context.update(event)
    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = []
    for key in ("trigger", "webhookType", "action", "type"):
        value = context.get(key)
        if isinstance(value, str):
            trigger_values.append(_normalize_label(value))

    if any(value in STATUS_UPDATE_TRIGGERS for value in trigger_values):
        return True

    if any(value in ISSUE_UPDATE_TRIGGERS for value in trigger_values):
        return _updated_fields_include_status(context)

    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields")
    if updated_fields is None:
        updated_fields = context.get("updated_fields")

    if isinstance(updated_fields, str):
        fields = re.split(r"[\s,;]+", updated_fields)
    elif isinstance(updated_fields, Mapping):
        fields = updated_fields.keys()
    elif isinstance(updated_fields, (list, tuple, set)):
        fields = updated_fields
    else:
        return False

    return any(_normalize_label(str(field)) in STATUS_FIELDS for field in fields)


def _new_status(context: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status"):
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = context.get(key)
        text = _text_or_name(value)
        if text:
            return text

    return None


def _first_text(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _text_or_name(context.get(key))
        if value:
            return value
    return None


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        name = value.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()

    return None


def _has_research_prefix(title: str) -> bool:
    return title.strip().lower().startswith(PREFIX.lower())


def _normalize_label(value: str | None) -> str | None:
    if value is None:
        return None

    with_spaces = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", "", with_spaces.lower())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
