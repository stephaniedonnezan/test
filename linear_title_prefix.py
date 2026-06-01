"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
TITLE_UPDATE_ACTION = "update_issue_title"

_STATUS_CHANGE_MARKERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_ISSUE_UPDATED_MARKERS = {
    "issue updated",
    "updated issue",
    "issue update",
    "update issue",
    "update",
    "updated",
}
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
    "workflow status",
    "workflow status id",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research.

    Cursor Linear automation payloads can be flat or nested below keys like
    ``triggerContext``, ``data``, and ``issue``. This helper normalizes those
    common shapes, recognizes status-change events, and keeps the action
    idempotent by skipping titles that already have the research prefix.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _new_status(contexts)
    if _normalize_label(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(contexts, ("title", "name"))
    if issue_id is None or title is None:
        return None

    title = title.strip()
    if not title or title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": TITLE_UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility alias for automation entrypoints named as event handlers."""

    return build_issue_title_update(event)


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely event and issue mappings in most-specific-first order."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping):
            return

        for key in ("triggerContext", "data", "issue"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                visit(nested)

        add(value)

    visit(event)
    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    saw_issue_update = False

    for context in contexts:
        for key in ("trigger", "action", "event", "eventType", "type", "webhookType"):
            marker = _normalize_label(context.get(key))
            if marker in _STATUS_CHANGE_MARKERS:
                return True
            if marker in _ISSUE_UPDATED_MARKERS:
                saw_issue_update = True

    return saw_issue_update and _updated_fields_include_status(contexts)


def _updated_fields_include_status(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _fields_include_status(context.get(key)):
                return True

        updated_from = context.get("updatedFrom")
        if isinstance(updated_from, Mapping) and _fields_include_status(updated_from):
            return True

    return False


def _fields_include_status(fields: Any) -> bool:
    if isinstance(fields, str):
        return _is_status_field(fields)

    if isinstance(fields, Mapping):
        return any(_is_status_field(key) for key in fields)

    if isinstance(fields, Iterable) and not isinstance(
        fields, (str, bytes, bytearray, Mapping)
    ):
        return any(_is_status_field(_field_name(field)) for field in fields)

    return False


def _field_name(field: Any) -> Any:
    if isinstance(field, Mapping):
        return field.get("name") or field.get("field") or field.get("key")
    return field


def _is_status_field(field: Any) -> bool:
    return _normalize_label(field) in _STATUS_FIELD_NAMES


def _new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    direct = _first_text(
        contexts,
        (
            "newStatus",
            "new_status",
            "statusName",
            "stateName",
            "state_name",
            "workflowStateName",
            "workflow_state_name",
        ),
    )
    if direct is not None:
        return direct

    for context in contexts:
        for key in ("state", "workflowState", "workflow_state", "status"):
            value = context.get(key)
            if isinstance(value, Mapping):
                nested = _first_text((value,), ("name", "title", "label"))
                if nested is not None:
                    return nested
            elif isinstance(value, str) and value.strip():
                return value

    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _normalize_label(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", words)
    return " ".join(words.lower().split())


def main() -> int:
    """Read a JSON payload from stdin and print the requested update, if any."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
