"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type", "event", "eventType")
_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}
_STATUS_CHANGE_TOKENS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_UPDATE_TOKENS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_NESTED_CONTEXT_KEYS = ("triggerContext", "data", "issue", "payload", "webhook", "resource")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "id", "identifier", "key")
_TITLE_KEYS = ("title",)
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "statusName",
    "status_name",
    "newState",
    "new_state",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_DIRECT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_CHANGE_KEYS = (
    "changes",
    "changed",
    "updated",
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
    "updatedFrom",
    "previousValues",
)
_NEW_VALUE_KEYS = ("to", "new", "after", "current", "newValue", "new_value", "value")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    candidates = list(_iter_contexts(event))
    if not _is_status_change(candidates):
        return None

    status = _extract_new_status(candidates)
    if _normalize_label(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(candidates, _ISSUE_ID_KEYS)
    title = _first_text(candidates, _TITLE_KEYS)
    if issue_id is None or title is None:
        return None

    title = title.strip()
    if not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _iter_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    stack: list[Mapping[str, Any]] = [event]
    seen: set[int] = set()

    while stack:
        current = stack.pop()
        current_id = id(current)
        if current_id in seen:
            continue
        seen.add(current_id)
        yield current

        for key in reversed(_NESTED_CONTEXT_KEYS):
            value = current.get(key)
            if isinstance(value, Mapping):
                stack.append(value)


def _is_status_change(candidates: Iterable[Mapping[str, Any]]) -> bool:
    has_update_trigger = False

    for candidate in candidates:
        for key in _TRIGGER_KEYS:
            token = _normalize_label(candidate.get(key))
            if not token:
                continue
            if _is_direct_status_change_token(token):
                return True
            if token in _UPDATE_TOKENS:
                has_update_trigger = True

    candidate_list = list(candidates)
    has_status_change_fields = any(_changed_fields_include_status(candidate) for candidate in candidate_list)
    return has_status_change_fields and (has_update_trigger or not any(_trigger_values(candidate) for candidate in candidate_list))


def _trigger_values(candidate: Mapping[str, Any]) -> list[Any]:
    return [candidate[key] for key in _TRIGGER_KEYS if key in candidate]


def _is_direct_status_change_token(token: str) -> bool:
    return token in _STATUS_CHANGE_TOKENS or any(token.endswith(f" {suffix}") for suffix in _STATUS_CHANGE_TOKENS)


def _changed_fields_include_status(candidate: Mapping[str, Any]) -> bool:
    for key in _CHANGE_KEYS:
        if key not in candidate:
            continue
        if _value_mentions_status_field(candidate[key]):
            return True
    return False


def _value_mentions_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in _STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        return any(_normalize_field_name(key) in _STATUS_FIELD_NAMES for key in value.keys())
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_value_mentions_status_field(item) for item in value)
    return False


def _extract_new_status(candidates: Iterable[Mapping[str, Any]]) -> str | None:
    candidate_list = list(candidates)

    for candidate in candidate_list:
        for key in _EXPLICIT_STATUS_KEYS:
            status = _status_text(candidate.get(key))
            if status is not None:
                return status

    for candidate in candidate_list:
        status = _status_from_changes(candidate)
        if status is not None:
            return status

    for candidate in candidate_list:
        for key in _DIRECT_STATUS_KEYS:
            status = _status_text(candidate.get(key))
            if status is not None:
                return status

    return None


def _status_from_changes(candidate: Mapping[str, Any]) -> str | None:
    for key in ("changes", "changed", "updated"):
        value = candidate.get(key)
        if not isinstance(value, Mapping):
            continue
        for status_key, change in value.items():
            if _normalize_field_name(status_key) not in _STATUS_FIELD_NAMES:
                continue
            status = _new_status_from_change(change)
            if status is not None:
                return status
    return None


def _new_status_from_change(change: Any) -> str | None:
    if not isinstance(change, Mapping):
        return _status_text(change)

    for key in _NEW_VALUE_KEYS:
        status = _status_text(change.get(key))
        if status is not None:
            return status

    return _status_text(change)


def _status_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _text(value.get(key))
            if text is not None:
                return text
        return None
    return _text(value)


def _first_text(candidates: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for candidate in candidates:
        for key in keys:
            text = _text(candidate.get(key))
            if text is not None and text.strip():
                return text
    return None


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_label(value: Any) -> str:
    text = _text(value)
    if text is None:
        return ""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text.strip())
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def _normalize_field_name(value: Any) -> str:
    return _normalize_label(value).replace(" ", "")


def main() -> int:
    """Read a JSON event from stdin and print the update action, if any."""

    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
