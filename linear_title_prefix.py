"""Build Linear issue title updates for Cursor research automations.

The automation runtime can pass either the flat Cursor ``triggerContext`` object
or a nested Linear webhook payload. This module keeps the decision pure so the
caller can perform the actual Linear mutation.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
TITLE_SEPARATOR = ": "

STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflowstatus",
}

STATUS_VALUE_KEYS = (
    "newStatus",
    "new_status",
    "status",
    "state",
    "workflowState",
    "workflow_status",
)

TRIGGER_KEYS = (
    "trigger",
    "webhookType",
    "webhook_type",
    "action",
    "type",
    "event",
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research.

    The returned action is intentionally small and serializable:
    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``.
    ``None`` means the payload should be ignored.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)

    if not _is_status_change_event(payload):
        return None

    if _normalize_status(_extract_status(payload)) != RESEARCH_STATUS:
        return None

    issue_id = _clean_string(_first_value(payload, ("issueId", "issue_id", "id", "identifier", "key")))
    title = _clean_string(_first_value(payload, ("title", "name")))
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        updated_title = title
    else:
        updated_title = f"{PREFIX}{TITLE_SEPARATOR}{title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": updated_title,
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge likely metadata and issue objects into one lookup dictionary."""

    flattened: dict[str, Any] = {}
    for path in (
        ("data", "issue"),
        ("issue",),
        ("triggerContext", "data", "issue"),
        ("triggerContext", "issue"),
        ("triggerContext",),
        ("data",),
        (),
    ):
        node = _get_path(event, path)
        if isinstance(node, Mapping):
            flattened.update(node)

    return flattened


def _get_path(event: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    node: Any = event
    for key in path:
        if not isinstance(node, Mapping):
            return None
        node = node.get(key)
    return node


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize_token(value)
        for key in TRIGGER_KEYS
        for value in _as_values(payload.get(key))
    ]

    if any(value in {"statuschanged", "statechanged", "workflowstatechanged"} for value in trigger_values):
        return True

    if any(value in {"issueupdated", "updatedissue", "update", "updated"} for value in trigger_values):
        return _status_field_changed(payload)

    return False


def _status_field_changed(payload: Mapping[str, Any]) -> bool:
    changed_fields = []
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        changed_fields.extend(_as_values(payload.get(key)))

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        changed_fields.extend(changes.keys())
    elif isinstance(changes, Sequence) and not isinstance(changes, (str, bytes)):
        for change in changes:
            if isinstance(change, Mapping):
                changed_fields.extend(
                    _as_values(
                        _first_value(
                            change,
                            ("field", "fieldName", "field_name", "name", "key", "property"),
                        )
                    )
                )
            else:
                changed_fields.append(change)

    return any(_normalize_field_name(field) in STATUS_FIELD_NAMES for field in changed_fields)


def _extract_status(payload: Mapping[str, Any]) -> Any:
    for key in ("newStatus", "new_status"):
        value = payload.get(key)
        status = _status_name(value)
        if status:
            return status

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _normalize_field_name(key) in STATUS_FIELD_NAMES:
                return _status_name(_first_value(value, ("to", "new", "newValue", "new_value", "after"))) or value

    for key in ("status", "state", "workflowState", "workflow_status"):
        value = payload.get(key)
        status = _status_name(value)
        if status:
            return status

    return None


def _status_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _first_value(value, ("name", "title", "label", "value"))
    return value


def _first_value(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            return value
    return None


def _as_values(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return list(value)
    return [value]


def _clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    cleaned = value.strip()
    return cleaned or None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_status(value: Any) -> str | None:
    text = _clean_string(value)
    if not text:
        return None

    return re.sub(r"[_\-\s]+", " ", _split_camel_case(text)).strip().casefold()


def _normalize_token(value: Any) -> str:
    text = _clean_string(value)
    if not text:
        return ""

    return re.sub(r"[^a-z0-9]", "", _split_camel_case(text).casefold())


def _normalize_field_name(value: Any) -> str:
    text = _clean_string(value)
    if not text:
        return ""

    return re.sub(r"[^a-z0-9]", "", _split_camel_case(text).casefold())


def _split_camel_case(text: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)


def main() -> int:
    """Read JSON from stdin and print the computed action, if any."""

    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
