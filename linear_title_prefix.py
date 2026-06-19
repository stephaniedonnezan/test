"""Build Linear issue-title updates for research-status automation events."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_status"}
_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "issue status changed",
    "workflow status changed",
}
_GENERIC_ISSUE_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research.

    The function is intentionally side-effect free: automation runtimes can call
    it to decide whether to update Linear, and tests can validate the decision
    without needing Linear credentials.
    """

    if not isinstance(event, Mapping):
        return None

    context = _build_context(event)
    if not _is_research_status_change(context):
        return None

    issue_id = _clean_text(_first_present(context, ("issueId", "issue_id", "id", "identifier", "key")))
    title = _clean_text(_first_present(context, ("title", "name")))
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _build_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge the payload shapes Cursor and Linear commonly send."""

    context: dict[str, Any] = {}

    automation_info = event.get("automation_trigger_info")
    if isinstance(automation_info, Mapping):
        trigger_context = automation_info.get("triggerContext")
        if isinstance(trigger_context, Mapping):
            _merge_context(context, trigger_context)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        _merge_context(context, trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            _merge_context(context, issue)
        _merge_context(context, data)

    _merge_context(context, event)
    return context


def _merge_context(context: dict[str, Any], source: Mapping[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, Mapping) and key in {"data", "issue", "triggerContext", "automation_trigger_info"}:
            continue
        context[key] = value


def _is_research_status_change(context: Mapping[str, Any]) -> bool:
    if _normalize_status(_new_status(context)) != TARGET_STATUS:
        return False

    event_names = [
        _normalize_event_name(value)
        for value in _values_for_keys(context, ("trigger", "webhookType", "action", "type"))
    ]
    if any(name in _DIRECT_STATUS_CHANGE_EVENTS for name in event_names):
        return True

    if any(name in _GENERIC_ISSUE_UPDATE_EVENTS for name in event_names):
        return _mentions_status_field(context.get("updatedFields")) or _mentions_status_field(
            context.get("changes")
        )

    return False


def _new_status(context: Mapping[str, Any]) -> Any:
    explicit_status = _first_present(
        context,
        (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "statusName",
            "stateName",
            "workflowStateName",
        ),
    )
    if explicit_status is not None:
        return explicit_status

    changed_status = _status_from_changes(context.get("changes"))
    if changed_status is not None:
        return changed_status

    for key in ("status", "state", "workflowState"):
        value = context.get(key)
        if value is not None:
            return value

    return None


def _status_from_changes(changes: Any) -> Any:
    if not isinstance(changes, Mapping):
        return None

    for key, value in changes.items():
        if _is_status_field_name(key):
            if isinstance(value, Mapping):
                return _first_present(value, ("to", "toValue", "newValue", "name"))
            return value

    return None


def _values_for_keys(context: Mapping[str, Any], keys: tuple[str, ...]) -> list[Any]:
    values: list[Any] = []
    for key in keys:
        value = context.get(key)
        if value is not None:
            values.append(value)
    return values


def _first_present(context: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = context.get(key)
        if value is not None:
            return value
    return None


def _mentions_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) for key in value.keys())
    if isinstance(value, list | tuple | set):
        return any(_mentions_status_field(item) for item in value)
    return False


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_key(value)
    return normalized in _STATUS_FIELD_NAMES


def _normalize_status(value: Any) -> str | None:
    if isinstance(value, Mapping):
        value = _first_present(value, ("name", "title", "value"))
    if value is None:
        return None
    return _normalize_words(str(value))


def _normalize_event_name(value: Any) -> str | None:
    if value is None:
        return None
    return _normalize_words(str(value))


def _normalize_key(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def _normalize_words(value: str) -> str:
    with_spaces = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    with_spaces = re.sub(r"[^A-Za-z0-9]+", " ", with_spaces)
    return " ".join(with_spaces.lower().split())


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print(json.dumps({"error": f"invalid JSON: {error.msg}"}), file=sys.stderr)
        return 1

    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
