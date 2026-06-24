"""Build Linear issue title updates for Cursor research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    mappings = list(_event_mappings(event))
    if not _is_status_change_event(mappings):
        return None

    new_status = _extract_new_status(mappings)
    if _normalize_status(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(mappings)
    title = _extract_title(mappings)
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _event_mappings(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield payload sections that commonly hold Linear webhook fields."""
    yield event

    trigger_context = _as_mapping(event.get("triggerContext"))
    if trigger_context:
        yield trigger_context

    data = _as_mapping(event.get("data"))
    if data:
        yield data
        issue = _as_mapping(data.get("issue"))
        if issue:
            yield issue

    issue = _as_mapping(event.get("issue"))
    if issue:
        yield issue


def _is_status_change_event(mappings: Iterable[Mapping[str, Any]]) -> bool:
    mapping_list = list(mappings)

    for payload in mapping_list:
        for key in ("trigger", "event", "action", "type"):
            if _is_direct_status_change(payload.get(key)):
                return True

    has_update_event = False
    has_status_field_change = False
    for payload in mapping_list:
        for key in ("trigger", "event", "action", "type"):
            normalized = _normalize_words(payload.get(key))
            if "update" in normalized.split() or "updated" in normalized.split():
                has_update_event = True

        if _updated_fields_include_status(payload):
            has_status_field_change = True

    return has_update_event and has_status_field_change


def _is_direct_status_change(value: Any) -> bool:
    normalized = _normalize_words(value)
    return "status changed" in normalized or "state changed" in normalized


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = payload.get(key)
        if isinstance(fields, str):
            fields = [fields]
        if isinstance(fields, Iterable) and not isinstance(fields, (bytes, str, Mapping)):
            for field in fields:
                if _normalize_field_name(field) in STATUS_FIELD_NAMES:
                    return True

    for key in ("changes", "changed", "updatedFrom", "updated_from"):
        changes = _as_mapping(payload.get(key))
        if not changes:
            continue
        if any(_normalize_field_name(field) in STATUS_FIELD_NAMES for field in changes):
            return True

    return False


def _extract_new_status(mappings: Iterable[Mapping[str, Any]]) -> str | None:
    mapping_list = list(mappings)
    explicit_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "statusName",
        "status_name",
    )

    for payload in mapping_list:
        value = _first_text(payload, explicit_keys)
        if value:
            return value

    for payload in mapping_list:
        value = _extract_changed_status(payload)
        if value:
            return value

    for payload in mapping_list:
        value = _status_from_payload(payload)
        if value:
            return value

    return None


def _extract_changed_status(payload: Mapping[str, Any]) -> str | None:
    changes = _as_mapping(payload.get("changes")) or _as_mapping(payload.get("changed"))
    if not changes:
        return None

    for field, change in changes.items():
        if _normalize_field_name(field) not in STATUS_FIELD_NAMES:
            continue
        if isinstance(change, str):
            return change.strip() or None
        change_mapping = _as_mapping(change)
        if not change_mapping:
            continue
        value = _first_text(change_mapping, ("newValue", "new_value", "new", "to", "after"))
        if value:
            return value
        for key in ("to", "after", "new"):
            nested = _as_mapping(change_mapping.get(key))
            value = _first_text(nested or {}, ("name", "title"))
            if value:
                return value

    return None


def _status_from_payload(payload: Mapping[str, Any]) -> str | None:
    value = _first_text(payload, ("status",))
    if value:
        return value

    for key in ("state", "workflowState", "workflow_state"):
        state = payload.get(key)
        if isinstance(state, str):
            return state.strip() or None
        state_mapping = _as_mapping(state)
        value = _first_text(state_mapping or {}, ("name", "title"))
        if value:
            return value

    return None


def _extract_issue_id(mappings: Iterable[Mapping[str, Any]]) -> str | None:
    for payload in mappings:
        value = _first_text(payload, ("issueId", "issue_id", "identifier", "key", "id"))
        if value:
            return value
    return None


def _extract_title(mappings: Iterable[Mapping[str, Any]]) -> str | None:
    for payload in mappings:
        value = _first_text(payload, ("title", "name"))
        if value:
            return value
    return None


def _first_text(payload: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _has_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(PREFIX)}\b", title, flags=re.IGNORECASE) is not None


def _normalize_status(value: Any) -> str:
    return _normalize_words(value)


def _normalize_field_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _normalize_words(value))


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value)
    return " ".join(value.casefold().split())


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
