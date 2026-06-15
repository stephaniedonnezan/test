"""Build title update actions for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any

TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"

_STATUS_FIELDS = {
    "status",
    "state",
    "workflowstate",
    "workflow_state",
    "stateid",
    "state_id",
    "workflowstateid",
    "workflow_state_id",
}
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "toStatus",
    "to_status",
    "targetStatus",
    "target_status",
)
_CURRENT_STATUS_KEYS = (
    "status",
    "state",
    "workflowState",
    "workflow_state",
)
_CHANGE_DESTINATION_KEYS = (
    "to",
    "new",
    "after",
    "current",
    "value",
)


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when an issue status changes to research.

    The automation runtime supplies a compact ``triggerContext`` payload, while
    direct Linear webhooks often nest issue fields under ``data.issue``. This
    function accepts both shapes and returns a declarative action for the caller
    to apply.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_contexts(event))
    if not _is_status_change(event, contexts):
        return None

    new_status = _extract_new_status(event, contexts)
    if _normalize_words(new_status) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely metadata and issue maps in precedence order."""

    seen: set[int] = set()

    def emit(value: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            yield value

    for item in (
        event.get("triggerContext"),
        event.get("data", {}).get("issue") if isinstance(event.get("data"), Mapping) else None,
        event.get("issue"),
        event.get("data"),
        event,
    ):
        yield from emit(item)


def _is_status_change(event: Mapping[str, Any], contexts: Iterable[Mapping[str, Any]]) -> bool:
    if _has_direct_status_change_marker(contexts):
        return True
    return _has_changed_status_field(event)


def _has_direct_status_change_marker(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type", "eventType", "triggerType"):
            marker = _normalize_words(context.get(key))
            if marker in {"status changed", "status change", "state changed", "workflow state changed"}:
                return True
            if "status changed" in marker or "state changed" in marker:
                return True
    return False


def _has_changed_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized_key = _normalize_key(key)
            if normalized_key in {"updatedfields", "changedfields"}:
                if _contains_status_field(item):
                    return True
            if normalized_key in {"changes", "changed", "updatedfrom", "previousvalues"}:
                if _changes_include_status(item):
                    return True
            if isinstance(item, (Mapping, list, tuple)) and _has_changed_status_field(item):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_has_changed_status_field(item) for item in value)
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_key(value) in _STATUS_FIELDS
    if isinstance(value, Mapping):
        return any(_normalize_key(key) in _STATUS_FIELDS for key in value)
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _changes_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        if any(_normalize_key(key) in _STATUS_FIELDS for key in value):
            return True
        field_name = value.get("field") or value.get("fieldName") or value.get("name")
        if _normalize_key(field_name) in _STATUS_FIELDS:
            return True
        return any(_changes_include_status(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_changes_include_status(item) for item in value)
    return False


def _extract_new_status(event: Mapping[str, Any], contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in _NEW_STATUS_KEYS:
            status = _status_text(context.get(key))
            if status:
                return status

    status = _status_from_changes(event)
    if status:
        return status

    for context in contexts:
        for key in _CURRENT_STATUS_KEYS:
            status = _status_text(context.get(key))
            if status:
                return status
    return None


def _status_from_changes(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _normalize_key(key) in {"changes", "changed"}:
                status = _status_from_change_payload(item)
                if status:
                    return status
            status = _status_from_changes(item)
            if status:
                return status
    elif isinstance(value, (list, tuple)):
        for item in value:
            status = _status_from_changes(item)
            if status:
                return status
    return None


def _status_from_change_payload(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _normalize_key(key) in _STATUS_FIELDS:
                status = _status_destination(item)
                if status:
                    return status
        field_name = value.get("field") or value.get("fieldName") or value.get("name")
        if _normalize_key(field_name) in _STATUS_FIELDS:
            status = _status_destination(value)
            if status:
                return status
        for item in value.values():
            status = _status_from_change_payload(item)
            if status:
                return status
    elif isinstance(value, (list, tuple)):
        for item in value:
            status = _status_from_change_payload(item)
            if status:
                return status
    return None


def _status_destination(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in _CHANGE_DESTINATION_KEYS:
            status = _status_text(value.get(key))
            if status:
                return status
    return _status_text(value)


def _status_text(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state", "workflowState"):
            text = _status_text(value.get(key))
            if text:
                return text
    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = re.sub(r"[_\-/]+", " ", value)
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value)
    return " ".join(value.lower().split())


def _normalize_key(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def main() -> int:
    """Read an event JSON object from stdin and print the update action."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print(json.dumps({"error": f"invalid JSON: {error.msg}"}), file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
