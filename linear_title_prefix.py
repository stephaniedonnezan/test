"""Build Linear issue title updates for research-status automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    The Cursor automation trigger provides a flat ``triggerContext`` object,
    while Linear webhooks are often nested under ``data.issue``. This function
    accepts both shapes and returns ``None`` for events that should be ignored.
    """

    if not isinstance(event, Mapping):
        return None

    containers = _event_containers(event)
    if not _is_status_change_event(containers):
        return None

    new_status = _first_status(containers)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(containers, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(containers, ("title", "name"))
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        updated_title = title
    else:
        updated_title = f"{PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": updated_title,
    }


def _event_containers(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return event dictionaries from most-specific trigger data to issue data."""

    containers: list[Mapping[str, Any]] = [event]

    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            containers.append(value)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        for key in ("data", "issue"):
            value = trigger_context.get(key)
            if isinstance(value, Mapping):
                containers.append(value)

    data = event.get("data")
    if isinstance(data, Mapping):
        for key in ("issue", "state", "workflowState"):
            value = data.get(key)
            if isinstance(value, Mapping):
                containers.append(value)

    issue = data.get("issue") if isinstance(data, Mapping) else None
    if isinstance(issue, Mapping):
        for key in ("state", "workflowState"):
            value = issue.get(key)
            if isinstance(value, Mapping):
                containers.append(value)

    return _dedupe_mappings(containers)


def _dedupe_mappings(containers: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    deduped: list[Mapping[str, Any]] = []
    seen: set[int] = set()
    for container in containers:
        marker = id(container)
        if marker not in seen:
            seen.add(marker)
            deduped.append(container)
    return deduped


def _is_status_change_event(containers: list[Mapping[str, Any]]) -> bool:
    event_names = [
        value
        for container in containers
        for key in ("trigger", "webhookType", "action", "type", "event")
        if (value := container.get(key)) is not None
    ]

    if any(_is_direct_status_change_name(value) for value in event_names):
        return True

    if any(_normalize(value) in {"update", "updated", "issue update", "issue updated", "updated issue"} for value in event_names):
        return _updated_fields_include_status(containers) or _changes_include_status(containers)

    return False


def _is_direct_status_change_name(value: Any) -> bool:
    normalized = _normalize(value)
    compact = normalized.replace(" ", "")
    return compact in {
        "statuschanged",
        "statuschange",
        "workflowstatechanged",
        "statechanged",
    }


def _updated_fields_include_status(containers: list[Mapping[str, Any]]) -> bool:
    for container in containers:
        updated_fields = container.get("updatedFields") or container.get("updated_fields")
        if isinstance(updated_fields, Mapping):
            field_names = updated_fields.keys()
        elif isinstance(updated_fields, list | tuple | set):
            field_names = updated_fields
        else:
            continue

        if any(_field_is_status(field_name) for field_name in field_names):
            return True
    return False


def _changes_include_status(containers: list[Mapping[str, Any]]) -> bool:
    for container in containers:
        changes = container.get("changes") or container.get("changed")
        if not isinstance(changes, Mapping):
            continue

        if any(_field_is_status(field_name) for field_name in changes.keys()):
            return True
    return False


def _field_is_status(field_name: Any) -> bool:
    return _normalize(field_name).replace(" ", "") in STATUS_FIELD_NAMES


def _first_status(containers: list[Mapping[str, Any]]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "statusName",
        "status_name",
        "workflowStateName",
        "workflow_state_name",
    ):
        value = _first_text(containers, (key,))
        if value:
            return value

    for container in containers:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = container.get(key)
            text = _text_or_name(value)
            if text:
                return text

    return None


def _first_text(containers: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for container in containers:
        for key in keys:
            value = container.get(key)
            text = _text_or_name(value)
            if text:
                return text
    return None


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "id", "identifier"):
            text = _text_or_name(value.get(key))
            if text:
                return text

    return None


def _normalize(value: Any) -> str:
    text = _text_or_name(value) or ""
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def main() -> int:
    """Read an event JSON object from stdin and print the update action."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
