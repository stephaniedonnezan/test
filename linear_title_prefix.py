"""Build title update actions for Linear issues entering research.

The automation runtime can pass either Cursor's flattened trigger context or
Linear's nested webhook payload.  This module keeps the decision pure so it can
be tested without network access.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"
TITLE_PREFIX_RE = re.compile(rf"^\s*{re.escape(TITLE_PREFIX)}\b", re.IGNORECASE)
STATUS_CHANGE_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue enters research.

    The returned shape is intentionally simple for the surrounding automation:
    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``.
    Non-matching, incomplete, or already-prefixed events return ``None``.
    """

    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    new_status = _first_text(
        context,
        (
            "newStatus",
            "new_status",
            "status",
            "state",
            "workflowState",
            "workflow_state",
        ),
    )
    if _normalize_text(new_status) != _normalize_text(RESEARCH_STATUS):
        return None

    issue_id = _first_text(
        context,
        ("issueId", "issue_id", "id", "identifier", "key", "issueKey"),
    )
    title = _first_text(context, ("title", "name"))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if not clean_title or TITLE_PREFIX_RE.match(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten the common Cursor and Linear payload locations into one context."""

    context: dict[str, Any] = {}

    # Inner objects carry issue details, while outer objects carry trigger data.
    for source in (
        _mapping_at(event, ("data", "issue")),
        _mapping_at(event, ("issue",)),
        _mapping_at(event, ("triggerContext", "data", "issue")),
        _mapping_at(event, ("triggerContext", "issue")),
        _mapping_at(event, ("data",)),
        _mapping_at(event, ("triggerContext",)),
        event,
    ):
        context.update(source)

    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    event_names = [
        _first_text(context, (key,))
        for key in ("trigger", "action", "type", "webhookType", "webhook_type")
    ]
    normalized_names = {_normalize_text(name) for name in event_names if name}

    if any("statuschanged" in name or "statuschange" in name for name in normalized_names):
        return True

    if any(name in {"update", "updated", "issueupdated", "updatedissue"} for name in normalized_names):
        return _updated_fields_include_status(context)

    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    fields = context.get("updatedFields") or context.get("updated_fields")
    if isinstance(fields, str):
        candidates = [fields]
    elif isinstance(fields, Mapping):
        candidates = list(fields.keys())
    elif isinstance(fields, list | tuple | set):
        candidates = list(fields)
    else:
        candidates = []

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        candidates.extend(changes.keys())

    return any(_normalize_field_name(field) in STATUS_CHANGE_FIELDS for field in candidates)


def _first_text(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = context.get(key)
        text = _text_value(value)
        if text:
            return text
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "id", "identifier", "key"):
            nested = value.get(key)
            if isinstance(nested, str):
                return nested
    return None


def _mapping_at(value: Mapping[str, Any], path: tuple[str, ...]) -> dict[str, Any]:
    current: Any = value
    for key in path:
        if not isinstance(current, Mapping):
            return {}
        current = current.get(key)
    return dict(current) if isinstance(current, Mapping) else {}


def _normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", value)
    return re.sub(r"[^a-z0-9]+", "", spaced.lower())


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def main() -> int:
    """Read a JSON payload from stdin and print the title update action, if any."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
