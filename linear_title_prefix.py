"""Build Linear issue title updates for research-status transitions.

The automation runner can call :func:`build_issue_title_update` with either the
flat Cursor trigger payload or a nested Linear webhook payload. The function is
side-effect free: it returns the update action the runner should apply, or
``None`` when the event is not relevant.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_TOKENS = {
    "statuschange",
    "statuschanged",
    "statusupdate",
    "statusupdated",
    "statechange",
    "statechanged",
    "workflowstatechange",
    "workflowstatechanged",
}

_GENERIC_UPDATE_TOKENS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}

_STATUS_FIELD_TOKENS = {
    "status",
    "state",
    "workflowstate",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update when an issue moves to "to research".

    The returned dictionary is intentionally simple so automation glue can turn
    it into the corresponding Linear API call:

    ``{"action": "update_issue_title", "issueId": "POI-123", "title": "..."}``
    """

    if not isinstance(event, Mapping):
        return None

    payload = _unwrap_trigger_context(event)
    issue = _extract_issue(payload)

    if not _is_status_change_event(payload):
        return None

    new_status = _extract_new_status(payload)
    if _normalize_phrase(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_text(payload, issue, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _extract_text(issue, payload, ("title",))
    if issue_id is None or title is None:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _unwrap_trigger_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        merged = dict(trigger_context)
        for key, value in event.items():
            if key != "triggerContext":
                merged[key] = value
        return merged
    return event


def _extract_issue(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    for path in (
        ("issue",),
        ("data", "issue"),
        ("data",),
        ("node",),
        ("entity",),
    ):
        value = _nested_mapping(payload, path)
        if _looks_like_issue(value):
            return value
    return payload


def _looks_like_issue(value: Mapping[str, Any] | None) -> bool:
    if value is None:
        return False
    return any(key in value for key in ("title", "identifier", "issueId", "issue_id", "key", "id"))


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_tokens = {
        _compact_token(value)
        for key in ("trigger", "webhookType", "webhook_type", "action", "type")
        for value in _values_for_key(payload, key)
    }
    trigger_tokens.discard("")

    if any(_is_direct_status_change_token(token) for token in trigger_tokens):
        return True

    if any(token in _GENERIC_UPDATE_TOKENS for token in trigger_tokens):
        return _updated_fields_include_status(payload) or _updated_from_include_status(payload)

    return False


def _is_direct_status_change_token(token: str) -> bool:
    if token in _DIRECT_STATUS_CHANGE_TOKENS:
        return True
    return "status" in token and ("change" in token or "update" in token)


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        for value in _values_for_key(payload, key):
            if _field_names_include_status(value):
                return True

    for key in ("changes", "changed", "updates"):
        for value in _values_for_key(payload, key):
            if _changes_include_status(value):
                return True

    return False


def _updated_from_include_status(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFrom", "updated_from", "previousValues", "previous_values"):
        for value in _values_for_key(payload, key):
            if _changes_include_status(value):
                return True
    return False


def _field_names_include_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value)
    if isinstance(value, Iterable):
        return any(_field_names_include_status(item) for item in value)
    return False


def _changes_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if _is_status_field(key):
                return True
            if isinstance(nested_value, Mapping) and _changes_include_status(nested_value):
                return True
        return False
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_changes_include_status(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    return _compact_token(value) in _STATUS_FIELD_TOKENS


def _extract_new_status(payload: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
    ):
        value = _first_value_for_key(payload, key)
        text = _status_text(value)
        if text:
            return text

    for container_key in ("changes", "changed", "updates"):
        for changes in _values_for_key(payload, container_key):
            text = _new_status_from_changes(changes)
            if text:
                return text

    issue = _extract_issue(payload)
    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _first_value_for_key(issue, key)
        text = _status_text(value)
        if text:
            return text

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _first_value_for_key(payload, key)
        text = _status_text(value)
        if text:
            return text

    return None


def _new_status_from_changes(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for key, change in value.items():
        if not _is_status_field(key):
            continue

        if isinstance(change, Mapping):
            for new_key in ("newValue", "new_value", "to", "after", "value", "name"):
                text = _status_text(change.get(new_key))
                if text:
                    return text
        else:
            text = _status_text(change)
            if text:
                return text

    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _status_text(value.get(key))
            if text:
                return text
    return None


def _extract_text(
    primary: Mapping[str, Any],
    secondary: Mapping[str, Any],
    keys: tuple[str, ...],
) -> str | None:
    for source in (primary, secondary):
        for key in keys:
            value = _first_value_for_key(source, key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _first_value_for_key(mapping: Mapping[str, Any], requested_key: str) -> Any:
    for value in _values_for_key(mapping, requested_key):
        return value
    return None


def _values_for_key(mapping: Mapping[str, Any], requested_key: str) -> Iterable[Any]:
    requested = _compact_token(requested_key)
    for key, value in mapping.items():
        if _compact_token(key) == requested:
            yield value


def _nested_mapping(mapping: Mapping[str, Any], path: tuple[str, ...]) -> Mapping[str, Any] | None:
    current: Any = mapping
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = _first_value_for_key(current, key)
    return current if isinstance(current, Mapping) else None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_phrase(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    with_spaces = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", with_spaces).casefold()
    return " ".join(normalized.split())


def _compact_token(value: Any) -> str:
    return _normalize_phrase(str(value) if value is not None else "").replace(" ", "")


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON input: {exc}", file=sys.stderr)
        return 1

    result = build_issue_title_update(event)
    if result is not None:
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
