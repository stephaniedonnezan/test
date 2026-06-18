"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "workflowstate",
    "workflow status",
    "workflowstatus",
}
_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
    "workflowstate changed",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action for issues moved to To Research.

    The function is intentionally side-effect free so automation glue can decide
    how to send the returned action to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_label(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(event, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _extract_first_text(event, ("title",))
    if not issue_id or not title:
        return None

    trimmed_title = title.strip()
    if _normalize_for_prefix_check(trimmed_title).startswith(
        _normalize_for_prefix_check(PREFIX)
    ):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {trimmed_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize_label(value)
        for source in _metadata_sources(event)
        for key in ("trigger", "webhookType", "action", "type")
        if (value := source.get(key)) is not None
    ]

    if any(value in _DIRECT_STATUS_CHANGE_EVENTS for value in trigger_values):
        return True

    if any(value in _GENERIC_UPDATE_EVENTS for value in trigger_values):
        return _status_field_was_changed(event)

    return False


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for source in _candidate_sources(event):
        for key in (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "statusName",
            "stateName",
            "workflowStateName",
        ):
            value = _coerce_label(source.get(key))
            if value:
                return value

    changed_status = _extract_changed_status(event)
    if changed_status:
        return changed_status

    for source in _candidate_sources(event):
        for key in ("status", "state", "workflowState", "workflow_status"):
            value = _coerce_label(source.get(key))
            if value:
                return value

    return None


def _extract_changed_status(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized_key = _normalize_label(key)
            if normalized_key in {"changes", "changed", "change", "state", "status", "workflow state", "workflowstate"}:
                extracted = _extract_status_from_change_container(nested, normalized_key)
                if extracted:
                    return extracted

        for nested in value.values():
            extracted = _extract_changed_status(nested)
            if extracted:
                return extracted

    elif isinstance(value, list):
        for item in value:
            extracted = _extract_changed_status(item)
            if extracted:
                return extracted

    return None


def _extract_status_from_change_container(value: Any, container_key: str) -> str | None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized_key = _normalize_label(key)
            if normalized_key in _STATUS_FIELD_NAMES:
                return _coerce_change_target(nested)
            if container_key in _STATUS_FIELD_NAMES and normalized_key in {
                "new",
                "to",
                "after",
                "current",
                "new value",
                "newvalue",
                "name",
            }:
                coerced = _coerce_label(nested)
                if coerced:
                    return coerced

    elif container_key in _STATUS_FIELD_NAMES:
        return _coerce_label(value)

    return None


def _coerce_change_target(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "new", "to", "after", "current", "name"):
            coerced = _coerce_label(value.get(key))
            if coerced:
                return coerced
    return _coerce_label(value)


def _status_field_was_changed(event: Mapping[str, Any]) -> bool:
    for source in _candidate_sources(event):
        for key in ("updatedFields", "changedFields"):
            if _contains_status_field(source.get(key)):
                return True

        changes = source.get("changes")
        if isinstance(changes, Mapping) and any(
            _normalize_label(key) in _STATUS_FIELD_NAMES for key in changes
        ):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_label(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(
            _normalize_label(key) in _STATUS_FIELD_NAMES or _contains_status_field(nested)
            for key, nested in value.items()
        )

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _extract_first_text(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for source in _candidate_sources(event):
        for key in keys:
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _metadata_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources = [event]
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        sources.insert(0, trigger_context)
    data = event.get("data")
    if isinstance(data, Mapping):
        sources.append(data)
    return sources


def _candidate_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []

    def add(source: Any) -> None:
        if isinstance(source, Mapping) and source not in sources:
            sources.append(source)

    trigger_context = event.get("triggerContext")
    add(trigger_context)

    for root in (trigger_context, event):
        if not isinstance(root, Mapping):
            continue
        add(_get_nested(root, ("data", "issue")))
        add(root.get("issue"))
        add(root.get("data"))

    add(event)
    return sources


def _get_nested(source: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = source
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _coerce_label(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            coerced = _coerce_label(value.get(key))
            if coerced:
                return coerced
    return None


def _normalize_label(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    with_spaces = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    with_spaces = re.sub(r"[^A-Za-z0-9]+", " ", with_spaces)
    return re.sub(r"\s+", " ", with_spaces).strip().lower()


def _normalize_for_prefix_check(value: str) -> str:
    return value.strip().casefold()


def _main() -> int:
    payload = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(payload), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
