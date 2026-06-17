"""Build Linear issue title updates for research status transitions."""

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
    """Return a Linear title update action when an issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    mappings = list(_iter_relevant_mappings(event))
    if not _is_status_change_event(mappings):
        return None

    new_status = _extract_new_status(mappings)
    if _normalize_label(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(mappings, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(mappings, ("title",))
    if not issue_id or not title:
        return None

    if title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _iter_relevant_mappings(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely payload locations from most specific issue data to outer metadata."""
    direct_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")

    for value in (
        issue,
        _mapping_value(data, "issue"),
        data,
        _mapping_value(direct_context, "issue"),
        direct_context,
        event,
    ):
        if isinstance(value, Mapping):
            yield value


def _mapping_value(value: Any, key: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(key)
    return None


def _is_status_change_event(mappings: list[Mapping[str, Any]]) -> bool:
    event_tokens = [
        _compact_label(value)
        for mapping in mappings
        for key in ("trigger", "webhookType", "action", "type", "eventType")
        for value in (_lookup(mapping, key),)
        if isinstance(value, str)
    ]

    if any(token in {"statuschanged", "statechanged", "workflowstatechanged"} for token in event_tokens):
        return True

    update_event = any(
        token in {"update", "updated", "issueupdate", "issueupdated", "updatedissue"}
        for token in event_tokens
    )
    return update_event and _status_field_was_changed(mappings)


def _status_field_was_changed(mappings: list[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        for key in ("updatedFields", "changedFields", "changedProperties"):
            value = _lookup(mapping, key)
            if _contains_status_field(value):
                return True

        for key in ("changes", "change", "updatedFrom", "updated_from"):
            value = _lookup(mapping, key)
            if isinstance(value, Mapping) and any(_is_status_field(field) for field in value):
                return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        return any(_is_status_field(field) for field in value)
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    return _compact_label(value) in STATUS_FIELD_NAMES


def _extract_new_status(mappings: list[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "newState",
        "new_state",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    for mapping in mappings:
        for key in explicit_keys:
            status = _status_text(_lookup(mapping, key))
            if status:
                return status

    for mapping in mappings:
        for key in ("changes", "change", "updatedFrom", "updated_from"):
            status = _status_from_change_mapping(_lookup(mapping, key))
            if status:
                return status

    for mapping in mappings:
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _status_text(_lookup(mapping, key))
            if status:
                return status

    return None


def _status_from_change_mapping(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for field, change in value.items():
        if not _is_status_field(field):
            continue

        status = _status_text(change)
        if status:
            return status
        if isinstance(change, Mapping):
            for key in ("to", "after", "newValue", "new_value", "current", "name"):
                status = _status_text(_lookup(change, key))
                if status:
                    return status

    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, str):
        return _clean_text(value)
    if isinstance(value, Mapping):
        for key in ("name", "title", "status"):
            text = _status_text(_lookup(value, key))
            if text:
                return text
    return None


def _first_text(mappings: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for mapping in mappings:
        for key in keys:
            text = _clean_text(_lookup(mapping, key))
            if text:
                return text
    return None


def _lookup(mapping: Mapping[str, Any], key: str) -> Any:
    if key in mapping:
        return mapping[key]

    normalized_key = _compact_label(key)
    for candidate_key, value in mapping.items():
        if _compact_label(candidate_key) == normalized_key:
            return value
    return None


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _normalize_label(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    return re.sub(r"\s+", " ", _split_label(text)).strip().casefold()


def _compact_label(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]+", "", _split_label(text).casefold())


def _split_label(value: str) -> str:
    split = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[^A-Za-z0-9]+", " ", split)


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        json.dump(action, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
