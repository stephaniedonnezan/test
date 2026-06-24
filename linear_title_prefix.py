"""Build Linear issue title updates for Cursor research handoffs.

The automation receives Linear status-change payloads in a few shapes.  This
module keeps the decision small and side-effect free: callers pass a decoded
event and receive the title update action to perform, or ``None``.
"""

from __future__ import annotations

import json
import re
import sys
from collections import deque
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_KEYS = {"status", "state", "workflowstate", "workflow_state"}
_STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}
_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    mappings = _event_mappings(event)

    if not _is_status_change_event(mappings):
        return None

    new_status = _extract_new_status(mappings)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_string(mappings, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _extract_string(mappings, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _event_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return relevant payload objects, preferring automation metadata first."""

    prioritized: list[Mapping[str, Any]] = []

    automation_info = event.get("automation_trigger_info") or event.get("automationTriggerInfo")
    if isinstance(automation_info, Mapping):
        _append_mapping(prioritized, automation_info.get("triggerContext"))

    _append_mapping(prioritized, event.get("triggerContext"))
    _append_mapping(prioritized, event)
    _append_mapping(prioritized, event.get("data"))
    _append_mapping(prioritized, event.get("issue"))

    data = event.get("data")
    if isinstance(data, Mapping):
        _append_mapping(prioritized, data.get("issue"))

    # Include shallow nested maps so Linear webhook variants such as
    # ``changes.state.to`` can be recognized without making assumptions about
    # the exact provider payload.
    for nested in _walk_mappings(event, max_depth=4):
        _append_mapping(prioritized, nested)

    return prioritized


def _append_mapping(mappings: list[Mapping[str, Any]], value: Any) -> None:
    if isinstance(value, Mapping) and not any(value is existing for existing in mappings):
        mappings.append(value)


def _walk_mappings(root: Mapping[str, Any], max_depth: int) -> Iterable[Mapping[str, Any]]:
    queue: deque[tuple[Any, int]] = deque([(root, 0)])
    seen: set[int] = set()

    while queue:
        value, depth = queue.popleft()
        if id(value) in seen:
            continue
        seen.add(id(value))

        if isinstance(value, Mapping):
            yield value
            if depth >= max_depth:
                continue
            for child in value.values():
                if isinstance(child, (Mapping, list, tuple)):
                    queue.append((child, depth + 1))
        elif isinstance(value, (list, tuple)) and depth < max_depth:
            for child in value:
                if isinstance(child, (Mapping, list, tuple)):
                    queue.append((child, depth + 1))


def _is_status_change_event(mappings: list[Mapping[str, Any]]) -> bool:
    trigger_values = _extract_trigger_values(mappings)
    if any(_compact_words(value) in _STATUS_CHANGE_TRIGGERS for value in trigger_values):
        return True

    if any(_compact_words(value) in _GENERIC_UPDATE_TRIGGERS for value in trigger_values):
        return _mentions_status_field(mappings)

    return False


def _extract_trigger_values(mappings: list[Mapping[str, Any]]) -> list[str]:
    values: list[str] = []
    trigger_keys = {"trigger", "webhooktype", "webhook_type", "action", "type", "eventtype", "event_type"}

    for mapping in mappings:
        for key, value in mapping.items():
            if _normalize_key(str(key)) in trigger_keys:
                text = _string_value(value)
                if text:
                    values.append(text)

    return values


def _mentions_status_field(mappings: list[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        for key, value in mapping.items():
            normalized_key = _normalize_key(str(key))

            if normalized_key in {"updatedfields", "changedfields"}:
                if _iterable_mentions_status(value):
                    return True

            if normalized_key in {"changes", "updatedfrom", "previous", "before"}:
                if _mapping_mentions_status(value):
                    return True

    return False


def _iterable_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_key(value) in _STATUS_FIELD_KEYS
    if isinstance(value, Mapping):
        return _mapping_mentions_status(value)
    if isinstance(value, Iterable):
        return any(_iterable_mentions_status(item) for item in value)
    return False


def _mapping_mentions_status(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False

    for key, child in value.items():
        if _normalize_key(str(key)) in _STATUS_FIELD_KEYS:
            return True
        if isinstance(child, Mapping) and _mapping_mentions_status(child):
            return True
    return False


def _extract_new_status(mappings: list[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    status_keys = ("status", "state", "workflowState", "workflow_state")

    explicit = _extract_string(mappings, explicit_keys)
    if explicit:
        return explicit

    changed = _extract_changed_status(mappings)
    if changed:
        return changed

    return _extract_string(mappings, status_keys)


def _extract_changed_status(mappings: list[Mapping[str, Any]]) -> str | None:
    for mapping in mappings:
        for key, value in mapping.items():
            normalized_key = _normalize_key(str(key))
            if normalized_key not in {"changes", "updatedfrom"} or not isinstance(value, Mapping):
                continue

            for status_key in ("status", "state", "workflowState", "workflow_state"):
                status_value = _get_key(value, status_key)
                if not isinstance(status_value, Mapping):
                    continue

                changed_value = _extract_string(
                    [status_value],
                    ("to", "new", "after", "current", "name"),
                )
                if changed_value:
                    return changed_value

    return None


def _extract_string(mappings: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for wanted_key in keys:
        for mapping in mappings:
            value = _get_key(mapping, wanted_key)
            text = _string_value(value)
            if text:
                return text
    return None


def _get_key(mapping: Mapping[str, Any], wanted_key: str) -> Any:
    normalized_wanted = _normalize_key(wanted_key)
    for key, value in mapping.items():
        if _normalize_key(str(key)) == normalized_wanted:
            return value
    return None


def _string_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "id", "identifier", "key"):
            text = _string_value(_get_key(value, key))
            if text:
                return text
    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _split_camel_case(value).lower())


def _normalize_words(value: str | None) -> str | None:
    if value is None:
        return None
    words = re.sub(r"[^a-z0-9]+", " ", _split_camel_case(value).lower())
    return " ".join(words.split())


def _compact_words(value: str) -> str:
    normalized = _normalize_words(value)
    return "" if normalized is None else normalized.replace(" ", "")


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    """Read a JSON event from stdin and print the update action as JSON."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    result = build_issue_title_update(event)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
