"""Build title update actions for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
TITLE_UPDATE_ACTION = "update_issue_title"

_CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_WORD = re.compile(r"[^A-Za-z0-9]+")
_WHITESPACE = re.compile(r"\s+")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research.

    The function is intentionally side-effect free so the automation runner can
    decide how to apply the returned action to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    if _normalized_status(_status_from_change(context)) != TARGET_STATUS:
        return None

    issue_id = _issue_id(context)
    title = _issue_title(context)
    if issue_id is None or title is None:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": TITLE_UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor and Linear webhook shapes into one flat context."""

    context: dict[str, Any] = {}

    for key in ("triggerContext", "data", "issue"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            context.update(_event_context(nested))

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            context.update(_event_context(issue))

    # Top-level fields should win over nested issue fields, because Cursor's
    # triggerContext carries the freshest trigger metadata.
    context.update(event)
    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        context.get("trigger"),
        context.get("webhookType"),
        context.get("action"),
        context.get("type"),
    ]

    if any(_normalized_text(value) in {"status changed", "status change"} for value in trigger_values):
        return True

    if any(_normalized_text(value) in {"update", "updated", "issue updated", "updated issue"} for value in trigger_values):
        return _mentions_status_field(context)

    return False


def _mentions_status_field(context: Mapping[str, Any]) -> bool:
    status_fields = {
        "status",
        "state",
        "workflowstate",
        "workflow state",
        "state id",
        "status id",
    }

    for key in ("updatedFields", "updated_fields"):
        fields = context.get(key)
        if isinstance(fields, str):
            values: Sequence[Any] = [fields]
        elif isinstance(fields, Sequence) and not isinstance(fields, (bytes, bytearray, str)):
            values = fields
        else:
            values = []

        if any(_normalized_text(value) in status_fields for value in values):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalized_text(key) in status_fields for key in changes)

    return False


def _status_from_change(context: Mapping[str, Any]) -> Any:
    for key in (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "status",
        "state",
        "workflowState",
        "workflow_state",
    ):
        value = context.get(key)
        status = _status_name(value)
        if status is not None:
            return status

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _status_name(_changed_to_value(changes.get(key)))
            if status is not None:
                return status

    return None


def _changed_to_value(change: Any) -> Any:
    if isinstance(change, Mapping):
        for key in ("to", "new", "newValue", "after"):
            if key in change:
                return change[key]
    return change


def _status_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            status = _status_name(value.get(key))
            if status is not None:
                return status
        return None

    text = _clean_text(value)
    return text or None


def _issue_id(context: Mapping[str, Any]) -> str | None:
    for key in ("issueId", "issue_id", "identifier", "key", "id"):
        text = _clean_text(context.get(key))
        if text:
            return text
    return None


def _issue_title(context: Mapping[str, Any]) -> str | None:
    text = _clean_text(context.get("title"))
    return text or None


def _has_research_prefix(title: str) -> bool:
    return _normalized_text(title).startswith(_normalized_text(TITLE_PREFIX))


def _normalized_status(value: Any) -> str:
    return _normalized_text(_status_name(value))


def _normalized_text(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return ""

    text = _CAMEL_CASE_BOUNDARY.sub(" ", text)
    text = _NON_WORD.sub(" ", text)
    return _WHITESPACE.sub(" ", text).strip().lower()


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    text = value.strip()
    return text or None


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
