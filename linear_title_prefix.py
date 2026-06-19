"""Build Linear issue-title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}
_DIRECT_STATUS_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statusupdated",
    "statusupdate",
}
_ISSUE_UPDATED_TRIGGERS = {
    "issueupdated",
    "updatedissue",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update action when an issue moves to research.

    The function accepts Cursor automation payloads and common Linear webhook
    shapes. It is intentionally side-effect free so callers can decide how to
    apply the returned action.
    """

    if not isinstance(event, Mapping):
        return None

    context = _merge_context(event)
    if not _is_status_change_event(event) or _normalized_text(_extract_new_status(context)) != TARGET_STATUS:
        return None

    issue_id = _first_string(context, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_string(context, ("title", "name"))
    if not issue_id or not title:
        return None

    trimmed_title = title.strip()
    if not trimmed_title or _has_research_prefix(trimmed_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {trimmed_title}",
    }


def _merge_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge issue data with outer trigger metadata, preferring outer fields."""

    contexts = _context_candidates(event)
    merged: dict[str, Any] = {}
    for context in reversed(contexts):
        merged.update(context)
    return merged


def _context_candidates(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, Mapping):
        return []

    candidates: list[Mapping[str, Any]] = [value]

    automation_info = value.get("automation_trigger_info")
    if isinstance(automation_info, Mapping):
        candidates.extend(_context_candidates(automation_info.get("triggerContext")))

    trigger_context = value.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        candidates.extend(_context_candidates(trigger_context))

    for key in ("data", "payload"):
        nested = value.get(key)
        if isinstance(nested, Mapping):
            candidates.extend(_context_candidates(nested))

    for key in ("issue", "node"):
        issue = value.get(key)
        if isinstance(issue, Mapping):
            candidates.append(issue)

    return candidates


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_tokens = {
        _normalized_token(value)
        for context in _context_candidates(event)
        for key in ("trigger", "webhookType", "action", "type")
        if isinstance((value := context.get(key)), str)
    }
    trigger_tokens.discard("")

    if trigger_tokens & _DIRECT_STATUS_TRIGGERS:
        return True

    if trigger_tokens & _ISSUE_UPDATED_TRIGGERS:
        return _status_was_updated(event)

    return False


def _status_was_updated(event: Mapping[str, Any]) -> bool:
    for context in _context_candidates(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(context.get(key)):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping) and any(_is_status_field_name(key) for key in changes):
            return True
        if isinstance(changes, list) and any(_contains_status_field(change) for change in changes):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) for key in value)
    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field_name(value: Any) -> bool:
    return isinstance(value, str) and _normalized_token(value) in {
        _normalized_token(name) for name in _STATUS_FIELD_NAMES
    }


def _extract_new_status(context: Mapping[str, Any]) -> str | None:
    explicit_status = _first_string(
        context,
        (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "statusName",
            "status_name",
        ),
    )
    if explicit_status:
        return explicit_status

    for key in ("state", "workflowState", "workflow_state", "status"):
        value = context.get(key)
        if isinstance(value, Mapping):
            status_name = _first_string(value, ("name", "title", "label"))
            if status_name:
                return status_name
        elif isinstance(value, str):
            return value

    for key in ("changes", "status", "state", "workflowState", "workflow_state"):
        status_name = _status_name_from_change(context.get(key))
        if status_name:
            return status_name

    return None


def _status_name_from_change(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for field_name in ("status", "state", "workflowState", "workflow_state"):
            nested_change = change.get(field_name)
            status_name = _status_name_from_change(nested_change)
            if status_name:
                return status_name

        for key in ("to", "newValue", "new_value", "after"):
            value = change.get(key)
            if isinstance(value, Mapping):
                status_name = _first_string(value, ("name", "title", "label"))
                if status_name:
                    return status_name
            elif isinstance(value, str):
                return value
    return None


def _first_string(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalized_text(value: str | None) -> str | None:
    if value is None:
        return None
    return " ".join(_split_words(value))


def _normalized_token(value: str) -> str:
    return "".join(_split_words(value))


def _split_words(value: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    return re.findall(r"[a-z0-9]+", spaced.casefold())


def main() -> int:
    """Read a JSON event from stdin and print the title-update action."""

    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
