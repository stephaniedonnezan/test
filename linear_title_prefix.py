"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_KEYS = {"status", "state", "workflowstate", "workflowstatus"}
_DIRECT_STATUS_EVENTS = {
    "statuschanged",
    "statuschange",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}
_UPDATE_EVENTS = {"update", "updated", "issueupdate", "issueupdated", "updatedissue"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to the research status."""
    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize_status(_new_status(event)) != TARGET_STATUS:
        return None

    issue_id = _issue_id(event)
    title = _issue_title(event)
    if not issue_id or not title:
        return None

    stripped_title = str(title).strip()
    if not stripped_title or _has_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": str(issue_id).strip(),
        "title": f"{PREFIX}: {stripped_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    for value in _event_type_values(event):
        normalized = _normalize_key(value)
        if normalized in _DIRECT_STATUS_EVENTS:
            return True
        if normalized in _UPDATE_EVENTS and _changed_status_field(event):
            return True

    return _changed_status_field(event)


def _event_type_values(event: Mapping[str, Any]) -> list[Any]:
    values: list[Any] = []
    for candidate in _candidate_maps(event):
        for key in ("trigger", "webhookType", "action", "type"):
            if key in candidate:
                values.append(candidate[key])
    return values


def _changed_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if _normalize_key(key) in {"updatedfields", "changedfields"}:
                if _contains_status_field(nested):
                    return True
            if _normalize_key(key) in {"changes", "updatedfield"}:
                if _changes_include_status(nested):
                    return True
            if _changed_status_field(nested):
                return True
    elif isinstance(value, list):
        return any(_changed_status_field(item) for item in value)

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_key(value) in _STATUS_FIELD_KEYS
    if isinstance(value, Mapping):
        return any(
            _normalize_key(key) in _STATUS_FIELD_KEYS or _contains_status_field(nested)
            for key, nested in value.items()
        )
    if isinstance(value, list):
        return any(_contains_status_field(item) for item in value)
    return False


def _changes_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        field = value.get("field") or value.get("name") or value.get("key")
        if field is not None and _normalize_key(field) in _STATUS_FIELD_KEYS:
            return True
        return any(
            _normalize_key(key) in _STATUS_FIELD_KEYS or _changes_include_status(nested)
            for key, nested in value.items()
        )
    if isinstance(value, list):
        return any(_changes_include_status(item) for item in value)
    if isinstance(value, str):
        return _normalize_key(value) in _STATUS_FIELD_KEYS
    return False


def _new_status(event: Mapping[str, Any]) -> Any:
    changed_status = _status_from_changes(event)
    if changed_status is not None:
        return changed_status

    for candidate in _candidate_maps(event):
        for key in (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "toStatus",
            "to_status",
            "status",
            "state",
            "workflowState",
            "workflow_state",
        ):
            if key in candidate:
                status = _status_name(candidate[key])
                if status is not None:
                    return status

    return None


def _status_from_changes(value: Any) -> Any:
    if isinstance(value, Mapping):
        field = value.get("field") or value.get("name") or value.get("key")
        if field is not None and _normalize_key(field) in _STATUS_FIELD_KEYS:
            for key in (
                "newValue",
                "new_value",
                "newStatus",
                "new_status",
                "after",
                "to",
                "value",
            ):
                if key in value:
                    status = _status_name(value[key])
                    if status is not None:
                        return status

        for key, nested in value.items():
            if _normalize_key(key) in _STATUS_FIELD_KEYS:
                status = _status_name(nested)
                if status is not None:
                    return status
            if _normalize_key(key) in {"changes", "updatedfields", "changedfields"}:
                status = _status_from_changes(nested)
                if status is not None:
                    return status
            elif isinstance(nested, (Mapping, list)):
                status = _status_from_changes(nested)
                if status is not None:
                    return status

    if isinstance(value, list):
        for item in value:
            status = _status_from_changes(item)
            if status is not None:
                return status

    return None


def _status_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if key in value:
                return value[key]
    return value


def _issue_id(event: Mapping[str, Any]) -> str | None:
    for candidate in _candidate_maps(event):
        for key in ("issueId", "issue_id", "identifier", "key", "id"):
            if key in candidate and candidate[key] is not None:
                issue_id = str(candidate[key]).strip()
                if issue_id:
                    return issue_id
    return None


def _issue_title(event: Mapping[str, Any]) -> str | None:
    for candidate in _candidate_maps(event):
        if "title" in candidate and candidate["title"] is not None:
            title = str(candidate["title"]).strip()
            if title:
                return title
    return None


def _candidate_maps(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in candidates:
            candidates.append(value)

    add(event.get("triggerContext"))
    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data)
    add(event.get("issue"))
    add(event)
    return candidates


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_status(value: Any) -> str:
    if value is None:
        return ""
    return _spaced_words(value)


def _normalize_key(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"[^a-z0-9]+", "", _spaced_words(value))


def _spaced_words(value: Any) -> str:
    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
