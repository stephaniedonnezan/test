"""Build Linear issue-title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
_TRIGGER_FIELDS = {"trigger", "webhooktype", "webhook_type", "action", "type"}
_WRAPPER_KEYS = ("issue", "data", "triggerContext", "trigger_context")
_OUTER_METADATA_KEYS = {
    "action",
    "newStatus",
    "new_status",
    "statusName",
    "status_name",
    "trigger",
    "type",
    "updatedFields",
    "updated_fields",
    "webhookType",
    "webhook_type",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research.

    The automation trigger may pass a flat `triggerContext` payload, while Linear
    webhooks commonly wrap issue data under `data` or `issue`. This function
    accepts both shapes and returns a serializable action for the caller to apply.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _merged_payload(event)
    if not _is_status_change_event(payload):
        return None

    new_status = _new_status(payload)
    if _normalize_status(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, ("issueId", "issue_id", "id", "identifier"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _merged_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common automation and Linear webhook wrappers.

    Nested issue data keeps precedence for issue fields such as `id` and `title`;
    top-level webhook metadata can still refine the trigger/status context.
    """

    payload: dict[str, Any] = {}

    for wrapper_key in _WRAPPER_KEYS:
        nested = event.get(wrapper_key)
        if isinstance(nested, Mapping):
            payload.update(_merged_payload(nested))

    for key, value in event.items():
        if key in _WRAPPER_KEYS:
            continue
        if key not in payload or key in _OUTER_METADATA_KEYS:
            payload[key] = value

    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        str(value)
        for key, value in payload.items()
        if _normalize_key(key) in _TRIGGER_FIELDS and isinstance(value, str)
    ]

    if any(_normalize_token(value) in {"statuschanged", "statuschange"} for value in trigger_values):
        return True
    updated_fields = payload.get("updatedFields") or payload.get("updated_fields")
    if _contains_status_field(updated_fields):
        return True

    return False


def _new_status(payload: Mapping[str, Any]) -> Any:
    for key in ("newStatus", "new_status", "statusName", "status_name"):
        value = payload.get(key)
        if value is not None:
            return _name_or_text(value)

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = payload.get(key)
        if value is not None:
            return _name_or_text(value)

    return None


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_key(value) in _STATUS_FIELDS
    if isinstance(value, Mapping):
        return any(_normalize_key(key) in _STATUS_FIELDS for key in value)
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _name_or_text(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if nested is not None:
                return nested
    return value


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return " ".join(part.lower() for part in _split_words(value))


def _normalize_token(value: str) -> str:
    return "".join(_split_words(value)).lower()


def _normalize_key(value: Any) -> str:
    return str(value).replace("-", "_").lower()


def _split_words(value: str) -> list[str]:
    spaced = _CAMEL_BOUNDARY_RE.sub(" ", value)
    return [part for part in re.split(r"[\s_-]+", spaced.strip()) if part]


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
