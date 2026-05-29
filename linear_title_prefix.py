"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
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
    """Return a Linear title update action when an issue enters To Research.

    The Cursor automation trigger passes a flat ``triggerContext`` payload, while
    Linear webhooks tend to nest issue data under ``data`` or ``issue``. This
    function accepts both shapes and returns ``None`` for non-matching events.
    """

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
    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely metadata and issue-data dictionaries in priority order."""

    contexts: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            contexts.append(issue)
        contexts.append(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        contexts.append(issue)

    contexts.append(event)
    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    normalized_events = {
        _normalize(value)
        for context in contexts
        for key in ("trigger", "event", "eventType", "action", "type")
        for value in (context.get(key),)
        if value is not None
    }

    if "status changed" in normalized_events or "status change" in normalized_events:
        return True

    issue_update_events = {
        "update",
        "updated",
        "issue update",
        "issue updated",
        "updated issue",
    }
    if normalized_events.intersection(issue_update_events):
        return _updated_status_fields(contexts)

    return False


def _updated_status_fields(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = context.get(key)
            if isinstance(fields, str):
                fields = [fields]
            if isinstance(fields, Iterable):
                for field in fields:
                    if _normalize(field) in {"status", "state", "workflow state"}:
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
        for key in ("state", "workflowState", "workflow_state"):
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
    result = build_issue_title_update(json.load(sys.stdin))
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
