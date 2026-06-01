"""Build Linear issue-title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
DIRECT_STATUS_EVENT_NAMES = {"statuschanged", "statuschange", "statusupdated", "statusupdate"}
UPDATED_ISSUE_EVENT_NAMES = {"issueupdated", "updatedissue", "update", "updated"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to to-research."""

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)

    if not _is_status_change_event(payload):
        return None

    if _normalize_words(_extract_new_status(payload)) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Linear webhook nesting levels into one lookup dictionary."""

    flattened: dict[str, Any] = {}
    for path in (
        ("issue",),
        ("data", "issue"),
        ("triggerContext", "issue"),
        ("triggerContext", "data", "issue"),
        ("data",),
        ("triggerContext", "data"),
        ("triggerContext",),
        (),
    ):
        value = _get_path(event, path)
        if isinstance(value, Mapping):
            flattened.update(value)
    return flattened


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_names = {
        _normalize_token(value)
        for key in ("trigger", "webhookType", "action", "type")
        if (value := payload.get(key)) is not None
    }

    if event_names & DIRECT_STATUS_EVENT_NAMES:
        return True

    if event_names & UPDATED_ISSUE_EVENT_NAMES:
        return _updated_fields_include_status(payload)

    return False


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if key not in payload:
            continue

        fields = payload[key]
        if isinstance(fields, str):
            candidates = [fields]
        elif isinstance(fields, Mapping):
            candidates = fields.keys()
        elif isinstance(fields, list | tuple | set):
            candidates = fields
        else:
            continue

        for field in candidates:
            if _normalize_field_name(field) in STATUS_FIELDS:
                return True

    return False


def _extract_new_status(payload: Mapping[str, Any]) -> Any:
    for key in (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "statusName",
        "status_name",
    ):
        if key in payload:
            return payload[key]

    for key in ("state", "workflowState", "workflow_state", "status"):
        value = payload.get(key)
        if isinstance(value, Mapping) and "name" in value:
            return value["name"]
        if value is not None:
            return value

    return None


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            value = value.strip()
            if value:
                return value
    return None


def _get_path(value: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = value
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _normalize_words(value: Any) -> str:
    if isinstance(value, Mapping):
        value = value.get("name")
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", " ", _split_camel_case(value).lower()).strip()


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", _split_camel_case(value).lower())


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", _split_camel_case(value).lower())


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
