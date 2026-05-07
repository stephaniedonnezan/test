"""Build title update actions for Linear issues moved to research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to "to research"."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    if not _is_status_change(payload):
        return None

    new_status = _first_string(
        payload,
        "newStatus",
        "new_status",
        "status",
        "statusName",
        "stateName",
    )
    if new_status is None:
        state = payload.get("state")
        if isinstance(state, Mapping):
            new_status = _first_string(state, "name")

    if _normalize_token(new_status) != _normalize_token(TARGET_STATUS):
        return None

    issue_id = _first_string(payload, "id", "issueId", "issue_id", "identifier")
    title = _first_string(payload, "title")
    if issue_id is None or title is None:
        return None

    clean_title = title.strip()
    if not clean_title or _has_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Linear webhook envelopes into one lookup dictionary."""
    payload: dict[str, Any] = {}

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        payload.update(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        payload.update(data)
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            payload.update(issue)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        payload.update(issue)

    # Top-level automation metadata should win over nested issue fields.
    payload.update(event)
    return payload


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger = _first_string(payload, "trigger", "webhookType", "action", "type")
    if trigger is not None and _normalize_token(trigger) in {
        "status changed",
        "statuschanged",
        "issue status changed",
        "state changed",
        "statechanged",
    }:
        return True

    updated_fields = payload.get("updatedFields") or payload.get("updated_fields")
    if isinstance(updated_fields, str):
        updated_fields = [updated_fields]
    if isinstance(updated_fields, list):
        return any(_normalize_token(field) in {"status", "state"} for field in updated_fields)

    return False


def _first_string(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return None


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"[\W_]+", " ", value, flags=re.ASCII)
    return " ".join(value.casefold().split())


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def main() -> int:
    """Read a JSON event from stdin and print the action as JSON when applicable."""
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
