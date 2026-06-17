"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflowstatus"}
DIRECT_STATUS_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatuschanged",
}
GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdated",
    "issueupdate",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if not issue_id or not title:
        return None

    clean_title = str(title).strip()
    if not clean_title or clean_title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": str(issue_id).strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_tokens = {
        _normalize_token(value)
        for mapping in _iter_mappings(event)
        for key, value in mapping.items()
        if key in {"trigger", "action", "type", "webhookType", "event", "webhook_type"}
    }

    if trigger_tokens & DIRECT_STATUS_TRIGGERS:
        return True

    if trigger_tokens & GENERIC_UPDATE_TRIGGERS:
        return _status_field_changed(event)

    return False


def _status_field_changed(event: Mapping[str, Any]) -> bool:
    for mapping in _iter_mappings(event):
        for key, value in mapping.items():
            normalized_key = _normalize_token(key)
            if normalized_key in {
                "updatedfields",
                "changedfields",
                "changedproperties",
                "updatedproperties",
            }:
                if _iterable_mentions_status_field(value):
                    return True

            if normalized_key in {"changes", "changed", "diff"} and isinstance(value, Mapping):
                if any(_is_status_field_name(field) for field in value):
                    return True

    return False


def _iterable_mentions_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if not isinstance(value, Iterable) or isinstance(value, (bytes, bytearray, Mapping)):
        return False

    return any(_is_status_field_name(item) for item in value)


def _is_status_field_name(value: Any) -> bool:
    return _normalize_token(value) in STATUS_FIELD_NAMES


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "newWorkflowStatus",
        "statusName",
        "stateName",
        "workflowStateName",
    )
    for mapping in _candidate_mappings(event):
        for key in explicit_keys:
            if key in mapping:
                status = _status_name(mapping[key])
                if status:
                    return status

    for mapping in _iter_mappings(event):
        changes = mapping.get("changes")
        if isinstance(changes, Mapping):
            status = _status_from_changes(changes)
            if status:
                return status

    for mapping in _candidate_mappings(event):
        for key in ("status", "state", "workflowState", "workflowStatus"):
            if key in mapping:
                status = _status_name(mapping[key])
                if status:
                    return status

    return None


def _status_from_changes(changes: Mapping[str, Any]) -> str | None:
    for field, value in changes.items():
        if not _is_status_field_name(field):
            continue

        if isinstance(value, Mapping):
            for key in ("new", "to", "after", "current", "newValue", "value", "name"):
                if key in value:
                    status = _status_name(value[key])
                    if status:
                        return status
        else:
            status = _status_name(value)
            if status:
                return status

    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if key in value:
                status = _status_name(value[key])
                if status:
                    return status

    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for mapping in _candidate_mappings(event):
        for key in ("issueId", "issue_id", "identifier", "key", "id"):
            value = mapping.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
    return None


def _extract_title(event: Mapping[str, Any]) -> str | None:
    for mapping in _candidate_mappings(event):
        value = mapping.get("title")
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _candidate_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        candidates.append(trigger_context)
        _append_mapping(candidates, trigger_context.get("issue"))

    data = event.get("data")
    if isinstance(data, Mapping):
        _append_mapping(candidates, data.get("issue"))
        candidates.append(data)

    _append_mapping(candidates, event.get("issue"))
    candidates.append(event)

    return candidates


def _append_mapping(candidates: list[Mapping[str, Any]], value: Any) -> None:
    if isinstance(value, Mapping):
        candidates.append(value)


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _iter_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_mappings(child)


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value))
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _normalize_token(value: Any) -> str:
    return _normalize_words(value).replace(" ", "")


def main() -> int:
    """Read a JSON event from stdin and print the requested title update."""

    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
