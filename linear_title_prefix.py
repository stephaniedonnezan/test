"""Build Linear issue title updates for research-status automation.

The automation webhook may provide a flat trigger context or a nested Linear
payload.  This module keeps the behavior small and deterministic: when an issue
status changes to "to research", prefix its title with "Cursor researching".
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action for research status changes.

    The returned value is intentionally side-effect free so an automation runner
    can decide how to apply it:

    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _first_string(
        _lookup_path(context, path)
        for context in contexts
        for path in (
            ("newStatus",),
            ("new_status",),
            ("newState",),
            ("new_state",),
            ("status", "name"),
            ("state", "name"),
            ("workflowState", "name"),
            ("workflow_state", "name"),
            ("status",),
            ("state",),
            ("workflowState",),
            ("workflow_state",),
        )
    )
    if _normalize_text(status) != RESEARCH_STATUS:
        return None

    issue_id = _first_string(
        _lookup_path(context, path)
        for context in contexts
        for path in (("id",), ("issueId",), ("issue_id",), ("identifier",))
    )
    title = _first_string(
        _lookup_path(context, path)
        for context in contexts
        for path in (("title",), ("name",))
    )
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload mappings ordered from most to least specific."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event.get("triggerContext"))
    add(event)
    add(event.get("data"))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("state"))
        add(data.get("workflowState"))

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("data"))
        add(trigger_context.get("issue"))

    return contexts


def _is_status_change_event(contexts: Sequence[Mapping[str, Any]]) -> bool:
    event_names = {
        _normalize_text(value)
        for context in contexts
        for key in ("trigger", "webhookType", "action", "type")
        if (value := context.get(key)) is not None
    }

    if event_names & {
        "status changed",
        "statuschanged",
        "state changed",
        "statechanged",
        "workflow state changed",
        "workflowstatechanged",
    }:
        return True

    if event_names & {"issue updated", "updated issue", "update", "updated"}:
        return _updated_fields_include_status(contexts)

    return False


def _updated_fields_include_status(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = context.get(key)
            if isinstance(fields, str):
                field_names = [fields]
            elif isinstance(fields, Sequence) and not isinstance(fields, (bytes, bytearray, str)):
                field_names = [str(field) for field in fields]
            else:
                continue

            if any(_normalize_text(field) in STATUS_FIELDS for field in field_names):
                return True
    return False


def _lookup_path(mapping: Mapping[str, Any], path: Sequence[str]) -> Any:
    current: Any = mapping
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _first_string(values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value
    return None


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value).strip()
    words = re.sub(r"[^a-zA-Z0-9]+", " ", words).strip().lower()
    return re.sub(r"\s+", " ", words)


def _has_title_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
