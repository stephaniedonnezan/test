"""Build Linear issue title updates for Cursor research automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"

_STATUS_FIELDS = {
    "newstatus",
    "new_status",
    "status",
    "state",
    "workflowstate",
    "workflow_state",
}
_STATUS_UPDATE_FIELDS = {
    "status",
    "state",
    "workflowstate",
    "workflow_state",
}
_TRIGGER_FIELDS = {"trigger", "webhooktype", "webhook_type", "action", "type"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action when an issue enters research."""

    if not isinstance(event, Mapping):
        return None

    payload = _merge_payload(event)
    if not _is_status_changed_event(payload):
        return None

    status = _extract_new_status(payload)
    if _normalize_text(status) != _normalize_text(RESEARCH_STATUS):
        return None

    issue_id = _extract_issue_id(payload)
    title = _extract_title(payload)
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        new_title = title
    else:
        new_title = f"{RESEARCH_PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": new_title,
    }


def _merge_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common automation and Linear webhook wrappers into one payload."""

    payload: dict[str, Any] = {}
    for key in ("issue", "data", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            payload.update(_merge_payload(value))
    payload.update(event)
    return payload


def _is_status_changed_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        value
        for key, value in _walk_items(payload)
        if _normalize_key(key) in _TRIGGER_FIELDS and isinstance(value, str)
    ]

    if any(_normalize_text(value) in {"statuschanged", "statuschange", "statuschanged"} for value in trigger_values):
        return True
    if any(_normalize_text(value) == "statuschanged" for value in trigger_values):
        return True
    if any(_normalize_text(value) in {"issueupdated", "updatedissue", "update", "updated"} for value in trigger_values):
        return _updated_fields_include_status(payload)

    return False


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    fields = (
        payload.get("updatedFields")
        or payload.get("updated_fields")
        or payload.get("changedFields")
        or payload.get("changed_fields")
    )

    if isinstance(fields, str):
        candidates: Iterable[Any] = re.split(r"[\s,]+", fields)
    elif isinstance(fields, Iterable) and not isinstance(fields, (Mapping, bytes, bytearray)):
        candidates = fields
    else:
        return False

    return any(_normalize_key(str(field)) in _STATUS_UPDATE_FIELDS for field in candidates)


def _extract_new_status(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status"):
        value = payload.get(key)
        status = _status_name(value)
        if status:
            return status

    for key, value in _walk_items(payload):
        if _normalize_key(key) in _STATUS_FIELDS:
            status = _status_name(value)
            if status:
                return status

    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "status"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()
    return None


def _extract_issue_id(payload: Mapping[str, Any]) -> str | None:
    for key in ("id", "issueId", "issue_id", "identifier"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_title(payload: Mapping[str, Any]) -> str | None:
    value = payload.get("title")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(RESEARCH_PREFIX.lower())


def _walk_items(value: Any) -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str):
                yield key, item
            yield from _walk_items(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_items(item)


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", _split_camel_case(value).lower())


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"[^a-z0-9]", "", _split_camel_case(value).lower())


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
