"""Build Linear issue title update actions for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow status", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to "to research"."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)

    if not _is_status_change(payload):
        return None

    status = _extract_new_status(payload)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    if title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common nested Linear/automation payload shapes into one lookup map."""
    payload: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if isinstance(value, Mapping):
            payload.update(value)

    issue = _mapping_at(event, "issue")
    data = _mapping_at(event, "data")
    trigger_context = _mapping_at(event, "triggerContext")

    if data:
        merge(_mapping_at(data, "issue"))
    merge(issue)
    merge(data)
    merge(trigger_context)
    merge(event)

    state = _mapping_at(event, "state") or _mapping_at(data, "state") or _mapping_at(issue, "state")
    workflow_state = (
        _mapping_at(event, "workflowState")
        or _mapping_at(data, "workflowState")
        or _mapping_at(issue, "workflowState")
    )

    if state:
        payload.setdefault("state", state)
        payload.setdefault("stateName", _first_text(state, ("name", "title")))
    if workflow_state:
        payload.setdefault("workflowState", workflow_state)
        payload.setdefault("workflowStateName", _first_text(workflow_state, ("name", "title")))

    return payload


def _mapping_at(source: Any, key: str) -> Mapping[str, Any] | None:
    if isinstance(source, Mapping) and isinstance(source.get(key), Mapping):
        return source[key]
    return None


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger_values = list(_trigger_values(payload))
    if any(_is_direct_status_change(value) for value in trigger_values):
        return True

    if any(_normalize_text(value) in {"issue updated", "updated issue", "update", "updated"} for value in trigger_values):
        return _updated_fields_include_status(payload.get("updatedFields") or payload.get("updated_fields"))

    return False


def _trigger_values(payload: Mapping[str, Any]) -> Iterable[Any]:
    for key in ("trigger", "webhookType", "action", "type"):
        value = payload.get(key)
        if value is not None:
            yield value


def _is_direct_status_change(value: Any) -> bool:
    normalized = _normalize_text(value)
    compact = normalized.replace(" ", "")
    return normalized in {"status changed", "status change"} or compact in {"statuschanged", "statuschange"}


def _updated_fields_include_status(updated_fields: Any) -> bool:
    if isinstance(updated_fields, str):
        fields = re.split(r"[, ]+", updated_fields)
    elif isinstance(updated_fields, Iterable):
        fields = updated_fields
    else:
        return False

    for field in fields:
        if isinstance(field, Mapping):
            value = field.get("name") or field.get("field") or field.get("key")
        else:
            value = field
        if _normalize_text(value) in STATUS_FIELDS:
            return True
    return False


def _extract_new_status(payload: Mapping[str, Any]) -> str | None:
    direct_status = _first_text(
        payload,
        (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "statusName",
            "stateName",
            "workflowStateName",
        ),
    )
    if direct_status:
        return direct_status

    for key in ("status", "state", "workflowState"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            nested = _first_text(value, ("name", "title"))
            if nested:
                return nested
        elif isinstance(value, str):
            return value.strip()

    return None


def _first_text(source: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = source.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
        elif isinstance(value, int):
            return str(value)
    return None


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[_\-/]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", normalized)


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    if result is not None:
        json.dump(result, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
