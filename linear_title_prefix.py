"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_EVENT_KEYS = ("trigger", "webhookType", "webhook_type", "action", "type", "event")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
    "changes",
    "updatedFrom",
    "updated_from",
)
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_CURRENT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id", "uuid")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to "to research".

    The Cursor automation trigger shape is flat under ``triggerContext`` while
    Linear webhooks often nest issue details under ``data.issue``. This function
    accepts both shapes and ignores all events that are not status changes into
    the target status.
    """

    if not isinstance(event, Mapping):
        return None

    sources = _collect_sources(event)
    if not _is_status_change_event(sources):
        return None

    if _normalize(_extract_new_status(sources)) != TARGET_STATUS:
        return None

    title = _first_text(sources, ("title", "name"))
    issue_id = _first_text(sources, _ID_KEYS)
    if not title or not issue_id:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _collect_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect likely metadata and issue-detail mappings in priority order."""

    sources: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in sources:
            sources.append(value)

    add(event.get("triggerContext"))
    add(event.get("trigger_context"))
    add(event.get("issue"))

    data = event.get("data")
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("node"))

    add(event)
    return sources


def _is_status_change_event(sources: Iterable[Mapping[str, Any]]) -> bool:
    event_names = [
        _normalize(source.get(key))
        for source in sources
        for key in _EVENT_KEYS
        if source.get(key) is not None
    ]

    for event_name in event_names:
        if (
            event_name in {
                "status changed",
                "status change",
                "state changed",
                "state change",
                "workflow state changed",
                "workflow state change",
                "issue status changed",
                "issue state changed",
            }
            or "status changed" in event_name
            or "state changed" in event_name
        ):
            return True

    if any(event_name in {"update", "updated", "issue update", "issue updated", "updated issue"} for event_name in event_names):
        return _status_field_was_updated(sources)

    return False


def _status_field_was_updated(sources: Iterable[Mapping[str, Any]]) -> bool:
    for source in sources:
        for key in _UPDATED_FIELD_KEYS:
            if key not in source:
                continue
            if _contains_status_field(source[key]):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) for key in value.keys())

    if isinstance(value, Iterable):
        for item in value:
            if isinstance(item, Mapping):
                names = (item.get("field"), item.get("name"), item.get("key"), item.get("property"))
                if any(_is_status_field_name(name) for name in names if name is not None):
                    return True
            elif _is_status_field_name(item):
                return True

    return False


def _is_status_field_name(value: Any) -> bool:
    compact = _normalize(value).replace(" ", "")
    return compact in {"status", "statusid", "state", "stateid", "workflowstate", "workflowstateid"}


def _extract_new_status(sources: Iterable[Mapping[str, Any]]) -> str | None:
    for source in sources:
        text = _first_text([source], _EXPLICIT_STATUS_KEYS)
        if text:
            return text

    changed_status = _extract_status_from_changes(sources)
    if changed_status:
        return changed_status

    for source in sources:
        text = _first_status_value(source, _CURRENT_STATUS_KEYS)
        if text:
            return text

    return None


def _extract_status_from_changes(sources: Iterable[Mapping[str, Any]]) -> str | None:
    for source in sources:
        for key in ("changes", "updatedFields", "updated_fields"):
            value = source.get(key)
            if isinstance(value, Mapping):
                for field, change in value.items():
                    if _is_status_field_name(field):
                        text = _status_text(change)
                        if text:
                            return text
            elif isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
                for item in value:
                    if not isinstance(item, Mapping):
                        continue
                    field = item.get("field") or item.get("name") or item.get("key") or item.get("property")
                    if not _is_status_field_name(field):
                        continue
                    text = _status_text(item)
                    if text:
                        return text
    return None


def _first_status_value(source: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        if key in source:
            text = _status_text(source[key])
            if text:
                return text
    return None


def _first_text(sources: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for source in sources:
        for key in keys:
            if key not in source:
                continue
            value = source[key]
            if isinstance(value, str):
                text = value.strip()
                if text:
                    return text
    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None

    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "to", "after", "current", "name", "title", "displayName", "value"):
            if key in value:
                text = _status_text(value[key])
                if text:
                    return text

    return None


def _has_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(PREFIX)}\b", title, flags=re.IGNORECASE) is not None


def _normalize(value: Any) -> str:
    text = _status_text(value) if not isinstance(value, str) else value
    if text is None:
        return ""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(text))
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
