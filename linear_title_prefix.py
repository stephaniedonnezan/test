"""Build Linear issue title updates for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}
_DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "statuschanged",
    "status change",
    "state changed",
    "workflow state changed",
    "workflowstate changed",
}
_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research.

    The Cursor automation trigger can provide a flat ``triggerContext`` payload,
    while Linear webhooks often nest issue details under ``data.issue``. This
    helper accepts both shapes and returns ``None`` when no title change is
    needed.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _extract_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _extract_first_text(contexts, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event)
    for key in ("triggerContext", "trigger_context", "data", "issue"):
        value = event.get(key)
        add(value)
        if isinstance(value, Mapping):
            for nested_key in ("issue", "data", "triggerContext", "trigger_context"):
                add(value.get(nested_key))

    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = [
        _normalize(context.get(key))
        for context in contexts
        for key in ("trigger", "webhookType", "webhook_type", "action", "type")
    ]

    if any(value in _DIRECT_STATUS_TRIGGERS for value in trigger_values):
        return True

    if any(value in _GENERIC_UPDATE_TRIGGERS for value in trigger_values):
        return _updated_fields_include_status(contexts)

    return False


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
            "fields",
        ):
            if _contains_status_field(context.get(key)):
                return True

        for key in ("changes", "updatedFrom", "updated_from"):
            changes = context.get(key)
            if isinstance(changes, Mapping) and any(
                _normalize(field) in _STATUS_FIELD_NAMES for field in changes
            ):
                return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize(value) in _STATUS_FIELD_NAMES
    if isinstance(value, (list, tuple, set)):
        return any(_contains_status_field(item) for item in value)
    if isinstance(value, Mapping):
        return any(_contains_status_field(item) for item in value.values()) or any(
            _normalize(key) in _STATUS_FIELD_NAMES for key in value
        )
    return False


def _extract_status(contexts: list[Mapping[str, Any]]) -> Any:
    for context in contexts:
        for key in (
            "newStatus",
            "new_status",
            "statusName",
            "status_name",
            "stateName",
            "state_name",
            "workflowStateName",
            "workflow_state_name",
        ):
            if context.get(key):
                return context[key]

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = context.get(key)
            if isinstance(value, Mapping):
                for nested_key in ("name", "title"):
                    if value.get(nested_key):
                        return value[nested_key]
            elif value:
                return value

    return None


def _extract_first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def main() -> int:
    payload = json.load(sys.stdin)
    result = build_issue_title_update(payload)
    if result is not None:
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
