"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}
DIRECT_STATUS_CHANGE_MARKERS = {
    "statuschanged",
    "statuschange",
    "status changed",
    "status_changed",
    "workflowstatechanged",
    "workflow state changed",
    "statechanged",
    "state changed",
}
GENERIC_UPDATE_MARKERS = {"update", "updated", "issue update", "issue updated", "updated issue"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change(event, contexts):
        return None

    new_status = _new_status(event, contexts)
    if _normalize_status(new_status) != TARGET_STATUS:
        return None

    issue_id = _issue_id(contexts)
    title = _issue_title(contexts)
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return relevant payload mappings from outermost to innermost."""

    contexts: list[Mapping[str, Any]] = [event]
    for path in (
        ("triggerContext",),
        ("data",),
        ("issue",),
        ("data", "issue"),
        ("payload",),
        ("payload", "issue"),
        ("webhook",),
        ("webhook", "issue"),
    ):
        value = _get_path(event, path)
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)
    return contexts


def _is_status_change(event: Mapping[str, Any], contexts: list[Mapping[str, Any]]) -> bool:
    markers = []
    for context in contexts:
        for key in ("trigger", "action", "type", "event", "webhookType", "triggerType"):
            value = _string_value(context.get(key))
            if value:
                markers.append(_normalize_marker(value))

    if any(marker in DIRECT_STATUS_CHANGE_MARKERS for marker in markers):
        return True

    if any(marker in GENERIC_UPDATE_MARKERS for marker in markers):
        return _changed_fields_include_status(event, contexts)

    return _changed_fields_include_status(event, contexts)


def _changed_fields_include_status(
    event: Mapping[str, Any], contexts: list[Mapping[str, Any]]
) -> bool:
    candidates: list[Any] = []
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if key in context:
                candidates.append(context[key])
        for key in ("changes", "updatedProperties"):
            if key in context:
                candidates.append(context[key])

    for candidate in candidates:
        if _field_collection_mentions_status(candidate):
            return True

    return _status_change_object(event) is not None


def _field_collection_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field(value) in STATUS_FIELDS
    if isinstance(value, Mapping):
        return any(
            _normalize_field(str(key)) in STATUS_FIELDS
            or _field_collection_mentions_status(item)
            for key, item in value.items()
        )
    if isinstance(value, list | tuple | set):
        return any(_field_collection_mentions_status(item) for item in value)
    return False


def _new_status(event: Mapping[str, Any], contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in (
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
        ):
            value = _string_value(context.get(key))
            if value:
                return value

    changed_status = _status_change_object(event)
    if changed_status:
        return changed_status

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = context.get(key)
            resolved = _name_value(value)
            if resolved:
                return resolved

    return None


def _status_change_object(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _normalize_field(str(key)) in STATUS_FIELDS:
                resolved = _change_destination(item)
                if resolved:
                    return resolved
        for item in value.values():
            resolved = _status_change_object(item)
            if resolved:
                return resolved
    elif isinstance(value, list | tuple):
        for item in value:
            resolved = _status_change_object(item)
            if resolved:
                return resolved
    return None


def _change_destination(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "new", "after", "current", "value", "name"):
            resolved = _name_value(value.get(key))
            if resolved:
                return resolved
    return _name_value(value)


def _issue_id(contexts: list[Mapping[str, Any]]) -> str | None:
    for key in ("identifier", "issueId", "issue_id", "key", "id"):
        for context in reversed(contexts):
            value = _string_value(context.get(key))
            if value:
                return value
    return None


def _issue_title(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in reversed(contexts):
        value = _string_value(context.get("title"))
        if value:
            return value
    return None


def _get_path(value: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = value
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _name_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _string_value(value.get(key))
            if text:
                return text
        return None
    return _string_value(value)


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    words = re.sub(r"([a-z])([A-Z])", r"\1 \2", value)
    words = re.sub(r"[_\-\s]+", " ", words).strip().lower()
    return words or None


def _normalize_marker(value: str) -> str:
    words = re.sub(r"([a-z])([A-Z])", r"\1 \2", value)
    words = re.sub(r"[_\-\s]+", " ", words).strip().lower()
    compact = words.replace(" ", "")
    return compact if compact in DIRECT_STATUS_CHANGE_MARKERS else words


def _normalize_field(value: str) -> str:
    words = re.sub(r"([a-z])([A-Z])", r"\1 \2", value)
    return re.sub(r"[_\-\s]+", " ", words).strip().lower().replace(" ", "")


def main() -> int:
    """Read a JSON event from stdin and print the computed action, if any."""

    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is None:
        return 0

    print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
