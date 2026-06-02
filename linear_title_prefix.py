"""Build title update actions for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    merged = _flatten_payload(event)
    if not _is_status_change_event(merged):
        return None

    status = _new_status_name(merged)
    if _normalize_words(status) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(merged, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(merged, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common automation and Linear webhook nesting into one payload."""
    flattened: dict[str, Any] = {}

    for key in ("issue", "data", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            flattened.update(_flatten_payload(value))

    flattened.update(event)
    return flattened


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    indicators = (
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    )
    normalized = {_normalize_token(value) for value in indicators if isinstance(value, str)}

    if "statuschanged" in normalized or "statuschange" in normalized:
        return True

    if normalized & {"issueupdated", "updatedissue", "update", "updated"}:
        return _updated_status_fields(payload)

    return False


def _updated_status_fields(payload: Mapping[str, Any]) -> bool:
    fields = payload.get("updatedFields") or payload.get("updated_fields")
    if isinstance(fields, str):
        field_names = [fields]
    elif isinstance(fields, list | tuple | set):
        field_names = [field for field in fields if isinstance(field, str)]
    else:
        return False

    return any(_normalize_token(field) in STATUS_FIELDS for field in field_names)


def _new_status_name(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "status"):
        value = payload.get(key)
        text = _status_text(value)
        if text:
            return text

    for key in ("state", "workflowState", "workflow_state"):
        value = payload.get(key)
        text = _status_text(value)
        if text:
            return text

    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return _first_text(value, ("name", "title", "status"))
    return None


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_words(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", separated.lower()).strip()


def _normalize_token(value: Any) -> str:
    words = _normalize_words(value)
    return "" if words is None else words.replace(" ", "")


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
