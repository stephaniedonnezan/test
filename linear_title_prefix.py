"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title update action when an issue enters research."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change(payload):
        return None

    new_status = _extract_status(payload)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(payload, ("id", "issueId", "issue_id", "identifier"))
    title = _extract_first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    if title.lower().startswith(TITLE_PREFIX.lower()):
        updated_title = title
    else:
        updated_title = f"{TITLE_PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": updated_title,
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common automation and Linear webhook containers into one view."""
    flattened: dict[str, Any] = {}

    # Apply broad issue-like objects first, then overlay trigger metadata so the
    # current status-change event is not masked by stale nested issue fields.
    for container_key in ("issue", "data", "triggerContext"):
        container = event.get(container_key)
        if isinstance(container, Mapping):
            nested_issue = container.get("issue")
            if isinstance(nested_issue, Mapping):
                _merge_missing(flattened, nested_issue)
            _merge_missing(flattened, container)

    _merge_missing(flattened, event)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        _merge_missing(flattened, issue)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            _merge_missing(flattened, issue)

    return flattened


def _merge_missing(target: dict[str, Any], source: Mapping[str, Any]) -> None:
    for key, value in source.items():
        if key not in target and value not in (None, ""):
            target[key] = value


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        value
        for key in ("trigger", "action", "type", "webhookType")
        if (value := payload.get(key)) is not None
    ]

    for value in trigger_values:
        normalized = _normalize_token(value)
        if normalized in {"statuschanged", "statuschange", "statusupdated"}:
            return True
        if normalized in {"issueupdated", "updatedissue", "update"}:
            return _updated_fields_include_status(payload)

    return False


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = payload.get(key)
        if fields is None:
            continue
        if isinstance(fields, str):
            values: Iterable[Any] = re.split(r"[, ]+", fields)
        elif isinstance(fields, Mapping):
            values = fields.keys()
        elif isinstance(fields, Iterable):
            values = fields
        else:
            continue

        for field in values:
            if _normalize_token(field) in STATUS_FIELDS:
                return True
    return False


def _extract_status(payload: Mapping[str, Any]) -> str | None:
    direct_status = _extract_first_text(
        payload,
        ("newStatus", "new_status", "newState", "new_state", "statusName", "status_name"),
    )
    if direct_status:
        return direct_status

    for key in ("state", "workflowState", "workflow_state", "status"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            name = _extract_first_text(value, ("name", "title", "status"))
            if name:
                return name
        elif isinstance(value, str) and value.strip():
            return value.strip()

    return None


def _extract_first_text(payload: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            value = value.strip()
            if value:
                return value
    return None


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()


def _normalize_token(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", _normalize_text(value))


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
