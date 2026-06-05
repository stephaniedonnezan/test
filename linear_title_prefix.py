"""Build Linear issue-title updates for issues moved to To Research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}

_DIRECT_STATUS_CHANGE_MARKERS = {
    "statuschange",
    "statuschanged",
    "statechange",
    "statechanged",
    "workflowstatechange",
    "workflowstatechanged",
}

_UPDATE_MARKERS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}

_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "statusName",
    "stateName",
    "workflowStateName",
)

_CURRENT_STATUS_KEYS = (
    "status",
    "state",
    "workflowState",
    "workflow_state",
)

_ISSUE_ID_KEYS = (
    "issueId",
    "issue_id",
    "identifier",
    "key",
    "id",
)


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue moves to To Research.

    The Cursor automation trigger uses a compact ``triggerContext`` payload,
    while Linear webhooks commonly wrap issue details in ``data`` or ``issue``.
    This function accepts both without depending on a particular transport.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _find_new_status(contexts)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    title = _find_first_text(contexts, ("title",))
    issue_id = _find_first_text(contexts, _ISSUE_ID_KEYS)
    if not title or not issue_id:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{RESEARCH_PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Any) -> dict[str, str] | None:
    """Compatibility wrapper for status-change automation entrypoints."""

    return build_issue_title_update(event)


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and id(value) not in seen:
            contexts.append(value)
            seen.add(id(value))

    add(event)

    for key in ("triggerContext", "trigger_context", "issue", "data"):
        add(event.get(key))

    for context in list(contexts):
        for key in ("issue", "data"):
            add(context.get(key))

    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    markers = list(_event_markers(contexts))
    if any(_compact(marker) in _DIRECT_STATUS_CHANGE_MARKERS for marker in markers):
        return True

    if _has_status_field_evidence(contexts):
        return True

    return any(_compact(marker) in _UPDATE_MARKERS for marker in markers) and _has_status_field_evidence(contexts)


def _event_markers(contexts: list[Mapping[str, Any]]) -> list[str]:
    markers: list[str] = []
    for context in contexts:
        for key in ("trigger", "event", "eventType", "type", "action", "webhookType"):
            value = context.get(key)
            if isinstance(value, str):
                markers.append(value)
    return markers


def _has_status_field_evidence(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(context.get(key)):
                return True

        for key in ("changes", "change", "updatedFrom", "updated_from"):
            value = context.get(key)
            if isinstance(value, Mapping) and any(_is_status_field_name(field) for field in value):
                return True

        changed_field = context.get("changedField") or context.get("field")
        if _is_status_field_name(changed_field):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Mapping):
        return any(
            _is_status_field_name(item)
            for item in (value.get("field"), value.get("name"), *value.keys())
        )

    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)

    return False


def _is_status_field_name(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return _compact(value) in _STATUS_FIELD_NAMES


def _find_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for key in _EXPLICIT_STATUS_KEYS:
        status = _find_status_value(contexts, key)
        if status:
            return status

    status = _find_status_from_changes(contexts)
    if status:
        return status

    for key in _CURRENT_STATUS_KEYS:
        status = _find_status_value(contexts, key)
        if status:
            return status

    return None


def _find_status_value(contexts: list[Mapping[str, Any]], key: str) -> str | None:
    for context in contexts:
        if key in context:
            status = _status_to_text(context[key])
            if status:
                return status
    return None


def _find_status_from_changes(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        changes = context.get("changes") or context.get("change")
        if not isinstance(changes, Mapping):
            continue

        for key, value in changes.items():
            if not _is_status_field_name(key):
                continue
            status = _status_after_change(value)
            if status:
                return status

    return None


def _status_after_change(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return _status_to_text(value)

    for key in ("to", "new", "after", "current", "value"):
        if key in value:
            status = _status_to_text(value[key])
            if status:
                return status

    return None


def _status_to_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state"):
            status = _status_to_text(value.get(key))
            if status:
                return status

    return None


def _find_first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        for context in contexts:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _has_research_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(RESEARCH_PREFIX)}\b", title, flags=re.IGNORECASE) is not None


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = re.sub(r"[_\-/]+", " ", value)
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value)
    return " ".join(value.casefold().split())


def _compact(value: str) -> str:
    normalized = _normalize_text(value)
    return "" if normalized is None else normalized.replace(" ", "")


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is None:
        print("null")
    else:
        print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
