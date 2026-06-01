"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "newstatus",
    "newstatusname",
    "newstate",
    "newstatename",
    "newworkflowstate",
    "newworkflowstatename",
    "status",
    "statusname",
    "state",
    "statename",
    "workflowstate",
    "workflowstatename",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue enters To Research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _new_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility alias for automation runtimes that look for event handlers."""

    return build_issue_title_update(event)


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely metadata and issue-data dictionaries in priority order."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")

    for container in (trigger_context, data, issue):
        if isinstance(container, Mapping):
            add(container.get("issue"))
            add(container.get("data"))
            add(container)

    add(event)
    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    normalized_events = {
        _normalize(value)
        for context in contexts
        for key in ("trigger", "event", "eventType", "webhookType", "type", "action")
        for value in (context.get(key),)
        if value is not None
    }

    status_change_events = {
        "status changed",
        "status change",
        "state changed",
        "workflow state changed",
    }
    if normalized_events.intersection(status_change_events):
        return True

    issue_update_events = {
        "update",
        "updated",
        "issue update",
        "issue updated",
        "updated issue",
    }
    if normalized_events.intersection(issue_update_events):
        return _updated_fields_include_status(contexts)

    return False


def _updated_fields_include_status(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = context.get(key)
            if isinstance(fields, str):
                fields = [fields]
            elif isinstance(fields, Mapping):
                fields = fields.keys()
            elif not isinstance(fields, Iterable):
                continue

            if any(_field_name(field) in _STATUS_FIELD_NAMES for field in fields):
                return True

        updated_from = context.get("updatedFrom")
        if isinstance(updated_from, Mapping):
            if any(_field_name(field) in _STATUS_FIELD_NAMES for field in updated_from):
                return True

    return False


def _new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key, value in context.items():
            if _field_name(key) in _STATUS_FIELD_NAMES:
                status = _coerce_text(value)
                if status:
                    return status

    for context in contexts:
        for key in ("state", "workflowState", "workflow_state", "status"):
            value = context.get(key)
            if isinstance(value, Mapping):
                status = _coerce_text(value.get("name"))
                if status:
                    return status

    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _coerce_text(context.get(key))
            if value and value.strip():
                return value
    return None


def _coerce_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "id", "identifier"):
            text = _coerce_text(value.get(key))
            if text:
                return text
    return None


def _field_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    """Read a JSON payload from stdin and print the requested update action."""

    try:
        result = build_issue_title_update(json.load(sys.stdin))
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
