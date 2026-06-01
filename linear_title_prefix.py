"""Build title updates for Linear issues entering research.

The automation runner can pass either the flattened trigger context used by
Cursor automations or a nested Linear webhook payload. This module keeps the
decision pure: it returns the title update to apply, or ``None`` when the event
is not a status change to "to research".
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TITLE_SEPARATOR = ": "
RESEARCH_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a Linear issue title update action for research status changes."""

    if not isinstance(event, Mapping):
        return None

    contexts = list(_iter_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    if _normalize_text(_first_text(contexts, _status_candidates)) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(contexts, _issue_id_candidates)
    title = _first_text(contexts, _title_candidates)
    if not issue_id or not title:
        return None

    if title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}{TITLE_SEPARATOR}{title}",
    }


def _iter_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely payload layers from most specific to least specific."""

    keys = ("triggerContext", "data", "issue", "node", "object")
    seen: set[int] = set()

    def walk(value: Any) -> Iterable[Mapping[str, Any]]:
        if not isinstance(value, Mapping) or id(value) in seen:
            return
        seen.add(id(value))
        yield value
        for key in keys:
            child = value.get(key)
            if isinstance(child, Mapping):
                yield from walk(child)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield from walk(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        yield from walk(data)

    yield from walk(event)


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = [
        value
        for context in contexts
        for key in ("trigger", "webhookType", "action", "type", "eventType")
        if (value := _text(context.get(key)))
    ]

    if any(_is_direct_status_change(value) for value in trigger_values):
        return True

    if any(_is_issue_update(value) for value in trigger_values):
        return any(_updated_fields_include_status(context) for context in contexts)

    return False


def _is_direct_status_change(value: str) -> bool:
    return _normalize_text(value) in {"status changed", "status change"}


def _is_issue_update(value: str) -> bool:
    normalized = _normalize_text(value)
    return normalized in {"update", "updated", "issue updated", "updated issue"}


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = context.get(key)
        if fields is None:
            continue
        if any(_normalize_field_name(field) in STATUS_FIELDS for field in _iter_field_names(fields)):
            return True
    return False


def _iter_field_names(fields: Any) -> Iterable[str]:
    if isinstance(fields, str):
        yield fields
    elif isinstance(fields, Mapping):
        yield from (str(key) for key in fields)
    elif isinstance(fields, Iterable):
        for field in fields:
            if isinstance(field, Mapping):
                for key in ("name", "field", "key"):
                    if key in field:
                        yield str(field[key])
            else:
                yield str(field)


def _status_candidates(context: Mapping[str, Any]) -> Iterable[Any]:
    for key in ("newStatus", "new_status", "toStatus", "to_status", "status"):
        yield context.get(key)
    yield _nested_name(context.get("state"))
    yield _nested_name(context.get("workflowState"))
    yield _nested_name(context.get("workflow_state"))


def _issue_id_candidates(context: Mapping[str, Any]) -> Iterable[Any]:
    for key in ("id", "issueId", "issue_id", "identifier"):
        yield context.get(key)


def _title_candidates(context: Mapping[str, Any]) -> Iterable[Any]:
    yield context.get("title")


def _nested_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        return value.get("name")
    return None


def _first_text(
    contexts: Iterable[Mapping[str, Any]], candidates: Any
) -> str | None:
    for context in contexts:
        for value in candidates(context):
            text = _text(value)
            if text:
                return text
    return None


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[\s_-]+", " ", separated).strip().lower()


def _normalize_field_name(value: str) -> str:
    return _normalize_text(value).replace(" ", "")


def main() -> int:
    """Read an event from stdin and write the computed action as JSON."""

    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is None:
        return 0
    json.dump(action, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
