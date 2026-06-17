"""Build Linear issue-title updates for Cursor research status transitions.

The module is intentionally small and dependency-free so it can be used as a
library in automation code or as a stdin/stdout command in webhook pipelines.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
STATUS_TRIGGER_VALUES = {
    "status changed",
    "status change",
    "statuschanged",
    "statuschange",
    "state changed",
    "state change",
    "statechanged",
    "statechange",
    "workflow state changed",
    "workflow state change",
    "workflowstatechanged",
    "workflowstatechange",
}
ISSUE_UPDATE_VALUES = {
    "issue updated",
    "updated issue",
    "issue update",
    "update issue",
    "updated",
    "update",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to "to research".

    Supported payloads include the flat Cursor automation trigger context and
    nested Linear webhook shapes such as ``{"data": {"issue": ...}}``.
    """

    if not isinstance(event, Mapping):
        return None

    payloads = _candidate_payloads(event)
    if not any(_is_status_change_payload(payload) for payload in payloads):
        return None

    if _normalize_status(_first_status_value(payloads)) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(payloads, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(payloads, ("title", "name"))
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{RESEARCH_PREFIX}: {title}",
    }


def _candidate_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely issue/trigger objects, ordered from most specific first."""

    candidates: list[Mapping[str, Any]] = []

    for path in (
        ("triggerContext",),
        ("data", "issue"),
        ("data", "node"),
        ("issue",),
        ("node",),
        ("data",),
    ):
        value = _get_path(event, path)
        if isinstance(value, Mapping):
            candidates.append(value)

    candidates.append(event)
    return _dedupe_mappings(candidates)


def _dedupe_mappings(values: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    deduped: list[Mapping[str, Any]] = []
    seen: set[int] = set()
    for value in values:
        marker = id(value)
        if marker not in seen:
            seen.add(marker)
            deduped.append(value)
    return deduped


def _is_status_change_payload(payload: Mapping[str, Any]) -> bool:
    event_values = [
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    ]
    normalized_events = {_normalize_event(value) for value in event_values if value is not None}

    if normalized_events & STATUS_TRIGGER_VALUES:
        return True

    if normalized_events & ISSUE_UPDATE_VALUES:
        return _updated_fields_include_status(payload) or _changes_include_status(payload)

    return _updated_fields_include_status(payload) or _changes_include_status(payload)


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = payload.get(key)
        if isinstance(fields, str):
            if _is_status_field(fields):
                return True
        elif isinstance(fields, Mapping):
            if any(_is_status_field(field) for field in fields):
                return True
        elif isinstance(fields, list | tuple | set):
            if any(_is_status_field(field) for field in fields):
                return True
    return False


def _changes_include_status(payload: Mapping[str, Any]) -> bool:
    changes = payload.get("changes")
    if not isinstance(changes, Mapping):
        return False

    return any(_is_status_field(field) for field in changes)


def _first_status_value(payloads: list[Mapping[str, Any]]) -> Any:
    for payload in payloads:
        value = _status_from_explicit_fields(payload)
        if value is not None:
            return value

    for payload in payloads:
        value = _status_from_changes(payload)
        if value is not None:
            return value

    for payload in payloads:
        value = _status_from_nested_fields(payload)
        if value is not None:
            return value

    return None


def _status_from_explicit_fields(payload: Mapping[str, Any]) -> Any:
    for key in (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    ):
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _status_from_changes(payload: Mapping[str, Any]) -> Any:
    changes = payload.get("changes")
    if not isinstance(changes, Mapping):
        return None

    for field, change in changes.items():
        if not _is_status_field(field):
            continue
        if isinstance(change, Mapping):
            for key in ("newValue", "new_value", "to", "after", "value", "name"):
                if change.get(key) is not None:
                    return change[key]
        elif change is not None:
            return change
    return None


def _status_from_nested_fields(payload: Mapping[str, Any]) -> Any:
    for key in ("status", "state", "workflowState", "workflow_state"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            for nested_key in ("name", "title", "status", "state"):
                if value.get(nested_key) is not None:
                    return value[nested_key]
        elif value is not None:
            return value
    return None


def _first_text(payloads: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for payload in payloads:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str):
                stripped = value.strip()
                if stripped:
                    return stripped
    return None


def _get_path(value: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = value
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _normalize_event(value: Any) -> str:
    text = _normalize_text(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value or ""))
    text = _normalize_text(text)
    return text


def _normalize_status(value: Any) -> str:
    return _normalize_text(value)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.casefold()


def _is_status_field(value: Any) -> bool:
    return _normalize_text(value).replace(" ", "") in STATUS_FIELDS


def _has_research_prefix(title: str) -> bool:
    return title.lstrip().casefold().startswith(RESEARCH_PREFIX.casefold())


def main() -> int:
    """Read a JSON event from stdin and print the requested update action."""

    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
