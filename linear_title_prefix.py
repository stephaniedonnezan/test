"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflow_state",
    "workflow-state",
}
_NEW_STATUS_KEYS = (
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
_TITLE_ID_KEYS = ("identifier", "key", "issueId", "issue_id", "id")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    sources = _payload_sources(event)
    if not _is_status_change(sources):
        return None

    new_status = _new_status(sources)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(sources, _TITLE_ID_KEYS)
    title = _first_text(sources, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _payload_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload layers from most issue-specific to broadest metadata."""

    trigger_context = _mapping_at(event, "triggerContext")
    automation_context = _mapping_at(event, "automation_trigger_info", "triggerContext")
    if automation_context:
        trigger_context = automation_context

    bases = [trigger_context, event] if trigger_context else [event]
    sources: list[Mapping[str, Any]] = []
    for base in bases:
        if not base:
            continue
        data = _mapping_at(base, "data")
        issue = _mapping_at(data, "issue") or _mapping_at(base, "issue")
        if issue:
            sources.append(issue)
        if data:
            sources.append(data)
        sources.append(base)
    return sources


def _is_status_change(sources: Iterable[Mapping[str, Any]]) -> bool:
    saw_generic_update = False

    for source in sources:
        for key in ("trigger", "webhookType", "action", "type", "event", "eventType"):
            marker = _normalize_identifier(source.get(key))
            if marker in {"statuschanged", "statechanged", "workflowstatechanged"}:
                return True
            if marker in {"update", "updated", "issueupdated", "updatedissue"}:
                saw_generic_update = True

    return saw_generic_update and _mentions_status_field(sources)


def _mentions_status_field(sources: Iterable[Mapping[str, Any]]) -> bool:
    for source in sources:
        for key in ("updatedFields", "changedFields"):
            fields = source.get(key)
            if _contains_status_field(fields):
                return True

        changes = source.get("changes") or source.get("updatedFrom")
        if isinstance(changes, Mapping):
            if any(_is_status_field(field) for field in changes):
                return True
        elif isinstance(changes, list):
            for change in changes:
                if isinstance(change, Mapping):
                    field = change.get("field") or change.get("name") or change.get("key")
                    if _is_status_field(field):
                        return True
                elif _is_status_field(change):
                    return True

    return False


def _new_status(sources: Iterable[Mapping[str, Any]]) -> str | None:
    for source in sources:
        for key in _NEW_STATUS_KEYS:
            value = _text_or_name(source.get(key))
            if value:
                return value

    for source in sources:
        for value in _status_values_from_changes(source.get("changes")):
            return value
        for value in _status_values_from_changes(source.get("updatedFrom")):
            return value

    for source in sources:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = _text_or_name(source.get(key))
            if value:
                return value

    return None


def _status_values_from_changes(changes: Any) -> Iterable[str]:
    if isinstance(changes, Mapping):
        for field, change in changes.items():
            if not _is_status_field(field):
                continue
            value = _changed_to_value(change)
            if value:
                yield value
    elif isinstance(changes, list):
        for change in changes:
            if not isinstance(change, Mapping):
                continue
            field = change.get("field") or change.get("name") or change.get("key")
            if not _is_status_field(field):
                continue
            value = _changed_to_value(change)
            if value:
                yield value


def _changed_to_value(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("to", "toValue", "newValue", "after", "value", "name"):
            value = _text_or_name(change.get(key))
            if value:
                return value
    return _text_or_name(change)


def _contains_status_field(fields: Any) -> bool:
    if isinstance(fields, str):
        return _is_status_field(fields)
    if isinstance(fields, Mapping):
        return any(_is_status_field(field) for field in fields)
    if isinstance(fields, Iterable):
        return any(_is_status_field(field) for field in fields)
    return False


def _is_status_field(value: Any) -> bool:
    return _normalize_identifier(value) in {
        _normalize_identifier(field) for field in _STATUS_FIELD_NAMES
    }


def _first_text(sources: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for source in sources:
        for key in keys:
            value = _text_or_name(source.get(key))
            if value and value.strip():
                return value
    return None


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "key", "id"):
            text = _text_or_name(value.get(key))
            if text:
                return text
    return None


def _mapping_at(payload: Mapping[str, Any] | None, *path: str) -> Mapping[str, Any] | None:
    current: Any = payload
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, Mapping) else None


def _normalize_identifier(value: Any) -> str:
    text = _text_or_name(value) or ""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _normalize_words(value: Any) -> str:
    text = _text_or_name(value) or ""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def main() -> int:
    action = build_issue_title_update(json.load(sys.stdin))
    if action:
        print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
