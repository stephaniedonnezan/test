"""Build Linear issue title updates for Cursor research status changes.

The automation receives webhook-like payloads from Cursor/Linear. When an issue
is moved to "to research", this module returns a small action object instructing
the caller to prefix the Linear issue title with "Cursor researching".
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
UPDATE_ACTION = "update_issue_title"

_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_ISSUE_UPDATE_TRIGGERS = {
    "issue updated",
    "updated issue",
    "update",
    "updated",
}
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "workflowstate",
    "workflow status",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title update action for "to research" transitions.

    The function is intentionally side-effect free so the surrounding automation
    can decide how to apply the returned action.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize(_extract_new_status(event)) != "to research":
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_issue_title(event)
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{RESEARCH_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = {
        _normalize(value)
        for context in _iter_contexts(event)
        for key in ("trigger", "webhookType", "webhook_type", "action", "type")
        if (value := context.get(key)) is not None
    }

    if trigger_values & _STATUS_CHANGE_TRIGGERS:
        return True

    if trigger_values & _ISSUE_UPDATE_TRIGGERS:
        return _updated_fields_include_status(event)

    # Some payloads omit a trigger name but include before/after status fields.
    return bool(_extract_new_status(event) and _extract_old_status(event))


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for context in _iter_contexts(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(context.get(key)):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            if _contains_status_field(changes.keys()):
                return True

    return False


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    explicit_paths = (
        ("newStatus",),
        ("new_status",),
        ("toStatus",),
        ("to_status",),
        ("targetStatus",),
        ("target_status",),
        ("newState",),
        ("new_state",),
        ("statusName",),
        ("status_name",),
        ("stateName",),
        ("state_name",),
        ("workflowStateName",),
        ("workflow_state_name",),
    )
    status_paths = (
        ("status", "name"),
        ("state", "name"),
        ("workflowState", "name"),
        ("workflow_state", "name"),
        ("status",),
        ("state",),
        ("workflowState",),
        ("workflow_state",),
    )

    return _extract_first_text(event, (*explicit_paths, *status_paths))


def _extract_old_status(event: Mapping[str, Any]) -> str | None:
    return _extract_first_text(
        event,
        (
            ("oldStatus",),
            ("old_status",),
            ("fromStatus",),
            ("from_status",),
            ("previousStatus",),
            ("previous_status",),
            ("oldState",),
            ("old_state",),
            ("previousState",),
            ("previous_state",),
        ),
    )


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    preferred_paths = (
        ("issueId",),
        ("issue_id",),
        ("identifier",),
        ("key",),
        ("issue", "identifier"),
        ("issue", "id"),
        ("data", "issue", "identifier"),
        ("data", "issue", "id"),
    )
    issue_id = _extract_first_text(event, preferred_paths)
    if issue_id:
        return issue_id

    for context in _iter_contexts(event):
        if context is event and any(key in context for key in ("automationId", "triggerContext")):
            continue
        value = _text_from_value(context.get("id"))
        if value:
            return value

    return None


def _extract_issue_title(event: Mapping[str, Any]) -> str | None:
    return _extract_first_text(
        event,
        (
            ("title",),
            ("issue", "title"),
            ("data", "issue", "title"),
        ),
    )


def _extract_first_text(
    event: Mapping[str, Any],
    paths: Iterable[tuple[str, ...]],
) -> str | None:
    contexts = tuple(_iter_contexts(event))
    for path in paths:
        for context in contexts:
            value = _get_path(context, path)
            text = _text_from_value(value)
            if text:
                return text
    return None


def _iter_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    seen: set[int] = set()

    def add(value: Any) -> Iterable[Mapping[str, Any]]:
        if not isinstance(value, Mapping):
            return
        object_id = id(value)
        if object_id in seen:
            return
        seen.add(object_id)
        yield value

    for key in ("triggerContext", "trigger_context"):
        yield from add(event.get(key))

    data = event.get("data")
    if isinstance(data, Mapping):
        yield from add(data.get("issue"))

    yield from add(event.get("issue"))
    yield from add(data)
    yield from add(event)


def _get_path(context: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = context
    for key in path:
        if not isinstance(value, Mapping) or key not in value:
            return None
        value = value[key]
    return value


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        values = value.keys()
    elif isinstance(value, Iterable):
        values = value
    else:
        return False

    return any(_normalize(item) in _STATUS_FIELD_NAMES for item in values)


def _text_from_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "id"):
            text = _text_from_value(value.get(key))
            if text:
                return text
        return None

    if value is None or isinstance(value, bool):
        return None

    text = str(value).strip()
    return text or None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(RESEARCH_PREFIX.casefold())


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def main() -> int:
    """Read a JSON payload from stdin and print the computed action."""

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(payload)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
