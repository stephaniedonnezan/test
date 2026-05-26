"""Build Linear issue title updates for issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow status"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    if not _is_status_change_event(payload):
        return None

    status = _first_string(
        payload,
        (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "status",
            "state.name",
            "workflowState.name",
            "workflow_status.name",
        ),
    )
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_string(
        payload,
        ("issue.id", "issueId", "issue_id", "identifier", "id"),
    )
    title = _first_string(payload, ("issue.title", "title"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor and Linear nesting layers without losing outer metadata."""

    payload: dict[str, Any] = {}
    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            payload.update(_flatten_event(value))

    payload.update(event)
    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_words = [
        _normalize(value)
        for key in ("trigger", "webhookType", "action", "type")
        if (value := payload.get(key)) is not None
    ]

    if any(word in {"status changed", "status change", "statuschanged"} for word in event_words):
        return True

    if any(word in {"issue updated", "updated issue", "update", "updated"} for word in event_words):
        return _updated_status_fields(payload.get("updatedFields")) or _updated_status_fields(
            payload.get("updated_fields")
        )

    return False


def _updated_status_fields(value: Any) -> bool:
    if isinstance(value, str):
        values: Sequence[Any] = [value]
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        values = value
    elif isinstance(value, Mapping):
        values = value.keys()
    else:
        return False

    return any(_normalize(str(field)) in STATUS_FIELDS for field in values)


def _first_string(payload: Mapping[str, Any], paths: Sequence[str]) -> str | None:
    for path in paths:
        value = _get_path(payload, path)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _get_path(payload: Mapping[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    with_spaces = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[\W_]+", " ", with_spaces).strip().casefold()


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
