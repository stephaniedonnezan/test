"""Build Linear issue title updates for Cursor research automations.

The automation is triggered by Linear issue status changes. When an issue is
moved into the "to research" workflow state, the returned action asks the
caller to prefix the issue title with "Cursor researching".
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
ACTION = "update_issue_title"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action for Linear issues moved to to-research."""

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    if not _is_status_change(payload):
        return None

    new_status = _extract_new_status(payload)
    if _normalize_value(new_status) != TARGET_STATUS:
        return None

    issue_id = _clean_text(_first_value(payload, ("issueId", "issue_id", "identifier", "key", "id")))
    title = _clean_text(_first_value(payload, ("title", "name")))
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor/Linear payload containers into one lookup map."""

    flattened: dict[str, Any] = {}

    for container_name in ("issue", "data", "triggerContext"):
        container = event.get(container_name)
        if isinstance(container, Mapping):
            flattened.update(_flatten_event(container))

    if isinstance(event.get("data"), Mapping):
        data = event["data"]
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            flattened.update(_flatten_event(issue))

    if isinstance(event.get("triggerContext"), Mapping):
        context = event["triggerContext"]
        issue = context.get("issue")
        if isinstance(issue, Mapping):
            flattened.update(_flatten_event(issue))

    flattened.update(event)
    return flattened


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    ]
    normalized_triggers = {_normalize_value(value) for value in trigger_values}

    if any(value in {"status changed", "status change", "statuschanged"} for value in normalized_triggers):
        return True

    if any(value in {"issue updated", "updated issue", "update", "issue update"} for value in normalized_triggers):
        return _status_field_was_updated(payload)

    return False


def _status_field_was_updated(payload: Mapping[str, Any]) -> bool:
    updated_fields = payload.get("updatedFields") or payload.get("updated_fields")
    if _contains_status_field(updated_fields):
        return True

    changes = payload.get("changes") or payload.get("changed")
    if isinstance(changes, Mapping):
        return any(_is_status_field_name(key) for key in changes)
    if _contains_status_field(changes):
        return True

    updated_from = payload.get("updatedFrom") or payload.get("updated_from")
    if isinstance(updated_from, Mapping):
        return any(_is_status_field_name(key) for key in updated_from)

    return False


def _extract_new_status(payload: Mapping[str, Any]) -> Any:
    for key in (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
    ):
        value = payload.get(key)
        if value is not None:
            return _status_name(value)

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            if key in changes:
                value = changes[key]
                if isinstance(value, Mapping):
                    return _status_name(
                        value.get("new")
                        or value.get("to")
                        or value.get("after")
                        or value.get("newValue")
                        or value.get("new_value")
                        or value.get("name")
                    )
                return _status_name(value)

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = payload.get(key)
        if value is not None:
            return _status_name(value)

    return None


def _first_value(payload: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _status_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "label", "status", "state", "workflowState"):
            nested = value.get(key)
            if nested is not None:
                return _status_name(nested)
    return value


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) for key in value)
    if isinstance(value, (list, tuple, set)):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_value(value)
    return normalized.replace(" ", "") in STATUS_FIELDS


def _normalize_value(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-\s]+", " ", text)
    return text.casefold()


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": f"invalid JSON: {exc.msg}"}), file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
