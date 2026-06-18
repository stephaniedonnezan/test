"""Build issue title update actions for Linear research-status webhooks.

The automation host is responsible for applying the returned action to Linear.
This module keeps the decision small and testable: only status changes moving an
issue to "to research" should receive the Cursor research title prefix.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflow state", "workflowstate"}
DIRECT_STATUS_TRIGGERS = {"status changed", "status change"}
GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue-title update action, or ``None`` when inapplicable."""

    if not isinstance(event, Mapping):
        return None

    contexts = _collect_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(contexts, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _collect_contexts(root: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect likely webhook envelopes and nested issue objects in priority order."""

    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def add(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        value_id = id(value)
        if value_id in seen:
            return
        seen.add(value_id)
        contexts.append(value)
        for key in ("triggerContext", "payload", "data", "issue", "node"):
            add(value.get(key))

    add(root)
    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    has_generic_update = False

    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type", "eventType"):
            marker = _normalize(context.get(key))
            if not marker:
                continue
            if marker in DIRECT_STATUS_TRIGGERS or "status changed" in marker:
                return True
            if marker in GENERIC_UPDATE_TRIGGERS:
                has_generic_update = True

    return has_generic_update and _changed_status_fields(contexts)


def _changed_status_fields(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "changedFields", "changes"):
            if _contains_status_field(context.get(key)):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize(value) in STATUS_FIELDS
    if isinstance(value, Mapping):
        return any(
            _normalize(key) in STATUS_FIELDS or _normalize(item) in STATUS_FIELDS
            for key, item in value.items()
        )
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        return any(_contains_status_field(item) for item in value)
    return False


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    contexts = list(contexts)
    explicit_keys = (
        "newStatus",
        "new_status",
        "newStatusName",
        "new_status_name",
        "statusName",
        "status_name",
        "newState",
        "new_state",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    status_keys = ("status", "state", "workflowState", "workflow_state")

    status = _first_text(contexts, explicit_keys)
    if status:
        return status

    status = _extract_changed_status(contexts)
    if status:
        return status

    return _first_text(contexts, status_keys)


def _extract_changed_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for container_key in ("changes", "updatedFields", "changedFields"):
            container = context.get(container_key)
            status = _extract_status_from_change_container(container)
            if status:
                return status
    return None


def _extract_status_from_change_container(container: Any) -> str | None:
    if isinstance(container, Mapping):
        for key, value in container.items():
            if _normalize(key) in STATUS_FIELDS:
                return _extract_status_value(value)
    if isinstance(container, Iterable) and not isinstance(container, (str, bytes, bytearray)):
        for item in container:
            if isinstance(item, Mapping):
                field = _first_text([item], ("field", "name", "key"))
                if field and _normalize(field) in STATUS_FIELDS:
                    return _extract_status_value(item)
    return None


def _extract_status_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "new", "after", "newValue", "value", "name"):
            text = _coerce_text(value.get(key))
            if text:
                return text
        for key in ("state", "status", "workflowState"):
            text = _coerce_text(value.get(key))
            if text:
                return text
    return _coerce_text(value)


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            text = _coerce_text(context.get(key))
            if text:
                return text
    return None


def _coerce_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "id", "key"):
            text = _coerce_text(value.get(key))
            if text:
                return text
    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize(value: Any) -> str:
    text = _coerce_text(value)
    if not text:
        return ""
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    """Read a JSON event from stdin and print the update action or ``null``."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    print(json.dumps(action, sort_keys=True) if action else "null")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
