"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state updated",
    "workflow state changed",
    "workflow state updated",
}
_ISSUE_UPDATE_EVENTS = {
    "issue updated",
    "updated issue",
    "update",
    "updated",
}
_STATUS_FIELD_NAMES = {
    "status",
    "status id",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
    "workflowstate",
    "workflowstate id",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to to research.

    The function is intentionally side-effect free so automation runners can use
    it with their preferred Linear client. It returns ``None`` for unrelated
    webhooks or malformed payloads.
    """

    if not isinstance(event, Mapping):
        return None

    context_maps = _context_maps(event)
    if not _is_status_change_event(context_maps):
        return None

    new_status = _issue_status(context_maps)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_title = _first_text(context_maps, ("title", "name"))
    issue_id = _first_text(
        context_maps,
        ("issueId", "issue_id", "identifier", "id"),
        reverse=True,
    )
    if not issue_title or not issue_id:
        return None

    issue_title = issue_title.strip()
    if _normalize(issue_title).startswith(_normalize(TITLE_PREFIX)):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {issue_title}",
    }


def _context_maps(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload contexts from most issue-specific to most global."""

    trigger_context = _as_mapping(event.get("triggerContext"))
    data = _as_mapping(event.get("data"))
    issue = _as_mapping(event.get("issue"))

    for container in (trigger_context, data):
        nested_issue = _as_mapping(container.get("issue")) if container else None
        if nested_issue:
            issue = nested_issue
            break

    contexts: list[Mapping[str, Any]] = []
    for candidate in (issue, data, trigger_context, event):
        if candidate and candidate not in contexts:
            contexts.append(candidate)
    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    event_values = []
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type", "event"):
            value = context.get(key)
            if isinstance(value, str):
                event_values.append(_normalize(value))

    if any(value in _DIRECT_STATUS_CHANGE_EVENTS for value in event_values):
        return True

    if any(value in _ISSUE_UPDATE_EVENTS for value in event_values):
        return _updated_fields_include_status(contexts)

    return False


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        raw_fields = (
            context.get("updatedFields")
            or context.get("updated_fields")
            or context.get("changedFields")
            or context.get("changed_fields")
        )
        if isinstance(raw_fields, str):
            fields = [raw_fields]
        elif isinstance(raw_fields, list | tuple | set):
            fields = list(raw_fields)
        else:
            continue

        for field in fields:
            if isinstance(field, Mapping):
                field_name = _first_text([field], ("field", "name", "key", "id"))
            else:
                field_name = str(field)
            if _normalize(field_name) in _STATUS_FIELD_NAMES:
                return True

    return False


def _issue_status(contexts: list[Mapping[str, Any]]) -> str | None:
    direct_status = _first_text(
        contexts,
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
        ),
        reverse=True,
    )
    if direct_status:
        return direct_status

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = context.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, Mapping):
                name = _first_text([value], ("name", "title"))
                if name:
                    return name

    return None


def _first_text(
    contexts: list[Mapping[str, Any]],
    keys: tuple[str, ...],
    *,
    reverse: bool = False,
) -> str | None:
    iterable = reversed(contexts) if reverse else contexts
    for context in iterable:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    """Read a JSON payload from stdin and print the title-update action."""

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
