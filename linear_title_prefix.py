"""Build Linear issue title updates for research-status automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_TRIGGER_KEYS = ("trigger", "action", "type", "webhookType", "eventType")
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "statusName",
    "status_name",
    "newState",
    "new_state",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
    "status",
)
_FALLBACK_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title", "name")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action for Linear issues moved to research.

    The automation receives slightly different shapes depending on whether it is
    invoked by Cursor trigger metadata or directly by Linear webhooks. This
    function accepts those common flat and nested shapes and returns a compact
    action payload for the caller to execute.
    """

    if not isinstance(event, Mapping):
        return None

    maps = _payload_maps(event)
    if not _is_status_change(event, maps):
        return None

    status = _changed_status(event, maps)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(_issue_maps(event), _ISSUE_ID_KEYS)
    title = _first_text(_issue_maps(event), _TITLE_KEYS)
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _payload_maps(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    maps: list[Mapping[str, Any]] = [event]
    for key in ("triggerContext", "data", "issue"):
        child = event.get(key)
        if isinstance(child, Mapping):
            maps.append(child)
    data = event.get("data")
    if isinstance(data, Mapping):
        for key in ("issue", "data"):
            child = data.get(key)
            if isinstance(child, Mapping):
                maps.append(child)
    return maps


def _issue_maps(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    maps: list[Mapping[str, Any]] = []
    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            maps.append(issue)
    issue = event.get("issue")
    if isinstance(issue, Mapping):
        maps.append(issue)
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        maps.append(trigger_context)
    maps.append(event)
    if isinstance(data, Mapping):
        maps.append(data)
    return maps


def _metadata_maps(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    maps: list[Mapping[str, Any]] = [event]
    for key in ("triggerContext", "data"):
        child = event.get(key)
        if isinstance(child, Mapping):
            maps.append(child)
    return maps


def _is_status_change(event: Mapping[str, Any], maps: Iterable[Mapping[str, Any]]) -> bool:
    if any(_is_direct_status_change(mapping.get(key)) for mapping in maps for key in _TRIGGER_KEYS):
        return True

    if _changed_status_from_changes(event) is not None:
        return True

    updated_fields = _first_value(maps, ("updatedFields", "updated_fields"))
    if _contains_status_field(updated_fields):
        return True

    generic_update = any(_is_generic_issue_update(mapping.get(key)) for mapping in maps for key in _TRIGGER_KEYS)
    return generic_update and _contains_status_field(updated_fields)


def _changed_status(event: Mapping[str, Any], maps: Iterable[Mapping[str, Any]]) -> Any:
    status = _first_value(_metadata_maps(event), _EXPLICIT_STATUS_KEYS)
    if status is not None:
        return _status_name(status)

    status = _changed_status_from_changes(event)
    if status is not None:
        return _status_name(status)

    return _status_name(_first_value(_issue_maps(event), _FALLBACK_STATUS_KEYS))


def _changed_status_from_changes(event: Mapping[str, Any]) -> Any:
    for mapping in _payload_maps(event):
        changes = mapping.get("changes") or mapping.get("updatedFrom")
        if not isinstance(changes, Mapping):
            continue
        for field, change in changes.items():
            if not _is_status_field_name(field):
                continue
            if isinstance(change, Mapping):
                for key in ("new", "after", "to", "current", "name"):
                    if key in change:
                        return change[key]
            return change
    return None


def _status_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if key in value:
                return value[key]
    return value


def _first_text(maps: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    value = _first_value(maps, keys)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _first_value(maps: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> Any:
    for mapping in maps:
        for key in keys:
            if key in mapping and mapping[key] is not None:
                return mapping[key]
    return None


def _is_direct_status_change(value: Any) -> bool:
    normalized = _normalize_words(value)
    compact = normalized.replace(" ", "")
    return compact in {"statuschanged", "statuschange"} or (
        "status" in normalized.split() and "changed" in normalized.split()
    )


def _is_generic_issue_update(value: Any) -> bool:
    normalized = _normalize_words(value)
    words = set(normalized.split())
    return "update" in words or "updated" in words


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) for key in value)
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field_name(value: Any) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", _normalize_words(value))
    return normalized in {
        "status",
        "statusid",
        "statusname",
        "state",
        "stateid",
        "statename",
        "workflowstate",
        "workflowstateid",
        "workflowstatename",
    }


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[_\-/]+", " ", text)
    return " ".join(text.strip().lower().split())


def _has_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(TITLE_PREFIX)}\b", title, re.IGNORECASE) is not None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
