"""Build title-update actions for Linear issues entering research status."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research.

    The Cursor automation trigger provides a flat ``triggerContext`` object, while
    Linear webhooks can wrap issue data under ``data`` or ``issue``. This function
    accepts both shapes and leaves non-matching events untouched.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_walk_mappings(event))
    if not _is_status_change(contexts):
        return None

    status = _first_status(contexts)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _first_string(contexts, ("issueId", "issue_id", "id", "identifier"))
    title = _first_string(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {stripped_title}",
    }


def _walk_mappings(value: Any) -> tuple[Mapping[str, Any], ...]:
    """Return nested dictionaries from outermost to innermost."""

    found: list[Mapping[str, Any]] = []

    def visit(candidate: Any) -> None:
        if not isinstance(candidate, Mapping) or candidate in found:
            return

        found.append(candidate)
        for key in (
            "automation_trigger_info",
            "triggerContext",
            "trigger_context",
            "data",
            "issue",
            "state",
            "status",
            "workflowState",
            "workflow_state",
        ):
            visit(candidate.get(key))

    visit(value)
    return tuple(found)


def _is_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            normalized = _normalize_text(context.get(key))
            if normalized in {"status changed", "status change", "status updated"}:
                return True

        normalized_action = _normalize_text(context.get("action"))
        normalized_type = _normalize_text(context.get("type"))
        if normalized_action in {"update", "updated"} or normalized_type in {
            "issue updated",
            "updated issue",
        }:
            updated_fields = _updated_fields(context.get("updatedFields"))
            updated_fields |= _updated_fields(context.get("updated_fields"))
            if updated_fields & STATUS_FIELDS:
                return True

    return False


def _updated_fields(value: Any) -> set[str]:
    if isinstance(value, str):
        return {_normalize_field(value)}

    if isinstance(value, Mapping):
        return {_normalize_field(key) for key in value}

    if isinstance(value, (list, tuple, set)):
        return {_normalize_field(item) for item in value if isinstance(item, str)}

    return set()


def _first_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "status_name"):
        value = _first_string(contexts, (key,))
        if value:
            return value

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = context.get(key)
            if isinstance(value, Mapping):
                nested_name = _mapping_string(value, ("name", "title"))
                if nested_name:
                    return nested_name
            elif isinstance(value, str) and value.strip():
                return value

    return None


def _first_string(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        value = _mapping_string(context, keys)
        if value:
            return value

    return None


def _mapping_string(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_field(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _normalize_text(value))


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    separated = re.sub(r"[^A-Za-z0-9]+", " ", separated)
    return " ".join(separated.lower().split())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
