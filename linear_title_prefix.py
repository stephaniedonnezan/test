"""Build Linear issue-title updates for issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"
STATUS_FIELDS = frozenset(("status", "state", "workflow_state", "workflowstate"))


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research.

    The automation trigger payload is intentionally normalized here because
    Linear/Cursor webhook shapes differ between direct and nested deliveries.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change(payload):
        return None

    status = _extract_new_status(payload)
    if _normalize_text(status) != RESEARCH_STATUS:
        return None

    issue_id = _clean_string(_first_present(payload, ("id", "issueId", "issue_id", "identifier")))
    title = _clean_string(_first_present(payload, ("title", "name")))
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge known nested payload containers into one lookup dictionary."""

    flattened: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if not isinstance(value, Mapping):
            return

        for key in ("triggerContext", "webhook", "data", "issue"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                merge(nested)

        flattened.update(value)

    merge(event)
    return flattened


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        payload.get(key)
        for key in ("trigger", "webhookType", "action", "type", "eventType")
        if key in payload
    ]
    normalized_triggers = {_normalize_text(value) for value in trigger_values}

    if any(value in {"status changed", "status change", "status updated"} for value in normalized_triggers):
        return True

    if any(value in {"issue updated", "updated issue", "update", "updated"} for value in normalized_triggers):
        return _updated_fields_include_status(payload)

    return False


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    fields = _first_present(
        payload,
        (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
            "changedProperties",
            "changed_properties",
        ),
    )

    if isinstance(fields, str):
        candidates: Sequence[Any] = re.split(r"[\s,]+", fields)
    elif isinstance(fields, Mapping):
        candidates = tuple(fields.keys())
    elif isinstance(fields, Sequence) and not isinstance(fields, (bytes, bytearray)):
        candidates = fields
    else:
        return False

    return any(_normalize_key(field) in STATUS_FIELDS for field in candidates)


def _extract_new_status(payload: Mapping[str, Any]) -> Any:
    explicit_status = _first_present(
        payload,
        (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "statusName",
            "status_name",
            "newState",
            "new_state",
        ),
    )
    if explicit_status is not None:
        return explicit_status

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            named_value = _first_present(value, ("name", "title", "label"))
            if named_value is not None:
                return named_value
        elif value is not None:
            return value

    return None


def _first_present(payload: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    cleaned = value.strip()
    return cleaned or None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()
    return re.sub(r"\s+", " ", normalized)


def _normalize_key(value: Any) -> str | None:
    normalized = _normalize_text(value)
    if normalized is None:
        return None
    return normalized.replace(" ", "_")


def main() -> int:
    """Read a JSON event from stdin and print the title-update action."""

    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
