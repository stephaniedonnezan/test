"""Build Linear issue title update actions for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}
_EXPLICIT_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("id", "issueId", "issue_id", "identifier", "key")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue-title update action for qualifying events.

    The function is intentionally side-effect free so it can be used by a webhook
    handler, worker, or the CLI entrypoint below.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_contexts(event))
    if not _is_research_status_change(contexts):
        return None

    issue_id = _first_text(contexts, _ISSUE_ID_KEYS)
    title = _first_text(contexts, ("title", "issueTitle", "issue_title"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility wrapper for snake_case callers."""

    return build_issue_title_update(event)


def handleIssueStatusChanged(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility wrapper for camelCase callers."""

    return build_issue_title_update(event)


def _contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely metadata and issue containers from common webhook shapes."""

    seen: set[int] = set()
    stack: list[Any] = [event]

    while stack:
        value = stack.pop(0)
        if not isinstance(value, Mapping):
            continue
        marker = id(value)
        if marker in seen:
            continue
        seen.add(marker)
        yield value

        for key in ("automation_trigger_info", "triggerContext", "trigger_context", "data", "issue"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                stack.append(nested)


def _is_research_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    status = _changed_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return False

    if _has_direct_status_change_marker(contexts):
        return True

    if _has_generic_update_marker(contexts) and _updated_status_field(contexts):
        return True

    return _has_explicit_new_status(contexts) and not any(_event_markers(contexts))


def _has_direct_status_change_marker(contexts: list[Mapping[str, Any]]) -> bool:
    direct_markers = {
        "status changed",
        "status change",
        "state changed",
        "state change",
        "workflow state changed",
        "workflow state change",
    }
    return any(marker in direct_markers for marker in _event_markers(contexts))


def _has_generic_update_marker(contexts: list[Mapping[str, Any]]) -> bool:
    generic_update_markers = {"update", "updated", "issue update", "issue updated", "updated issue"}
    return any(marker in generic_update_markers for marker in _event_markers(contexts))


def _event_markers(contexts: list[Mapping[str, Any]]) -> Iterable[str]:
    for context in contexts:
        for key in ("trigger", "webhookType", "webhook_type", "action", "type"):
            marker = _extract_text(context.get(key))
            if marker:
                yield _normalize(marker)


def _changed_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in _EXPLICIT_NEW_STATUS_KEYS:
            text = _extract_text(context.get(key))
            if text:
                return text

    for context in contexts:
        text = _extract_text(_changed_field_target(context.get("changes")))
        if text:
            return text

    for context in contexts:
        for key in _STATUS_KEYS:
            text = _extract_text(context.get(key))
            if text:
                return text

    return None


def _has_explicit_new_status(contexts: list[Mapping[str, Any]]) -> bool:
    return any(
        _extract_text(context.get(key))
        for context in contexts
        for key in _EXPLICIT_NEW_STATUS_KEYS
    )


def _updated_status_field(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields", "fields"):
            if any(_normalize(field) in _STATUS_FIELD_NAMES for field in _iter_field_names(context.get(key))):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            if any(_normalize(field) in _STATUS_FIELD_NAMES for field in changes):
                return True
        elif any(_normalize(field) in _STATUS_FIELD_NAMES for field in _iter_field_names(changes)):
            return True

    return False


def _iter_field_names(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
        return

    if not isinstance(value, Iterable) or isinstance(value, (bytes, bytearray, Mapping)):
        return

    for item in value:
        if isinstance(item, str):
            yield item
        elif isinstance(item, Mapping):
            text = _extract_text(item.get("field") or item.get("name") or item.get("key"))
            if text:
                yield text


def _changed_field_target(changes: Any) -> Any:
    if isinstance(changes, Mapping):
        for field_name, change in changes.items():
            if _normalize(field_name) in _STATUS_FIELD_NAMES:
                return _change_target_value(change)
    elif isinstance(changes, Iterable) and not isinstance(changes, (str, bytes, bytearray)):
        for change in changes:
            if not isinstance(change, Mapping):
                continue
            field = change.get("field") or change.get("name") or change.get("key")
            if _normalize(field) in _STATUS_FIELD_NAMES:
                return _change_target_value(change)
    return None


def _change_target_value(change: Any) -> Any:
    if not isinstance(change, Mapping):
        return change

    for key in ("to", "newValue", "new_value", "after", "current"):
        if key in change:
            return change[key]
    return change


def _first_text(contexts: list[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            text = _extract_text(context.get(key))
            if text:
                return text
    return None


def _extract_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if isinstance(value, Mapping):
        for key in ("name", "title", "displayName", "key", "id"):
            text = _extract_text(value.get(key))
            if text:
                return text

    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize(value: Any) -> str:
    text = _extract_text(value)
    if not text:
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
