"""Build Linear issue title updates for Cursor research automation.

The automation runner is expected to pass a Linear status-change event to
``build_issue_title_update``.  When the issue moves to "to research", the
function returns an action describing the title update to perform.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_UPDATE_FIELDS = {"status", "state", "workflowstate", "workflow state"}
_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "status updated",
    "status update",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
    "issue status changed",
    "issue status change",
}
_ISSUE_UPDATE_ACTIONS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update action for Linear research status events.

    The function accepts both the flat Cursor automation trigger context and
    common nested Linear webhook shapes.  It returns ``None`` when the event is
    not a status change to "to research" or when the title is already prefixed.
    """

    if not isinstance(event, Mapping):
        return None

    mappings = list(_iter_candidate_mappings(event))
    if not _is_status_change_event(mappings):
        return None

    new_status = _first_text_for_keys(
        mappings,
        (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "newWorkflowState",
            "new_workflow_state",
            "toStatus",
            "to_status",
        ),
    )
    if new_status is None:
        new_status = _first_text_for_keys(
            mappings,
            ("status", "state", "workflowState", "workflow_state"),
        )

    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text_for_keys(
        mappings,
        ("issueId", "issue_id", "identifier", "id"),
    )
    title = _first_text_for_keys(mappings, ("title",))
    if not issue_id or not title:
        return None

    if _title_has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _iter_candidate_mappings(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely metadata and issue objects from flat or nested payloads."""

    seen: set[int] = set()

    def visit(value: Any) -> Iterable[Mapping[str, Any]]:
        if not isinstance(value, Mapping):
            return
        value_id = id(value)
        if value_id in seen:
            return
        seen.add(value_id)
        yield value

        for key in (
            "triggerContext",
            "trigger_context",
            "payload",
            "data",
            "issue",
            "node",
            "object",
        ):
            child = value.get(key)
            if isinstance(child, Mapping):
                yield from visit(child)

    yield from visit(event)


def _is_status_change_event(mappings: Iterable[Mapping[str, Any]]) -> bool:
    saw_issue_update = False
    saw_status_field_update = False

    for mapping in mappings:
        for key in ("trigger", "event", "type", "action"):
            normalized = _normalize_words(_text_value(mapping.get(key)))
            if normalized in _STATUS_CHANGE_TRIGGERS:
                return True
            if normalized in _ISSUE_UPDATE_ACTIONS:
                saw_issue_update = True

        if _updated_fields_include_status(mapping):
            saw_status_field_update = True

        if saw_issue_update and saw_status_field_update:
            return True

    return False


def _updated_fields_include_status(mapping: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = mapping.get(key)
        if fields is None:
            continue
        if isinstance(fields, str):
            values = [fields]
        elif isinstance(fields, Mapping):
            values = fields.keys()
        elif isinstance(fields, Iterable):
            values = fields
        else:
            continue

        for value in values:
            if _normalize_words(_text_value(value)) in _STATUS_UPDATE_FIELDS:
                return True

    return False


def _first_text_for_keys(
    mappings: Iterable[Mapping[str, Any]], keys: Iterable[str]
) -> str | None:
    for mapping in mappings:
        for key in keys:
            value = _text_value(mapping.get(key))
            if value:
                return value
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "id"):
            text = _text_value(value.get(key))
            if text:
                return text

    return None


def _normalize_words(value: str | None) -> str | None:
    if value is None:
        return None

    with_camel_spaces = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    separated = re.sub(r"[^A-Za-z0-9]+", " ", with_camel_spaces)
    normalized = " ".join(separated.lower().split())
    return normalized or None


def _title_has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
