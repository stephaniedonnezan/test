"""Build title-update actions for Linear issues moved to research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue enters research."""
    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change(context):
        return None

    status = _new_status(context)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _clean_text(_first_value(context, ("id", "issueId", "issue_id", "identifier")))
    title = _clean_text(_first_value(context, ("title",)))
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Cursor automation and Linear webhook containers."""
    context: dict[str, Any] = {}

    for path in (
        ("data", "issue"),
        ("issue",),
        ("triggerContext",),
        ("data",),
    ):
        nested = _nested_mapping(event, path)
        if nested:
            context.update(nested)

    context.update(event)
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        context.update(trigger_context)

    return context


def _nested_mapping(event: Mapping[str, Any], path: Sequence[str]) -> Mapping[str, Any] | None:
    current: Any = event
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)

    return current if isinstance(current, Mapping) else None


def _is_status_change(context: Mapping[str, Any]) -> bool:
    trigger_values = (
        context.get("trigger"),
        context.get("webhookType"),
        context.get("action"),
        context.get("type"),
    )
    normalized_triggers = {_normalize(value) for value in trigger_values if value}

    if normalized_triggers & {"status changed", "statuschanged", "status change"}:
        return True

    if normalized_triggers & {"issue updated", "updated issue", "update", "updated"}:
        return _updated_fields_include_status(context)

    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    updated_fields = (
        context.get("updatedFields")
        or context.get("updated_fields")
        or context.get("changedFields")
        or context.get("changed_fields")
    )

    if isinstance(updated_fields, Mapping):
        candidates = updated_fields.keys()
    elif isinstance(updated_fields, Sequence) and not isinstance(updated_fields, (str, bytes)):
        candidates = updated_fields
    else:
        return False

    return any(_normalize_field_name(field) in STATUS_FIELDS for field in candidates)


def _new_status(context: Mapping[str, Any]) -> str | None:
    direct_status = _first_value(
        context,
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
    if direct_status:
        return _clean_text(direct_status)

    for key in ("state", "workflowState", "workflow_state", "status"):
        value = context.get(key)
        if isinstance(value, Mapping):
            name = _clean_text(value.get("name"))
            if name:
                return name
        else:
            name = _clean_text(value)
            if name:
                return name

    return None


def _first_value(context: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        value = context.get(key)
        if value is not None:
            return value
    return None


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _normalize_field_name(value: Any) -> str:
    return _normalize(value).replace(" ", "")


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
