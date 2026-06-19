"""Build Linear issue title updates for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
PREFIXED_TITLE = f"{PREFIX}: "

_EVENT_KEYS = ("trigger", "webhookType", "action", "type", "event", "eventType")
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "status",
    "state",
    "workflowState",
    "workflow_state",
)
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
)
_CHANGE_KEYS = ("changes", "change", "updatedFrom")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue enters "to research".

    The handler is intentionally side-effect free so callers can wire the
    returned action into their Linear update mechanism.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_gather_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    status = _find_status(contexts)
    if not _is_to_research(status):
        return None

    issue_id = _find_text(contexts, _ISSUE_ID_KEYS)
    title = _find_text(contexts, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIXED_TITLE}{title}",
    }


def _gather_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely payload locations from most to least automation-specific."""

    seen: set[int] = set()

    def add(value: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            yield value

    automation_info = event.get("automation_trigger_info") or event.get(
        "automationTriggerInfo"
    )
    if isinstance(automation_info, Mapping):
        yield from add(automation_info.get("triggerContext"))
        yield from add(automation_info.get("trigger_context"))
        yield from add(automation_info)

    yield from add(event.get("triggerContext"))
    yield from add(event.get("trigger_context"))
    yield from add(event)

    data = event.get("data")
    if isinstance(data, Mapping):
        yield from add(data)
        yield from add(data.get("issue"))
        yield from add(data.get("node"))

    yield from add(event.get("issue"))


def _is_status_change_event(contexts: Sequence[Mapping[str, Any]]) -> bool:
    if _has_status_change_trigger(contexts):
        return True

    if not _has_issue_update_trigger(contexts):
        return False

    return _has_updated_status_field(contexts) or _has_status_change_record(contexts)


def _has_status_change_trigger(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _EVENT_KEYS:
            value = context.get(key)
            normalized = _compact_text(value)
            if normalized in {
                "statuschanged",
                "statuschange",
                "statechanged",
                "statechange",
                "workflowstatechanged",
                "workflowstatechange",
            }:
                return True
    return False


def _has_issue_update_trigger(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _EVENT_KEYS:
            normalized = _normalize_text(context.get(key))
            compact = normalized.replace(" ", "")
            if compact in {"issueupdated", "updatedissue"} or normalized == "update":
                return True
    return False


def _has_updated_status_field(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _UPDATED_FIELD_KEYS:
            if _contains_status_field(context.get(key)):
                return True
    return False


def _has_status_change_record(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _CHANGE_KEYS:
            if _changes_include_status(context.get(key)):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _compact_text(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        for key, item in value.items():
            if _compact_text(key) in _STATUS_FIELD_NAMES:
                return True
            if isinstance(item, Mapping):
                nested_name = item.get("field") or item.get("name") or item.get("key")
                if _compact_text(nested_name) in _STATUS_FIELD_NAMES:
                    return True
        return False

    if isinstance(value, Sequence):
        return any(
            _contains_status_field(item)
            for item in value
            if not isinstance(item, (bytes, bytearray))
        )

    return False


def _changes_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _compact_text(key) in _STATUS_FIELD_NAMES:
                return True
            if isinstance(item, Mapping):
                field = item.get("field") or item.get("name") or item.get("key")
                if _compact_text(field) in _STATUS_FIELD_NAMES:
                    return True
        return False

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_changes_include_status(item) for item in value)

    return False


def _find_status(contexts: Sequence[Mapping[str, Any]]) -> Any:
    for context in contexts:
        for key in _EXPLICIT_STATUS_KEYS:
            if key in context:
                return _status_value(context[key])

    for context in contexts:
        for key in _CHANGE_KEYS:
            status = _status_from_changes(context.get(key))
            if status is not None:
                return status

    return None


def _status_from_changes(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _compact_text(key) in _STATUS_FIELD_NAMES:
                return _new_value(item)
            if isinstance(item, Mapping):
                field = item.get("field") or item.get("name") or item.get("key")
                if _compact_text(field) in _STATUS_FIELD_NAMES:
                    return _new_value(item)

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            status = _status_from_changes(item)
            if status is not None:
                return status

    return None


def _new_value(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return _status_value(value)

    for key in ("newValue", "new_value", "after", "to", "value", "name"):
        if key in value:
            return _status_value(value[key])

    return _status_value(value)


def _status_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value"):
            if key in value:
                return value[key]
    return value


def _is_to_research(value: Any) -> bool:
    return _normalize_text(value) == "to research"


def _find_text(contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
            if value is not None and not isinstance(value, (Mapping, Sequence)):
                return str(value)
    return None


def _has_research_prefix(title: str) -> bool:
    return re.match(r"^\s*cursor\s+researching\b", title, re.IGNORECASE) is not None


def _normalize_text(value: Any) -> str:
    value = _status_value(value)
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _compact_text(value: Any) -> str:
    return _normalize_text(value).replace(" ", "")


def main() -> int:
    payload = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(payload), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
