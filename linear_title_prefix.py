"""Build Linear issue title update actions for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_CHANGE_FIELD_NAMES = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}
_STATUS_VALUE_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when an issue moves to the research status.

    The function accepts the flat Cursor automation trigger context as well as
    the nested payload shapes commonly used by Linear webhooks.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_candidate_contexts(event))
    if not _is_status_change(contexts):
        return None

    status = _find_new_status(contexts)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _find_issue_id(contexts)
    title = _first_text(contexts, ("title", "issueTitle", "issue_title", "name"))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if _has_research_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{RESEARCH_PREFIX}: {clean_title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely metadata and issue containers from outermost to innermost."""

    seen: set[int] = set()

    def walk(value: Any) -> Iterable[Mapping[str, Any]]:
        if not isinstance(value, Mapping):
            return
        identity = id(value)
        if identity in seen:
            return
        seen.add(identity)
        yield value

        for key in (
            "triggerContext",
            "context",
            "payload",
            "data",
            "issue",
            "node",
            "object",
            "resource",
        ):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                yield from walk(nested)

    yield from walk(event)


def _is_status_change(contexts: Iterable[Mapping[str, Any]]) -> bool:
    contexts = list(contexts)
    has_non_status_trigger = False

    for context in contexts:
        for key in ("trigger", "event", "eventType", "webhookType", "action", "type"):
            normalized = _normalize_text(context.get(key))
            if normalized in {
                "status changed",
                "status change",
                "state changed",
                "state change",
                "workflow state changed",
                "workflow state change",
            }:
                return True
            if normalized and normalized not in {"linear", "issue", "update", "updated"}:
                has_non_status_trigger = True

    if _has_changed_status_field(contexts):
        return True

    # A dedicated "new status" field is only present on status transition
    # payloads in Cursor automations. Do not let it override an explicit
    # non-status trigger such as comment_created.
    if has_non_status_trigger:
        return False

    return any(
        _first_text((context,), ("newStatus", "new_status", "newState", "new_state"))
        for context in contexts
    )


def _has_changed_status_field(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "changedFields"):
            if _contains_status_field(context.get(key)):
                return True

        for key in ("changes", "updatedFrom", "updated_from"):
            value = context.get(key)
            if isinstance(value, Mapping) and any(
                _normalize_key(changed_key) in _STATUS_CHANGE_FIELD_NAMES
                for changed_key in value.keys()
            ):
                return True

        if _normalize_text(context.get("action")) == "update" and _contains_status_field(
            context.get("field")
        ):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_key(value) in _STATUS_CHANGE_FIELD_NAMES
    if isinstance(value, Mapping):
        field_name = _first_text((value,), ("field", "fieldName", "name", "key"))
        return bool(field_name and _normalize_key(field_name) in _STATUS_CHANGE_FIELD_NAMES)
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
        return any(_contains_status_field(item) for item in value)
    return False


def _find_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    contexts = list(contexts)

    for context in contexts:
        status = _status_from_changes(context.get("changes"))
        if status:
            return status
        status = _status_from_changes(context.get("changedFields"))
        if status:
            return status

    status = _first_text(
        contexts,
        (
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
        ),
    )
    if status:
        return status

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _status_value(context.get(key))
            if status:
                return status

    return None


def _status_from_changes(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, changed_value in value.items():
            field_name = _normalize_key(key)
            if field_name not in _STATUS_CHANGE_FIELD_NAMES:
                continue
            status = (
                _status_value(changed_value)
                if field_name in _STATUS_VALUE_FIELD_NAMES
                else _status_name_from_mapping(changed_value)
            )
            if status:
                return status
        return None

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for item in value:
            if isinstance(item, Mapping):
                field_name = _first_text((item,), ("field", "fieldName", "name", "key"))
                normalized_field_name = _normalize_key(field_name)
                if normalized_field_name in _STATUS_CHANGE_FIELD_NAMES:
                    status = (
                        _status_value(item)
                        if normalized_field_name in _STATUS_VALUE_FIELD_NAMES
                        else _status_name_from_mapping(item)
                    )
                    if status:
                        return status

    return None


def _find_issue_id(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    contexts = list(contexts)
    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key"))
    return issue_id or _first_text(contexts, ("id",))


def _status_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None

    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "to", "after", "value"):
            status = _status_value(value.get(key))
            if status:
                return status
        return _status_name_from_mapping(value)

    return None


def _status_name_from_mapping(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None
    return _first_text(
        (value,),
        (
            "newValueName",
            "new_value_name",
            "toName",
            "to_name",
            "afterName",
            "after_name",
            "name",
            "title",
            "label",
        ),
    )


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    keys = tuple(keys)
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
            if isinstance(value, (int, float)):
                return str(value)
    return None


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^a-zA-Z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", words)


def _normalize_key(value: Any) -> str:
    return _normalize_text(value).replace(" ", "")


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(RESEARCH_PREFIX.lower())


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
