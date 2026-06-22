"""Build Linear issue title updates for research-status transitions.

The public entrypoint is :func:`build_issue_title_update`, which accepts a
decoded Linear/Cursor automation payload and returns a small action dictionary
when the issue title should be prefixed.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
    "workflow",
    "workflowid",
}
STATUS_CHANGED_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
    "issue status changed",
}
UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action for transitions to "to research".

    The function is intentionally side-effect free so webhook handlers, scripts,
    or automation runners can decide how to apply the returned action.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_title = _extract_issue_title(event)
    issue_id = _extract_issue_id(event)
    if not issue_title or not issue_id:
        return None

    stripped_title = issue_title.strip()
    if _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values: list[str] = []
    for container in _metadata_containers(event):
        for key, raw_value in container.items():
            value = _string_value(raw_value)
            if _normalize_key(str(key)) in {"trigger", "webhooktype"} and value:
                trigger_values.append(value)
    if any(_normalize_text(value) in STATUS_CHANGED_TRIGGERS for value in trigger_values):
        return True

    action_values: list[str] = []
    for container in _metadata_containers(event):
        for key, raw_value in container.items():
            value = _string_value(raw_value)
            if _normalize_key(str(key)) in {"action", "type"} and value:
                action_values.append(_normalize_text(value))
    if any(value in STATUS_CHANGED_TRIGGERS for value in action_values):
        return True

    if any(value in UPDATE_TRIGGERS for value in action_values):
        return _has_status_field_change(event)

    return False


def _has_status_field_change(event: Mapping[str, Any]) -> bool:
    for container in _walk_mappings(event):
        for key, value in container.items():
            normalized_key = _normalize_key(str(key))

            if normalized_key in {"updatedfields", "changedfields"}:
                if any(_is_status_field_name(item) for item in _iter_values(value)):
                    return True

            if normalized_key in {"updatedfrom", "previous", "previousvalues", "changes"}:
                if _contains_status_field(value):
                    return True

            if normalized_key in {
                "statuschanged",
                "statechanged",
                "workflowstatechanged",
            } and bool(value):
                return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            _is_status_field_name(key) or _contains_status_field(nested)
            for key, nested in value.items()
        )
    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field_name(value: Any) -> bool:
    text = _normalize_key(str(value))
    return text in STATUS_FIELD_NAMES or text.endswith("status") or text.endswith("state")


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    direct_keys = (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    for container in _candidate_containers(event):
        value = _first_string_for_keys(container, direct_keys)
        if value:
            return value

    for container in _candidate_containers(event):
        value = _first_status_like_value(container, fallback_keys)
        if value:
            return value

    return None


def _extract_issue_title(event: Mapping[str, Any]) -> str | None:
    for container in _candidate_containers(event):
        value = _first_string_for_keys(container, ("title",))
        if value and value.strip():
            return value
    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    preferred_keys = ("issueId", "issue_id", "identifier", "key", "id")
    for container in _candidate_containers(event):
        value = _first_string_for_keys(container, preferred_keys)
        if value and value.strip():
            return value
    return None


def _candidate_containers(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    containers: list[Mapping[str, Any]] = []

    for path in (
        ("triggerContext",),
        ("data", "issue"),
        ("issue",),
        ("data",),
        (),
    ):
        value: Any = event
        for key in path:
            if not isinstance(value, Mapping):
                break
            value = value.get(key)
        else:
            if isinstance(value, Mapping):
                containers.append(value)

    containers.extend(
        nested
        for nested in _walk_mappings(event)
        if nested not in containers and "title" in nested
    )
    return containers


def _metadata_containers(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    containers = [event]
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        containers.append(trigger_context)
    return containers


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested in value.values():
            yield from _walk_mappings(nested)
    elif isinstance(value, list | tuple | set):
        for nested in value:
            yield from _walk_mappings(nested)


def _first_string_for_keys(container: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    key_lookup = {_normalize_key(str(key)): value for key, value in container.items()}
    for key in keys:
        value = key_lookup.get(_normalize_key(key))
        if value is None:
            continue
        string = _string_value(value)
        if string is not None:
            return string
    return None


def _first_status_like_value(
    container: Mapping[str, Any], keys: Iterable[str]
) -> str | None:
    key_lookup = {_normalize_key(key): key for key in keys}
    for key, value in container.items():
        if _normalize_key(str(key)) not in key_lookup:
            continue
        if isinstance(value, Mapping):
            nested = _first_string_for_keys(
                value, ("name", "title", "status", "state", "workflowState")
            )
            if nested:
                return nested
        else:
            string = _string_value(value)
            if string is not None:
                return string
    return None


def _iter_values(value: Any) -> Iterable[Any]:
    if isinstance(value, Mapping):
        yield from value.keys()
    elif isinstance(value, str):
        yield value
    elif isinstance(value, Iterable):
        yield from value


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, int | float):
        return str(value)
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_text(value: Any) -> str:
    string = _string_value(value)
    if string is None:
        return ""
    words = _split_words(string)
    return " ".join(words)


def _normalize_key(value: str) -> str:
    return "".join(_split_words(value))


def _split_words(value: str) -> list[str]:
    split_camel = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", split_camel).strip().lower()
    return normalized.split()


def main() -> int:
    """Read a JSON event from stdin and print the update action, if any."""

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print(f"Invalid JSON: {error}", file=sys.stderr)
        return 1

    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
