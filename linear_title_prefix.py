"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "workflow state changed",
}
GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title update when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    contexts = list(_candidate_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    status = _new_status(contexts)
    if _normalize(status) != _normalize(TARGET_STATUS):
        return None

    issue_id = _first_text(contexts, ("id", "issueId", "issue_id", "identifier", "key"))
    title = _first_text(contexts, ("title",))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if not clean_title or _has_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield useful flat and nested webhook payload locations in priority order."""

    seen: set[int] = set()

    def add(value: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            yield value

    trigger_context = event.get("triggerContext")
    for value in add(trigger_context):
        yield value

    data = event.get("data")
    if isinstance(data, Mapping):
        for value in add(data.get("issue")):
            yield value

    for value in add(event.get("issue")):
        yield value

    for key in ("data", "payload"):
        nested = event.get(key)
        for value in add(nested):
            yield value

        if isinstance(nested, Mapping):
            for child_key in ("issue", "data", "payload", "state", "workflowState", "status"):
                for value in add(nested.get(child_key)):
                    yield value

    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            for child_key in ("state", "workflowState", "status"):
                for value in add(issue.get(child_key)):
                    yield value

    for value in add(event):
        yield value


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    contexts = list(contexts)

    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type", "eventType"):
            event_name = _normalize(context.get(key))
            if event_name in STATUS_CHANGE_EVENTS:
                return True

    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type", "eventType"):
            event_name = _normalize(context.get(key))
            if event_name in GENERIC_UPDATE_EVENTS and _updated_status_field(context):
                return True

    return False


def _updated_status_field(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = context.get(key)
        if isinstance(fields, str):
            if _field_is_status(fields):
                return True
        elif isinstance(fields, Iterable) and not isinstance(fields, (str, bytes, Mapping)):
            if any(_field_is_status(str(field)) for field in fields):
                return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_field_is_status(str(field)) for field in changes)

    return False


def _new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    contexts = list(contexts)

    for key in (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
    ):
        status = _first_text(contexts, (key,))
        if status:
            return status

    for context in contexts:
        changes_status = _status_from_changes(context.get("changes"))
        if changes_status:
            return changes_status

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _text_or_name(context.get(key))
            if status:
                return status

    return None


def _status_from_changes(changes: Any) -> str | None:
    if not isinstance(changes, Mapping):
        return None

    for key, value in changes.items():
        if not _field_is_status(str(key)):
            continue

        if isinstance(value, Mapping):
            for status_key in ("newValue", "new_value", "to", "after", "new", "name"):
                status = _text_or_name(value.get(status_key))
                if status:
                    return status
        else:
            status = _text_or_name(value)
            if status:
                return status

    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _text_or_name(context.get(key))
            if value:
                return value
    return None


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _text_or_name(value.get(key))
            if text:
                return text

    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _field_is_status(field: str) -> bool:
    return _normalize(field).replace(" ", "") in STATUS_FIELDS


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", spaced).strip().casefold()
    return re.sub(r"\s+", " ", words)


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
