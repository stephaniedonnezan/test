"""Build Linear issue title updates for issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
TITLE_UPDATE_ACTION = "update_issue_title"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "statuschange",
    "statuschanged",
    "statusupdated",
    "statechange",
    "statechanged",
    "stateupdated",
    "workflowstatechange",
    "workflowstatechanged",
    "workflowstateupdated",
}
_ISSUE_UPDATE_EVENTS = {
    "issueupdated",
    "updatedissue",
    "update",
    "updated",
}
_STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research.

    The automation trigger payload can be a flat trigger context or a nested
    Linear webhook body. This helper is intentionally side-effect free so the
    automation runner can decide how to execute the returned action.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _issue_status(contexts)
    if _normalize_label(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    issue_id = issue_id.strip()
    title = title.strip()
    if not issue_id or not title or title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": TITLE_UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility alias for automation entrypoints named after the event."""

    return build_issue_title_update(event)


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return nested Linear payload contexts, ordered issue-specific first."""

    contexts: list[Mapping[str, Any]] = []

    def visit(context: Mapping[str, Any]) -> None:
        for key in ("issue", "data", "triggerContext"):
            value = context.get(key)
            if isinstance(value, Mapping):
                visit(value)

        if context not in contexts:
            contexts.append(context)

    visit(event)
    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    normalized_events: list[str] = []

    for context in contexts:
        for key in ("trigger", "action", "type", "event", "webhookType"):
            value = context.get(key)
            if isinstance(value, str):
                normalized_events.append(_compact_label(value))

    if any(event in _DIRECT_STATUS_CHANGE_EVENTS for event in normalized_events):
        return True

    if any(event in _ISSUE_UPDATE_EVENTS for event in normalized_events):
        return _updated_fields_include_status(contexts)

    return False


def _updated_fields_include_status(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = context.get(key)
            if isinstance(fields, str):
                if _is_status_field(fields):
                    return True
            elif isinstance(fields, Mapping):
                if any(_is_status_field(field) for field in fields):
                    return True
            elif isinstance(fields, Iterable):
                if any(_field_item_indicates_status(field) for field in fields):
                    return True

    return False


def _field_item_indicates_status(field: Any) -> bool:
    if isinstance(field, Mapping):
        field_name = _first_text([field], ("field", "name", "key", "id"))
        return field_name is not None and _is_status_field(field_name)

    return isinstance(field, str) and _is_status_field(field)


def _is_status_field(field: str) -> bool:
    return _compact_label(field) in _STATUS_FIELD_NAMES


def _issue_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
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
    )
    if direct_status:
        return direct_status

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
            if isinstance(value, Mapping):
                name = _first_text([value], ("name", "title", "label"))
                if name:
                    return name

    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value

    return None


def _normalize_label(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return " ".join(normalized.lower().split())


def _compact_label(value: str) -> str:
    return _normalize_label(value).replace(" ", "")


def main() -> int:
    """Read a JSON payload from stdin and print the title-update action."""

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(payload)
    print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
