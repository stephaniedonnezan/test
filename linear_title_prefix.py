"""Build a Linear issue title update for issues moved to research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    if not _is_status_change(event, payload):
        return None

    status = _extract_status(payload)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    issue_id = _clean_text(_first_value(payload, ("issueId", "issue_id", "id", "identifier", "key")))
    title = _clean_text(_first_value(payload, ("title", "name")))
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        updated_title = title
    else:
        updated_title = f"{PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": updated_title,
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Collect useful fields from common Cursor and Linear webhook shapes."""
    flattened: dict[str, Any] = {}

    for key in ("issue", "data", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            flattened.update(_flatten_event(value))

    if isinstance(event.get("state"), Mapping):
        flattened.setdefault("state", event["state"])
        flattened.setdefault("stateName", event["state"].get("name"))

    if isinstance(event.get("workflowState"), Mapping):
        flattened.setdefault("workflowState", event["workflowState"])
        flattened.setdefault("workflowStateName", event["workflowState"].get("name"))

    flattened.update(event)
    return flattened


def _is_status_change(event: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
    event_names = [
        _normalize_words(value)
        for value in _collect_values(event, ("trigger", "webhookType", "action", "type"))
        if _clean_text(value)
    ]

    if any(name in {"status changed", "status change", "state changed", "workflow state changed"} for name in event_names):
        return True

    if any(name in {"issue updated", "updated issue", "update", "updated"} for name in event_names):
        return _updated_fields_include_status(payload)

    return False


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    values = _first_value(payload, ("updatedFields", "updated_fields", "changedFields", "changed_fields"))
    if values is None:
        changes = _first_value(payload, ("changes", "changed"))
        if isinstance(changes, Mapping):
            values = changes.keys()

    if isinstance(values, str):
        field_names = [values]
    elif isinstance(values, Mapping):
        field_names = values.keys()
    elif isinstance(values, (list, tuple, set)):
        field_names = values
    else:
        return False

    normalized_fields = {_normalize_words(field) for field in field_names}
    return bool(normalized_fields & STATUS_FIELD_NAMES)


def _extract_status(payload: Mapping[str, Any]) -> Any:
    for key in (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
        "status",
        "state",
        "workflowState",
    ):
        value = payload.get(key)
        if isinstance(value, Mapping):
            value = _first_value(value, ("name", "title", "key", "id"))
        if _clean_text(value):
            return value
    return None


def _collect_values(value: Any, keys: tuple[str, ...]) -> list[Any]:
    if not isinstance(value, Mapping):
        return []

    matches: list[Any] = []
    for key, nested_value in value.items():
        if key in keys:
            matches.append(nested_value)
        if isinstance(nested_value, Mapping):
            matches.extend(_collect_values(nested_value, keys))
    return matches


def _first_value(payload: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _clean_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _normalize_words(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
