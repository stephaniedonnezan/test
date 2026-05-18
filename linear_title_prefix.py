"""Build title-update actions for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_CHANGE_MARKERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_UPDATE_MARKERS = {"update", "updated", "issue updated", "updated issue"}
_STATUS_FIELD_MARKERS = {"status", "state", "workflow state", "workflow status"}
_TRIGGER_KEYS = ("trigger", "action", "type", "event", "eventType", "webhookType")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
    "changedProperties",
    "changed_properties",
)
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "newWorkflowStatus",
    "new_workflow_status",
)
_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state", "workflowStatus", "workflow_status")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "id")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    title = _first_text_from_keys(_issue_scopes(event), ("title",))
    issue_id = _first_text_from_keys(_issue_scopes(event), _ISSUE_ID_KEYS)
    if not title or not issue_id:
        return None

    title = title.strip()
    if not title or title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    update_seen = False

    for scope in _walk_mappings(event):
        for key in _TRIGGER_KEYS:
            marker = _normalize(scope.get(key))
            if marker in _STATUS_CHANGE_MARKERS:
                return True
            if marker in _UPDATE_MARKERS:
                update_seen = True

    return update_seen and _updated_fields_include_status(event)


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for scope in _walk_mappings(event):
        for key in _UPDATED_FIELD_KEYS:
            if _contains_status_field(scope.get(key)):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    normalized = _normalize(value)
    if normalized in _STATUS_FIELD_MARKERS:
        return True

    if isinstance(value, Mapping):
        for key, item in value.items():
            if _normalize(key) in _STATUS_FIELD_MARKERS or _contains_status_field(item):
                return True
        return False

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_contains_status_field(item) for item in value)

    return False


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    scopes = _status_scopes(event)

    for scope in scopes:
        status = _first_text_from_keys((scope,), _NEW_STATUS_KEYS)
        if status:
            return status

    for scope in scopes:
        status = _first_text_from_keys((scope,), _STATUS_KEYS)
        if status:
            return status

    return None


def _status_scopes(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    scopes: list[Mapping[str, Any]] = []
    _append_mapping(scopes, event)
    _append_mapping(scopes, event.get("triggerContext"))
    _append_mapping(scopes, event.get("data"))
    _append_mapping(scopes, _mapping_get(event.get("data"), "issue"))
    _append_mapping(scopes, event.get("issue"))

    for scope in _walk_mappings(event):
        _append_mapping(scopes, scope)

    return scopes


def _issue_scopes(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    scopes: list[Mapping[str, Any]] = []
    _append_mapping(scopes, event.get("triggerContext"))
    _append_mapping(scopes, _mapping_get(event.get("data"), "issue"))
    _append_mapping(scopes, event.get("issue"))
    _append_mapping(scopes, event.get("data"))
    _append_mapping(scopes, event)

    for scope in _walk_mappings(event):
        _append_mapping(scopes, scope)

    return scopes


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for item in value.values():
            yield from _walk_mappings(item)
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for item in value:
            yield from _walk_mappings(item)


def _append_mapping(scopes: list[Mapping[str, Any]], value: Any) -> None:
    if not isinstance(value, Mapping):
        return
    if all(id(value) != id(scope) for scope in scopes):
        scopes.append(value)


def _mapping_get(value: Any, key: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(key)
    return None


def _first_text_from_keys(scopes: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for scope in scopes:
        for key in keys:
            text = _to_text(scope.get(key))
            if text:
                return text
    return None


def _to_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _first_text_from_keys((value,), ("name", "title", "status", "identifier", "id"))
    if isinstance(value, str):
        return value.strip() or None
    if value is None:
        return None
    return str(value).strip() or None


def _normalize(value: Any) -> str:
    text = _to_text(value)
    if not text:
        return ""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> None:
    result = build_issue_title_update(json.load(sys.stdin))
    if result is not None:
        print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
