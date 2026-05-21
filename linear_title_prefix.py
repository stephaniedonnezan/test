"""Build title update actions for Linear issues moved to research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "stateid", "workflowstateid"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research.

    The Cursor automation trigger payloads are intentionally loose, so this
    accepts both the flat trigger context and common nested Linear webhook forms.
    """
    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _extract_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(contexts)
    title = _extract_title(contexts)
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload sections in the order most likely to contain issue data."""
    root = event
    trigger_context = _mapping_at(root, "triggerContext") or _mapping_at(root, "trigger_context")
    data = _mapping_at(root, "data")
    root_issue = _mapping_at(root, "issue")
    data_issue = _mapping_at(data, "issue") if data else None
    trigger_issue = _mapping_at(trigger_context, "issue") if trigger_context else None

    ordered = [
        trigger_context,
        trigger_issue,
        data_issue,
        data,
        root_issue,
        root,
    ]

    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()
    for context in ordered:
        if context and id(context) not in seen:
            contexts.append(context)
            seen.add(id(context))
    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    trigger_values = []
    for context in contexts:
        for key in ("trigger", "event", "action", "type", "webhookType", "webhook_type"):
            value = context.get(key)
            if isinstance(value, str):
                trigger_values.append(_normalize(value))

    if any("status changed" in value or "status change" in value for value in trigger_values):
        return True

    is_issue_update = any(
        value in {"update", "updated", "issue updated", "updated issue"} for value in trigger_values
    )
    return is_issue_update and any(_updated_fields_include_status(context) for context in contexts)


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    for key in (
        "updatedFields",
        "updated_fields",
        "changedFields",
        "changed_fields",
        "changes",
        "updatedFrom",
        "updated_from",
    ):
        value = context.get(key)
        if value is not None and _contains_status_field(value):
            return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        return any(_normalize_field_name(key) in STATUS_FIELD_NAMES for key in value.keys())
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _extract_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in ("newStatus", "new_status", "newState", "new_state"):
            status = _status_name(context.get(key))
            if status:
                return status

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _status_name(context.get(key))
            if status:
                return status

    return None


def _extract_issue_id(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in ("issueId", "issue_id", "identifier", "id"):
            issue_id = context.get(key)
            if isinstance(issue_id, str) and issue_id.strip():
                return issue_id.strip()
    return None


def _extract_title(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        title = context.get("title")
        if isinstance(title, str) and title.strip():
            return title.strip()
    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested_value = value.get(key)
            if isinstance(nested_value, str) and nested_value.strip():
                return nested_value
    return None


def _mapping_at(mapping: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if mapping is None:
        return None
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None
    with_spaces = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value))
    with_spaces = re.sub(r"[^A-Za-z0-9]+", " ", with_spaces)
    return re.sub(r"\s+", " ", with_spaces).strip().casefold()


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def main() -> int:
    """Read a JSON event from stdin and print the generated action, if any."""
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
