"""Build Linear issue title updates for research status changes.

The automation trigger can arrive as a flat Cursor payload or as a nested Linear
webhook payload.  This module keeps the public surface small: pass an event into
``build_issue_title_update`` and receive the title update action when one is
needed.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action for Linear research status changes."""
    if not isinstance(event, Mapping):
        return None

    flattened = _flatten_event(event)
    if not _is_status_change_event(flattened):
        return None

    if _normalize_status(_extract_status(flattened)) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(flattened, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(flattened, ("title", "name"))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if not stripped_title or _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{RESEARCH_PREFIX}: {stripped_title}",
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge known nested payload locations while preserving top-level metadata."""
    flattened: dict[str, Any] = {}

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        flattened.update(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            flattened.update(issue)
        flattened.update(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        flattened.update(issue)

    flattened.update(event)
    return flattened


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = [
        event.get("trigger"),
        event.get("webhookType"),
        event.get("action"),
        event.get("type"),
    ]
    normalized_triggers = {
        _normalize_token(value)
        for value in trigger_values
        if isinstance(value, str) and value.strip()
    }

    if normalized_triggers & {"statuschanged", "statuschange", "statuschangedissue"}:
        return True

    if normalized_triggers & {"issueupdated", "updatedissue", "update"}:
        return _updated_fields_include_status(event.get("updatedFields"))

    return False


def _updated_fields_include_status(updated_fields: Any) -> bool:
    if updated_fields is None:
        return False

    if isinstance(updated_fields, str):
        fields = [updated_fields]
    elif isinstance(updated_fields, Mapping):
        fields = list(updated_fields.keys())
    elif isinstance(updated_fields, list | tuple | set):
        fields = list(updated_fields)
    else:
        return False

    return any(_normalize_field_name(field) in STATUS_FIELDS for field in fields)


def _extract_status(event: Mapping[str, Any]) -> Any:
    for key in ("newStatus", "new_status", "newState", "new_state"):
        value = event.get(key)
        if value:
            return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = event.get(key)
        if isinstance(value, Mapping):
            name = value.get("name")
            if name:
                return name
        elif value:
            return value

    return None


def _first_text(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = event.get(key)
        if isinstance(value, str):
            return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(RESEARCH_PREFIX.casefold())


def _normalize_status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return _split_words(value)


def _normalize_token(value: str) -> str:
    return _split_words(value).replace(" ", "")


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _split_words(value).replace(" ", "")


def _split_words(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value)
    return " ".join(value.casefold().split())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
