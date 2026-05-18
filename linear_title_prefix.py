"""Build title update actions for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "statusid", "state", "stateid", "workflowstate", "workflowstateid"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    payloads = _payload_candidates(event)
    metadata = _merged_metadata(payloads)

    if not _is_status_change_event(metadata):
        return None

    if _normalize(_status_name(metadata)) != TARGET_STATUS:
        return None

    issue_id = _first_text(metadata, ("issueId", "issue_id", "id", "identifier"))
    title = _first_text(metadata, ("title", "issueTitle", "issue_title"))
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


def _payload_candidates(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        candidates.append(value)
        for key in ("triggerContext", "data", "issue"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                visit(nested)

    visit(event)
    return candidates


def _merged_metadata(payloads: list[Mapping[str, Any]]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for payload in reversed(payloads):
        metadata.update(payload)
        for key in ("state", "workflowState", "status"):
            value = payload.get(key)
            if isinstance(value, Mapping):
                name = value.get("name")
                if isinstance(name, str) and name.strip():
                    metadata[f"{key}Name"] = name
    return metadata


def _is_status_change_event(metadata: Mapping[str, Any]) -> bool:
    event_tokens = [
        metadata.get(key)
        for key in ("trigger", "webhookType", "action", "type")
        if isinstance(metadata.get(key), str)
    ]
    normalized_events = {_normalize(token) for token in event_tokens}

    if any(token in {"status changed", "status change", "state changed"} for token in normalized_events):
        return True

    if any(token in {"issue updated", "updated issue", "update", "updated"} for token in normalized_events):
        return _updated_status_fields(metadata)

    return False


def _updated_status_fields(metadata: Mapping[str, Any]) -> bool:
    updated_fields = metadata.get("updatedFields") or metadata.get("updated_fields")
    if isinstance(updated_fields, str):
        values = [updated_fields]
    elif isinstance(updated_fields, Mapping):
        values = list(updated_fields)
    elif isinstance(updated_fields, list | tuple | set):
        values = list(updated_fields)
    else:
        return False

    return any(_normalize_field_name(value) in STATUS_FIELDS for value in values)


def _status_name(metadata: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "newState", "new_state", "statusName", "stateName", "workflowStateName"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value

    for key in ("status", "state", "workflowState"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, Mapping):
            name = value.get("name")
            if isinstance(name, str) and name.strip():
                return name

    return None


def _first_text(metadata: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[\s_-]+", " ", spaced).strip().lower()


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _normalize(value).replace(" ", "")


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    if action is not None:
        print(json.dumps(action))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
