"""Build Linear issue title update actions for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections import deque
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_TRIGGER_KEYS = ("trigger", "event", "eventType", "event_type", "type", "action")
_STATUS_CHANGE_MARKERS = {
    "statuschange",
    "statuschanged",
    "statusupdated",
    "statechange",
    "statechanged",
    "stateupdated",
    "workflowstatechange",
    "workflowstatechanged",
    "workflowstateupdated",
}
_UPDATE_MARKERS = {"update", "updated", "issueupdate", "issueupdated", "updatedissue"}
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
)
_UPDATED_FROM_KEYS = ("updatedFrom", "updated_from", "previousValues", "previous_values")
_STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "statusname",
    "state",
    "stateid",
    "statename",
    "workflowstate",
    "workflowstateid",
    "workflowstatename",
    "workflowstatus",
    "workflowstatusid",
    "workflowstatusname",
}
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "toStatus",
    "to_status",
    "toState",
    "to_state",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state", "workflowStatus")
_NEW_VALUE_KEYS = ("to", "new", "after", "current")
_OLD_VALUE_KEYS = {"from", "old", "before", "previous", "updatedFrom", "updated_from"}
_TITLE_KEYS = ("title", "issueTitle", "issue_title")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "id")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    contexts = list(_ordered_contexts(event))
    if not _is_status_change_event(contexts):
        return None
    if _normalize_status(_new_status(contexts)) != _normalize_status(TARGET_STATUS):
        return None

    title_context = _first_issue_context_with_title(contexts)
    if title_context is None:
        return None

    title = _first_text(title_context, _TITLE_KEYS)
    if title is None or _has_research_prefix(title):
        return None

    issue_id = _issue_id(title_context, contexts)
    if issue_id is None:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _ordered_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely Linear issue/status contexts from most to least specific."""
    yielded: set[int] = set()

    def emit(value: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(value, Mapping) and id(value) not in yielded:
            yielded.add(id(value))
            yield value

    for path in (
        ("triggerContext", "issue"),
        ("triggerContext", "data"),
        ("triggerContext",),
        ("data", "issue"),
        ("payload", "issue"),
        ("issue",),
        ("data",),
        ("payload", "data"),
        ("payload",),
        (),
    ):
        yield from emit(_mapping_at_path(event, path))

    for value in _walk_mappings(event):
        yield from emit(value)


def _mapping_at_path(event: Mapping[str, Any], path: tuple[str, ...]) -> Mapping[str, Any] | None:
    value: Any = event
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value if isinstance(value, Mapping) else None


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    queue: deque[Any] = deque([value])
    seen: set[int] = set()

    while queue:
        current = queue.popleft()
        if isinstance(current, Mapping):
            if id(current) in seen:
                continue
            seen.add(id(current))
            yield current
            queue.extend(current.values())
        elif isinstance(current, list):
            queue.extend(current)


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    markers = {
        _compact_text(value)
        for context in contexts
        for key in _TRIGGER_KEYS
        for value in (context.get(key),)
        if isinstance(value, str)
    }

    if markers.intersection(_STATUS_CHANGE_MARKERS) or any(
        marker in value for value in markers for marker in _STATUS_CHANGE_MARKERS
    ):
        return True
    if (
        markers.intersection(_UPDATE_MARKERS)
        or any(marker in value for value in markers for marker in _UPDATE_MARKERS)
    ) and _updated_fields_include_status(contexts):
        return True

    return not markers and _updated_fields_include_status(contexts)


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _UPDATED_FIELD_KEYS:
            if _contains_status_field(context.get(key)):
                return True
        for key in _UPDATED_FROM_KEYS:
            if _contains_status_field(context.get(key)):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _compact_text(value) in _STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        return any(_compact_text(key) in _STATUS_FIELD_NAMES for key in value.keys()) or any(
            _contains_status_field(item) for item in value.values()
        )
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in _NEW_STATUS_KEYS:
            value = _status_text(context.get(key))
            if value is not None:
                return value

    for context in contexts:
        for key in _UPDATED_FIELD_KEYS:
            value = _status_from_updated_fields(context.get(key))
            if value is not None:
                return value

    for context in contexts:
        if _is_change_container(context):
            continue
        for key in _STATUS_KEYS:
            value = _status_text(context.get(key))
            if value is not None:
                return value

    return None


def _status_from_updated_fields(fields: Any) -> str | None:
    if not isinstance(fields, Mapping):
        return None

    for field_name, value in fields.items():
        if _compact_text(field_name) not in _STATUS_FIELD_NAMES:
            continue
        if isinstance(value, Mapping):
            for key in _NEW_VALUE_KEYS:
                status = _status_text(value.get(key))
                if status is not None:
                    return status
        else:
            status = _status_text(value)
            if status is not None:
                return status

    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _status_text(value.get(key))
            if text is not None:
                return text
    return None


def _is_change_container(context: Mapping[str, Any]) -> bool:
    keys = {_compact_text(key) for key in context.keys()}
    return bool(keys.intersection({_compact_text(key) for key in _OLD_VALUE_KEYS}))


def _first_issue_context_with_title(
    contexts: list[Mapping[str, Any]]
) -> Mapping[str, Any] | None:
    for context in contexts:
        if _first_text(context, _TITLE_KEYS) is not None:
            return context
    return None


def _first_text(context: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)
    return None


def _issue_id(
    title_context: Mapping[str, Any], contexts: list[Mapping[str, Any]]
) -> str | None:
    issue_id = _first_text(title_context, _ISSUE_ID_KEYS)
    if issue_id is not None:
        return issue_id

    for context in contexts:
        if _first_text(context, _TITLE_KEYS) is None and not _looks_like_issue_context(context):
            continue
        issue_id = _first_text(context, _ISSUE_ID_KEYS)
        if issue_id is not None:
            return issue_id

    return None


def _looks_like_issue_context(context: Mapping[str, Any]) -> bool:
    issue_keys = set(_TITLE_KEYS).union(_STATUS_KEYS).union(_NEW_STATUS_KEYS)
    return any(key in context for key in issue_keys)


def _has_research_prefix(title: str) -> bool:
    return title.lstrip().casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_status(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def _compact_text(value: Any) -> str:
    return _normalize_status(value if isinstance(value, str) else str(value)).replace(" ", "")


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
