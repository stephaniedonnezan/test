"""Build Linear issue-title update actions for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_IDENTITY_KEYS = {"id", "issueId", "issue_id", "identifier", "key", "title"}
_CONTAINER_KEYS = {"automation_trigger_info", "triggerContext", "data", "issue"}
_STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
    "workflowstatus",
}
_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
    "issue status changed",
    "issue status change",
    "issue state changed",
    "issue state change",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action when an issue enters research."""

    if not isinstance(event, Mapping):
        return None

    for context in _candidate_contexts(event):
        if not _is_status_change_event(context):
            continue

        status = _changed_status(context)
        if _normalize_text(status) != TARGET_STATUS:
            continue

        issue_id = _first_text(context, ("issueId", "issue_id", "id", "identifier", "key"))
        title = _first_text(context, ("title",))
        if not issue_id or not title or _has_prefix(title):
            continue

        clean_title = title.strip()
        return {
            "action": "update_issue_title",
            "issueId": issue_id.strip(),
            "title": f"{PREFIX}: {clean_title}",
        }

    return None


def _candidate_contexts(event: Mapping[str, Any]) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    roots = [event]

    automation_context = event.get("automation_trigger_info")
    if isinstance(automation_context, Mapping):
        roots.append(automation_context)

    for root in roots:
        contexts.extend(_contexts_for_root(root))

    return contexts


def _contexts_for_root(root: Mapping[str, Any]) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    root_meta = _metadata(root)

    trigger_context = root.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        contexts.append({**root_meta, **trigger_context})

    data = root.get("data")
    if isinstance(data, Mapping):
        data_meta = {**root_meta, **_metadata(data)}
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            contexts.append({**data_meta, **issue})
        contexts.append({**data_meta, **data})

    issue = root.get("issue")
    if isinstance(issue, Mapping):
        contexts.append({**root_meta, **issue})

    contexts.append(dict(root))
    return contexts


def _metadata(mapping: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in mapping.items()
        if key not in _IDENTITY_KEYS and key not in _CONTAINER_KEYS
    }


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    event_names = [
        _normalize_text(context.get(key))
        for key in ("trigger", "webhookType", "action", "type")
    ]

    if any(name in _DIRECT_STATUS_CHANGE_EVENTS for name in event_names):
        return True

    if any(name in _GENERIC_UPDATE_EVENTS for name in event_names):
        return _updated_status_fields(context)

    return False


def _updated_status_fields(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if _contains_status_field(context.get(key)):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_is_status_field(field) for field in changes.keys())

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        return any(
            _is_status_field(key) or _contains_status_field(item)
            for key, item in value.items()
        )

    if isinstance(value, (list, tuple, set)):
        return any(_contains_status_field(item) for item in value)

    return False


def _is_status_field(value: Any) -> bool:
    return _normalize_compact(value) in _STATUS_FIELD_NAMES


def _changed_status(context: Mapping[str, Any]) -> Any:
    for key in (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
    ):
        if key in context:
            return _status_name(context[key])

    status_from_changes = _status_from_changes(context.get("changes"))
    if status_from_changes is not None:
        return status_from_changes

    for key in ("status", "state", "workflowState", "workflow_state"):
        if key in context:
            return _status_name(context[key])

    return None


def _status_from_changes(changes: Any) -> Any:
    if not isinstance(changes, Mapping):
        return None

    for field, change in changes.items():
        if not _is_status_field(field):
            continue
        if isinstance(change, Mapping):
            for key in (
                "newValue",
                "new_value",
                "new",
                "to",
                "after",
                "value",
                "name",
            ):
                if key in change:
                    return _status_name(change[key])
        return _status_name(change)

    return None


def _status_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value"):
            if key in value:
                return _status_name(value[key])
    return value


def _first_text(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(PREFIX)}\b", title, flags=re.IGNORECASE) is not None


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = _status_name(value)
    if text is None:
        return ""
    text = str(text).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _normalize_compact(value: Any) -> str:
    return _normalize_text(value).replace(" ", "")


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
