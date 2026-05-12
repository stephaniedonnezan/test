"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "workflowstate",
    "status id",
    "statusid",
    "state id",
    "stateid",
    "workflow state id",
    "workflowstateid",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research.

    The automation runner is expected to perform the returned action. Payloads
    from Cursor automations and Linear webhooks vary slightly, so this function
    accepts both flat trigger contexts and nested issue-update payloads.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _new_status_name(event)
    if _normalize_label(status) != TARGET_STATUS:
        return None

    issue_id = _first_string(_issue_candidates(event), ("issueId", "issue_id", "id", "identifier"))
    title = _first_string(_issue_candidates(event), ("title",))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {stripped_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    direct_trigger = _first_string(
        _event_candidates(event),
        ("trigger", "event", "eventType", "event_type"),
    )
    if _is_status_change_label(direct_trigger):
        return True

    action = _first_string(_event_candidates(event), ("action", "type"))
    normalized_action = _normalize_label(action)
    if normalized_action in {"update", "updated", "issue updated", "updated issue"}:
        return _has_status_updated_field(event)

    return False


def _is_status_change_label(value: str | None) -> bool:
    normalized = _normalize_label(value)
    return normalized in {"status changed", "status change", "state changed", "state change"}


def _new_status_name(event: Mapping[str, Any]) -> str | None:
    candidates = _event_candidates(event) + _issue_candidates(event)
    direct = _first_string(
        candidates,
        (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "statusName",
            "status_name",
            "stateName",
            "state_name",
            "workflowStateName",
            "workflow_state_name",
        ),
    )
    if direct:
        return direct

    for candidate in candidates:
        status = _status_from_mapping(candidate)
        if status:
            return status

    return None


def _status_from_mapping(mapping: Mapping[str, Any]) -> str | None:
    for key in ("status", "state", "workflowState", "workflow_state"):
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, Mapping):
            name = value.get("name")
            if isinstance(name, str) and name.strip():
                return name
    return None


def _has_status_updated_field(event: Mapping[str, Any]) -> bool:
    for key, value in _walk_items(event):
        if _normalize_label(key) not in {"updated fields", "changed fields", "updatedfrom", "updated from"}:
            continue

        if isinstance(value, Mapping):
            if any(_is_status_field_name(field_name) for field_name in value.keys()):
                return True
        elif isinstance(value, str):
            if _is_status_field_name(value):
                return True
        elif isinstance(value, Iterable) and not isinstance(value, (bytes, str)):
            for item in value:
                if isinstance(item, str) and _is_status_field_name(item):
                    return True
                if isinstance(item, Mapping):
                    if any(
                        _is_status_field_name(item_value)
                        for item_value in (item.get("name"), item.get("field"), item.get("key"))
                        if isinstance(item_value, str)
                    ):
                        return True

    return False


def _is_status_field_name(value: str) -> bool:
    return _normalize_label(value) in _STATUS_FIELD_NAMES


def _event_candidates(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []
    _append_mapping(candidates, event.get("triggerContext"))
    _append_mapping(candidates, event)
    _append_mapping(candidates, event.get("data"))
    return candidates


def _issue_candidates(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []
    trigger_context = event.get("triggerContext")
    data = event.get("data")

    if isinstance(trigger_context, Mapping):
        _append_mapping(candidates, trigger_context.get("issue"))
        _append_mapping(candidates, trigger_context)

    if isinstance(data, Mapping):
        _append_mapping(candidates, data.get("issue"))
        _append_mapping(candidates, data)

    _append_mapping(candidates, event.get("issue"))
    _append_mapping(candidates, event)
    return candidates


def _append_mapping(candidates: list[Mapping[str, Any]], value: Any) -> None:
    if isinstance(value, Mapping) and not any(value is existing for existing in candidates):
        candidates.append(value)


def _first_string(candidates: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for candidate in candidates:
        for key in keys:
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_label(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    with_spaces = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    with_spaces = re.sub(r"[^A-Za-z0-9]+", " ", with_spaces)
    return re.sub(r"\s+", " ", with_spaces).strip().casefold()


def _walk_items(value: Any) -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if isinstance(key, str):
                yield key, child
            yield from _walk_items(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_items(child)


def main() -> int:
    payload = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(payload)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
