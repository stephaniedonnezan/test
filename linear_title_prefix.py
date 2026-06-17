"""Build title update actions for Linear issues entering research status."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"
TITLE_SEPARATOR = ": "
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}
STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "statuschanged",
    "state changed",
    "statechanged",
    "workflow state changed",
    "workflowstatechanged",
}
GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action for matching status changes.

    The automation receives both flat Cursor trigger payloads and nested Linear
    webhook payloads, so this function normalizes the common shapes before
    deciding whether a title update is required.
    """

    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    if _normalize_status(_first_string(context, ("newStatus", "new_status", "statusName"))) != RESEARCH_STATUS:
        status_value = _status_from_payload(context)
        if _normalize_status(status_value) != RESEARCH_STATUS:
            return None

    issue_id = _first_string(context, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_string(context, ("title", "name"))
    if issue_id is None or title is None:
        return None

    clean_title = title.strip()
    if not clean_title or _has_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}{TITLE_SEPARATOR}{clean_title}",
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten known trigger/issue containers while preserving outer metadata."""

    context: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if isinstance(value, Mapping):
            context.update(value)

    merge(event.get("data"))
    data = event.get("data")
    if isinstance(data, Mapping):
        merge(data.get("issue"))

    merge(event.get("issue"))
    merge(event.get("triggerContext"))
    merge(event)
    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize_phrase(value)
        for key in ("trigger", "webhookType", "action", "type")
        if (value := context.get(key)) is not None
    ]

    if any(value in STATUS_CHANGE_TRIGGERS for value in trigger_values):
        return True

    if any(value in GENERIC_UPDATE_TRIGGERS for value in trigger_values):
        return _updated_fields_include_status(context)

    return _updated_fields_include_status(context)


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = context.get(key)
        if isinstance(fields, str):
            names = re.split(r"[, ]+", fields)
        elif isinstance(fields, list | tuple | set):
            names = fields
        else:
            continue

        if any(_normalize_field_name(name) in STATUS_FIELDS for name in names):
            return True

    changes = context.get("changes") or context.get("updatedProperties")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(name) in STATUS_FIELDS for name in changes)

    return False


def _status_from_payload(context: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "status", "state", "workflowState"):
        value = context.get(key)
        if isinstance(value, Mapping):
            nested = _first_string(value, ("name", "title", "label"))
            if nested is not None:
                return nested
        elif isinstance(value, str):
            return value
    return None


def _first_string(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    return _normalize_phrase(value)


def _normalize_phrase(value: Any) -> str:
    text = str(value)
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().casefold()


def _normalize_field_name(value: Any) -> str:
    return _normalize_phrase(value).replace(" ", "")


def main() -> int:
    """Read a JSON event from stdin and print the update action if any."""

    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
