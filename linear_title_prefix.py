"""Build Linear issue title updates for research status changes.

The automation that calls this module is expected to perform the actual
Linear API mutation. This module keeps the webhook parsing and idempotent title
construction in one testable place.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}
_DIRECT_STATUS_TRIGGERS = {"status changed", "status change"}
_GENERIC_UPDATE_TRIGGERS = {"issue updated", "updated issue", "update", "updated"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action when an issue moves to research.

    The return value is intentionally side-effect free so it can be used by
    automation runners, CLIs, and tests:

    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``

    Non-status changes, statuses other than "to research", missing issue data,
    and already-prefixed titles return ``None``.
    """

    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    issue = _issue_payload(context) or _issue_payload(event) or {}

    if not _is_status_change(context, event):
        return None

    if _normalize_text(_new_status(context, issue)) != RESEARCH_STATUS:
        return None

    issue_id = _string_value(
        _first_present(
            context,
            issue,
            ("issueId", "issue_id", "identifier", "key", "id"),
        )
    )
    title = _string_value(_first_present(context, issue, ("title", "name")))

    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _event_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    automation_info = event.get("automation_trigger_info")
    if isinstance(automation_info, Mapping):
        trigger_context = automation_info.get("triggerContext")
        if isinstance(trigger_context, Mapping):
            return trigger_context

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context

    return event


def _issue_payload(context: Mapping[str, Any]) -> Mapping[str, Any] | None:
    for path in (
        ("issue",),
        ("data", "issue"),
        ("payload", "issue"),
        ("payload", "data", "issue"),
        ("data",),
        ("payload",),
    ):
        value: Any = context
        for key in path:
            if not isinstance(value, Mapping):
                value = None
                break
            value = value.get(key)
        if isinstance(value, Mapping) and _looks_like_issue(value):
            return value
    return None


def _looks_like_issue(value: Mapping[str, Any]) -> bool:
    return any(key in value for key in ("title", "name")) and any(
        key in value for key in ("issueId", "issue_id", "identifier", "key", "id")
    )


def _is_status_change(context: Mapping[str, Any], event: Mapping[str, Any]) -> bool:
    trigger_names = set()
    for source in (event, context):
        for key in ("trigger", "webhookType", "action", "type"):
            normalized = _normalize_text(source.get(key))
            if normalized:
                trigger_names.add(normalized)

    if trigger_names & _DIRECT_STATUS_TRIGGERS:
        return True

    if trigger_names & _GENERIC_UPDATE_TRIGGERS:
        return _status_field_changed(context) or _status_field_changed(event)

    return False


def _status_field_changed(source: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        value = source.get(key)
        if _contains_status_field(value):
            return True

    changes = source.get("changes") or source.get("changed") or source.get("updates")
    if isinstance(changes, Mapping):
        return any(_is_status_field_name(field) for field in changes)
    if isinstance(changes, list):
        return _contains_status_field(changes)

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Mapping):
        field_name = _first_present(value, value, ("name", "field", "key", "property"))
        if _is_status_field_name(field_name):
            return True
        return any(_contains_status_field(item) for item in value.values())

    if isinstance(value, list):
        return any(_contains_status_field(item) for item in value)

    return False


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_text(value)
    return normalized in _STATUS_FIELD_NAMES


def _new_status(context: Mapping[str, Any], issue: Mapping[str, Any]) -> Any:
    for source in (context, issue):
        changed_status = _new_status_from_changes(source)
        if changed_status is not None:
            return changed_status

    for source in (context, issue):
        explicit_status = _first_present(
            source,
            source,
            (
                "newStatus",
                "new_status",
                "newState",
                "new_state",
                "statusName",
                "status_name",
                "stateName",
                "state_name",
                "workflowStateName",
                "workflow_state_name",
                "status",
                "state",
                "workflowState",
                "workflow_state",
            ),
        )
        if explicit_status is not None:
            return _name_value(explicit_status)

    return None


def _new_status_from_changes(source: Mapping[str, Any]) -> Any:
    changes = source.get("changes") or source.get("changed") or source.get("updates")

    if isinstance(changes, Mapping):
        for field, value in changes.items():
            if _is_status_field_name(field):
                return _changed_value(value)

    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        value = source.get(key)
        changed_status = _new_status_from_changed_fields(value)
        if changed_status is not None:
            return changed_status

    return None


def _new_status_from_changed_fields(value: Any) -> Any:
    if isinstance(value, Mapping):
        field_name = _first_present(value, value, ("name", "field", "key", "property"))
        if _is_status_field_name(field_name):
            return _changed_value(value)

        for nested in value.values():
            changed_status = _new_status_from_changed_fields(nested)
            if changed_status is not None:
                return changed_status

    if isinstance(value, list):
        for item in value:
            changed_status = _new_status_from_changed_fields(item)
            if changed_status is not None:
                return changed_status

    return None


def _changed_value(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return _name_value(value)

    for key in (
        "to",
        "new",
        "newValue",
        "new_value",
        "after",
        "current",
        "value",
        "name",
    ):
        if key in value:
            return _name_value(value[key])

    return None


def _first_present(
    primary: Mapping[str, Any],
    fallback: Mapping[str, Any],
    keys: tuple[str, ...],
) -> Any:
    for source in (primary, fallback):
        for key in keys:
            if key in source:
                return source[key]
    return None


def _name_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if key in value:
                return value[key]
    return value


def _string_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _has_title_prefix(title: str) -> bool:
    return title.lstrip().lower().startswith(TITLE_PREFIX.lower())


def _normalize_text(value: Any) -> str:
    value = _name_value(value)
    if value is None:
        return ""

    text = str(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": f"invalid JSON: {exc.msg}"}), file=sys.stderr)
        return 1

    result = build_issue_title_update(event)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
