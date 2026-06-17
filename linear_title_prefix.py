"""Build Linear issue title updates for research status transitions.

The automation runtime can pass either the Cursor `triggerContext` shape or a
more direct Linear webhook payload. This module keeps the payload handling small
and deterministic so it can be reused by a thin integration layer.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to to-research.

    The returned shape is intentionally transport-agnostic:
    `{ "action": "update_issue_title", "issueId": "...", "title": "..." }`.
    The caller is responsible for applying the update to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change(contexts):
        return None

    new_status = _new_status(contexts)
    if _normalize_status(new_status) != _normalize_status(TARGET_STATUS):
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(contexts, ("title", "name"))
    if issue_id is None or title is None:
        return None

    if title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely payload contexts from most general to most issue-specific."""

    contexts: list[Mapping[str, Any]] = []

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping) or value in contexts:
            return
        contexts.append(value)
        for key in ("triggerContext", "data", "issue"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                visit(nested)

    visit(event)
    return contexts


def _is_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = []
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            text = _as_text(context.get(key))
            if text:
                trigger_values.append(_normalize_token(text))

    if any(value in {"statuschanged", "statechanged", "workflowstatechanged"} for value in trigger_values):
        return True

    if _updated_status_fields(contexts):
        return True

    return False


def _updated_status_fields(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields", "updatedFrom"):
            if _contains_status_field(context.get(key)):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            if any(_is_status_field(key) for key in changes):
                return True
            if _contains_status_field(changes.get("fields")):
                return True
        elif _contains_status_field(changes):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        return any(_is_status_field(key) or _contains_status_field(item) for key, item in value.items())
    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    text = _as_text(value)
    return text is not None and _normalize_field(text) in STATUS_FIELDS


def _new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        status = _first_text([context], ("newStatus", "new_status", "statusName", "stateName", "workflowStateName"))
        if status:
            return status

    for context in contexts:
        status = _status_from_changes(context.get("changes"))
        if status:
            return status
        status = _status_from_changes(context.get("changedFields"))
        if status:
            return status

    for context in reversed(contexts):
        status = _first_text([context], ("status", "state", "workflowState"))
        if status:
            return status

    return None


def _status_from_changes(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for field in ("status", "state", "workflowState", "workflow_state"):
        status = _status_value(value.get(field))
        if status:
            return status

    for key in ("to", "after", "new", "newValue"):
        status = _status_value(value.get(key))
        if status:
            return status

    return None


def _status_value(value: Any) -> str | None:
    text = _as_text(value)
    if text:
        return text
    if isinstance(value, Mapping):
        return _first_text([value], ("name", "status", "state", "workflowState", "newValue", "to", "after"))
    return None


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _extract_path(context, key)
            text = _as_text(value)
            if text:
                return text
            if isinstance(value, Mapping):
                nested = _first_text([value], ("name", "title", "id", "identifier", "key"))
                if nested:
                    return nested
    return None


def _extract_path(context: Mapping[str, Any], key: str) -> Any:
    if key in context:
        return context[key]

    normalized_key = _normalize_field(key)
    for candidate, value in context.items():
        if _normalize_field(str(candidate)) == normalized_key:
            return value

    return None


def _as_text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, int):
        return str(value)
    return None


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).strip().casefold()
    return re.sub(r"\s+", " ", text) or None


def _normalize_token(value: str) -> str:
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-zA-Z0-9]+", "", text).casefold()


def _normalize_field(value: str) -> str:
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-zA-Z0-9]+", " ", text).strip().casefold()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
