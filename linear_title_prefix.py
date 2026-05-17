"""Build Linear issue title updates for research status transitions."""

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
    """Return a title update action when a Linear issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    flattened = _flatten_payload(event)
    if not _is_status_change_event(flattened):
        return None

    status = _new_status(flattened)
    if _normalize_status(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(flattened, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(flattened, ("title", "name"))
    if not issue_id or not title:
        return None

    cleaned_title = title.strip()
    if _has_prefix(cleaned_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {cleaned_title}",
    }


def _flatten_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Linear webhook nesting while keeping outer trigger metadata."""
    flattened: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if not isinstance(value, Mapping):
            return

        for nested_key in ("issue", "data", "triggerContext"):
            nested_value = value.get(nested_key)
            if isinstance(nested_value, Mapping):
                merge(nested_value)

        for key, item in value.items():
            if key not in {"issue", "data", "triggerContext"}:
                flattened[key] = item

    merge(payload)
    return flattened


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_names = [
        _normalize_event(value)
        for key in ("trigger", "webhookType", "action", "type")
        if (value := payload.get(key)) is not None
    ]

    if any(name in {"statuschanged", "statuschange"} for name in event_names):
        return True

    updated_fields = payload.get("updatedFields") or payload.get("updated_fields")
    if _has_status_field(updated_fields) and any(
        name in {"update", "issueupdate", "updatedissue", "issueupdated"}
        for name in event_names
    ):
        return True

    return False


def _new_status(payload: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    ):
        value = payload.get(key)
        if isinstance(value, str):
            return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, Mapping):
            nested_name = value.get("name")
            if isinstance(nested_name, str):
                return nested_name

    return None


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_status_field(updated_fields: Any) -> bool:
    if isinstance(updated_fields, str):
        fields = re.split(r"[\s,]+", updated_fields)
    elif isinstance(updated_fields, Mapping):
        fields = updated_fields.keys()
    elif isinstance(updated_fields, list | tuple | set):
        fields = updated_fields
    else:
        return False

    return any(_normalize_field(field) in STATUS_FIELDS for field in fields)


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"[\s_-]+", " ", _split_camel(value)).strip().casefold()


def _normalize_event(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]", "", _split_camel(value).casefold())


def _normalize_field(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9_]", "", value.casefold())


def _split_camel(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
