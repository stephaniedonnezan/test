"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    containers = _candidate_containers(event)
    if not _is_status_change_event(containers):
        return None

    status = _extract_new_status(containers)
    if _normalize(status) != _normalize(TARGET_STATUS):
        return None

    issue_id = _extract_issue_id(containers)
    title = _extract_title(containers)
    if not issue_id or not title or _already_prefixed(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _candidate_containers(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    containers: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            containers.append(value)

    add(event)
    for key in ("triggerContext", "trigger_context", "webhook", "payload"):
        add(event.get(key))

    # Prefer direct trigger context values before nested Linear issue data.
    for parent in tuple(containers):
        for key in ("issue", "data"):
            add(parent.get(key))
            nested = parent.get(key)
            if isinstance(nested, Mapping):
                add(nested.get("issue"))

    return containers


def _is_status_change_event(containers: Iterable[Mapping[str, Any]]) -> bool:
    items = list(containers)
    event_texts = [
        _normalize(container.get(key))
        for container in items
        for key in ("trigger", "action", "type", "webhookType", "webhook_type", "event")
    ]

    if any("status" in text and ("change" in text or "changed" in text) for text in event_texts):
        return True

    update_event = any(text in {"update", "updated", "issue update", "issue updated", "updated issue"} for text in event_texts)
    return update_event and _changed_fields_include_status(items)


def _changed_fields_include_status(containers: Iterable[Mapping[str, Any]]) -> bool:
    for container in containers:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            value = container.get(key)
            if _field_collection_includes_status(value):
                return True

        changes = container.get("changes")
        if isinstance(changes, Mapping):
            if any(_normalize(key) in STATUS_FIELD_NAMES for key in changes):
                return True
        elif _field_collection_includes_status(changes):
            return True

    return False


def _field_collection_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize(value) in STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        return any(_normalize(key) in STATUS_FIELD_NAMES for key in value)
    if isinstance(value, Iterable):
        return any(_field_collection_includes_status(item) for item in value)
    return False


def _extract_new_status(containers: Iterable[Mapping[str, Any]]) -> str | None:
    items = list(containers)
    explicit_status_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    status = _first_text(items, explicit_status_keys)
    if status:
        return status

    status = _status_from_changes(items)
    if status:
        return status

    return _first_text(items, ("status", "state", "workflowState", "workflow_state"))


def _status_from_changes(containers: Iterable[Mapping[str, Any]]) -> str | None:
    for container in containers:
        changes = container.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for key, value in changes.items():
            if _normalize(key) in STATUS_FIELD_NAMES:
                changed_value = _status_from_changed_value(value)
                if changed_value:
                    return changed_value

    return None


def _status_from_changed_value(value: Any) -> str | None:
    if isinstance(value, str):
        return _clean(value)
    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "after", "to", "current", "name", "title"):
            text = _text_from_value(value.get(key))
            if text:
                return text
    return None


def _extract_issue_id(containers: Iterable[Mapping[str, Any]]) -> str | None:
    return _first_text(containers, ("issueId", "issue_id", "identifier", "key", "id"))


def _extract_title(containers: Iterable[Mapping[str, Any]]) -> str | None:
    return _first_text(containers, ("title",))


def _first_text(containers: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for container in containers:
        for key in keys:
            text = _text_from_value(container.get(key))
            if text:
                return text
    return None


def _text_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        return _clean(value)
    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "id"):
            text = _text_from_value(value.get(key))
            if text:
                return text
    return None


def _clean(value: str) -> str | None:
    cleaned = value.strip()
    return cleaned or None


def _already_prefixed(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(build_issue_title_update(event), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
