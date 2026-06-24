"""Build Linear issue title updates for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change(payload):
        return None

    if _normalize_label(_extract_status(payload)) != RESEARCH_STATUS:
        return None

    issue_id = _clean_text(_first_value(payload, ("id", "issueId", "issue_id", "identifier")))
    title = _clean_text(_first_value(payload, ("title", "name")))
    if not issue_id or not title:
        return None

    if title.casefold().startswith(TITLE_PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor automation and Linear webhook nesting into one payload."""

    payload: dict[str, Any] = {}
    for key in ("triggerContext", "data", "issue"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            payload.update(_flatten_payload(nested))

    payload.update(event)
    return payload


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize_label(value)
        for key in ("trigger", "webhookType", "action", "type")
        if (value := payload.get(key)) is not None
    ]
    if any(value in {"status changed", "status change"} for value in trigger_values):
        return True

    if any(value in {"update", "updated", "issue updated", "updated issue"} for value in trigger_values):
        return _updated_fields_include_status(payload.get("updatedFields"))

    return False


def _updated_fields_include_status(updated_fields: Any) -> bool:
    if updated_fields is None:
        return False

    if isinstance(updated_fields, str):
        fields = [updated_fields]
    elif isinstance(updated_fields, Mapping):
        fields = updated_fields.keys()
    elif isinstance(updated_fields, Sequence) and not isinstance(updated_fields, (str, bytes, bytearray)):
        fields = updated_fields
    else:
        return False

    for field in fields:
        normalized = _normalize_label(field)
        compact = normalized.replace(" ", "")
        if normalized in STATUS_FIELDS or compact in STATUS_FIELDS:
            return True

    return False


def _extract_status(payload: Mapping[str, Any]) -> Any:
    for key in ("newStatus", "new_status", "status"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            value = value.get("name")
        if value is not None:
            return value

    for key in ("state", "workflowState"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            value = value.get("name")
        if value is not None:
            return value

    return None


def _first_value(payload: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _normalize_label(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.casefold()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is None:
        return 1

    json.dump(update, sys.stdout, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
