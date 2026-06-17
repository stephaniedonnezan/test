"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate"}
_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type")
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title update when an issue enters to research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(event, contexts):
        return None

    if _normalize_label(_changed_status(event, contexts)) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(contexts, ("title",))
    if not issue_id or not title:
        return None

    if title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload mappings from most useful to least useful."""

    trigger_context = _mapping_value(event, "triggerContext")
    data = _mapping_value(event, "data")
    issue = _mapping_value(event, "issue")
    data_issue = _mapping_value(data, "issue") if data else None

    ordered = [trigger_context, data_issue, issue, data, event]
    return [context for context in ordered if context is not None]


def _mapping_value(mapping: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if not mapping:
        return None
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else None


def _is_status_change_event(
    event: Mapping[str, Any], contexts: Iterable[Mapping[str, Any]]
) -> bool:
    for context in contexts:
        for key in _TRIGGER_KEYS:
            label = _normalize_label(context.get(key))
            if label in {"status changed", "state changed", "workflow state changed"}:
                return True
            if label in {"issue updated", "updated issue", "update", "updated"}:
                return _has_changed_status_field(event)

    return False


def _has_changed_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            field_name = _normalize_field_name(key)
            if key in {"updatedFields", "changedFields"}:
                if _changed_field_collection_has_status(item):
                    return True
            elif field_name in _STATUS_FIELD_NAMES and _looks_like_change_metadata(item):
                return True
            elif _has_changed_status_field(item):
                return True
    elif isinstance(value, list):
        return any(_has_changed_status_field(item) for item in value)

    return False


def _changed_field_collection_has_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in _STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        name = _first_text((value,), ("field", "fieldName", "name", "key"))
        return _normalize_field_name(name) in _STATUS_FIELD_NAMES
    if isinstance(value, list):
        return any(_changed_field_collection_has_status(item) for item in value)
    return False


def _looks_like_change_metadata(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    return any(key in value for key in ("to", "new", "after", "newValue", "toValue"))


def _changed_status(event: Mapping[str, Any], contexts: Iterable[Mapping[str, Any]]) -> Any:
    for context in contexts:
        for key in _EXPLICIT_STATUS_KEYS:
            value = _status_name(context.get(key))
            if value:
                return value

    changed_value = _changed_status_from_metadata(event)
    if changed_value:
        return changed_value

    for context in contexts:
        for key in _STATUS_KEYS:
            value = _status_name(context.get(key))
            if value:
                return value

    return None


def _changed_status_from_metadata(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _normalize_field_name(key) in _STATUS_FIELD_NAMES and isinstance(item, Mapping):
                for to_key in ("to", "new", "after", "newValue", "toValue"):
                    status = _status_name(item.get(to_key))
                    if status:
                        return status
            status = _changed_status_from_metadata(item)
            if status:
                return status
    elif isinstance(value, list):
        for item in value:
            status = _changed_status_from_metadata(item)
            if status:
                return status

    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, Mapping):
        return _first_text((value,), ("name", "title", "label", "value"))
    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str):
                text = value.strip()
                if text:
                    return text
            elif isinstance(value, int):
                return str(value)
    return None


def _normalize_label(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^a-zA-Z0-9]+", " ", spaced).lower().strip()
    return re.sub(r"\s+", " ", words)


def _normalize_field_name(value: Any) -> str:
    return _normalize_label(value).replace(" ", "")


def main() -> int:
    payload = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(payload)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
