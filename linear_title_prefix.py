"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to "to research"."""
    if not isinstance(event, Mapping):
        return None

    sources = _payload_sources(event)
    if not _is_status_change_event(sources):
        return None

    new_status = _extract_new_status(sources)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(sources, ("issueId", "issue_id", "id", "identifier"))
    title = _first_text(sources, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _payload_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []

    trigger_context = _mapping_value(event, "triggerContext")
    data = _mapping_value(event, "data")
    issue = _mapping_value(event, "issue")
    data_issue = _mapping_value(data, "issue") if data else None

    for source in (trigger_context, issue, data_issue, data, event):
        if source is not None and source not in sources:
            sources.append(source)

    return sources


def _mapping_value(source: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if not isinstance(source, Mapping):
        return None

    value = source.get(key)
    return value if isinstance(value, Mapping) else None


def _is_status_change_event(sources: Sequence[Mapping[str, Any]]) -> bool:
    event_values = _event_descriptor_values(sources)
    if any(_is_direct_status_change(value) for value in event_values):
        return True

    if any(_is_issue_update(value) for value in event_values):
        return _updated_status_fields(sources)

    return False


def _event_descriptor_values(sources: Sequence[Mapping[str, Any]]) -> list[Any]:
    values: list[Any] = []
    for source in sources:
        for key in ("trigger", "event", "eventType", "event_type", "type", "action", "webhookType"):
            if key in source:
                values.append(source[key])
    return values


def _is_direct_status_change(value: Any) -> bool:
    normalized = _normalize_words(value)
    return normalized in {"status changed", "status change"} or (
        "status" in normalized and ("changed" in normalized or "change" in normalized)
    )


def _is_issue_update(value: Any) -> bool:
    normalized = _normalize_words(value)
    return normalized in {"update", "updated", "issue update", "issue updated", "updated issue"}


def _updated_status_fields(sources: Sequence[Mapping[str, Any]]) -> bool:
    for source in sources:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields", "changes"):
            if key in source:
                for field in _iter_field_names(source[key]):
                    normalized = _normalize_words(field)
                    if normalized in STATUS_FIELD_NAMES:
                        return True
    return False


def _iter_field_names(value: Any) -> list[Any]:
    if isinstance(value, str):
        return [value]

    if isinstance(value, Mapping):
        fields: list[Any] = list(value.keys())
        for nested_key in ("name", "field", "key"):
            if nested_key in value:
                fields.append(value[nested_key])
        return fields

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        fields = []
        for item in value:
            fields.extend(_iter_field_names(item))
        return fields

    return []


def _extract_new_status(sources: Sequence[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "newState",
        "new_state",
        "toState",
        "to_state",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    for keys in (explicit_keys, fallback_keys):
        for source in sources:
            for key in keys:
                if key in source:
                    status = _text_or_name(source[key])
                    if status:
                        return status

    return None


def _first_text(sources: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for source in sources:
        for key in keys:
            if key in source:
                value = _text_or_name(source[key])
                if value and value.strip():
                    return value
    return None


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if isinstance(value, Mapping):
        for key in ("name", "title", "id", "identifier"):
            nested = value.get(key)
            if isinstance(nested, str):
                return nested

    return None


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    result = build_issue_title_update(json.load(sys.stdin))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
