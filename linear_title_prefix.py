"""Build title updates for Linear issues entering the research workflow."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state", "workflow_status", "workflow status"}
_TRIGGER_FIELDS = ("trigger", "webhookType", "action", "type")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue-title update action for research status changes.

    The automation trigger can arrive as a flat Cursor trigger context or as a
    nested Linear webhook payload. This function keeps side effects outside the
    handler and returns the intended update action for the caller to execute.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _merge_payload(event)
    if not _is_status_change(event, payload):
        return None

    status = _new_status(payload)
    if _normalize(status) != _normalize(TARGET_STATUS):
        return None

    issue_id = _first_string(payload, ("issueId", "issue_id", "id", "identifier"))
    title = _first_string(payload, ("title", "name"))
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


def _merge_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    for key in ("issue", "data", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            payload.update(_merge_payload(value))

    payload.update(event)

    issue = payload.get("issue")
    if isinstance(issue, Mapping):
        payload.update({key: value for key, value in issue.items() if key not in payload})

    return payload


def _is_status_change(event: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
    trigger_values = list(_trigger_values(event)) + list(_trigger_values(payload))
    if any(_is_status_change_value(value) for value in trigger_values):
        return True

    if any(_is_issue_update_value(value) for value in trigger_values):
        return _updated_fields_include_status(payload)

    return False


def _trigger_values(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for field in _TRIGGER_FIELDS:
            field_value = value.get(field)
            if isinstance(field_value, str):
                yield field_value
        for nested_key in ("triggerContext", "data"):
            yield from _trigger_values(value.get(nested_key))


def _is_status_change_value(value: str) -> bool:
    normalized = _normalize(value)
    return normalized in {"status changed", "status change", "state changed", "workflow state changed"}


def _is_issue_update_value(value: str) -> bool:
    normalized = _normalize(value)
    return normalized in {"update", "updated", "issue update", "issue updated", "updated issue"}


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    fields = payload.get("updatedFields") or payload.get("updated_fields") or payload.get("changedFields")
    if isinstance(fields, str):
        fields = [fields]
    if not isinstance(fields, Iterable):
        return False

    return any(_normalize_field_name(field) in _STATUS_FIELDS for field in fields if isinstance(field, str))


def _new_status(payload: Mapping[str, Any]) -> str | None:
    for field in ("newStatus", "new_status", "statusName", "status_name"):
        value = payload.get(field)
        if isinstance(value, str):
            return value

    for field in ("state", "workflowState", "status"):
        value = payload.get(field)
        if isinstance(value, Mapping):
            name = value.get("name")
            if isinstance(name, str):
                return name
        elif isinstance(value, str):
            return value

    return None


def _first_string(payload: Mapping[str, Any], fields: Iterable[str]) -> str | None:
    for field in fields:
        value = payload.get(field)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[\W_]+", " ", spaced).strip().casefold()


def _normalize_field_name(value: str) -> str:
    return _normalize(value) or ""


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is None:
        return 0

    json.dump(update, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
