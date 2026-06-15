"""Build title updates for Linear issues entering research status.

The automation receives slightly different payload shapes depending on whether
the event comes from Cursor's trigger wrapper or directly from Linear.  This
module keeps the public behavior small: return an issue-title update action
only when an issue status changes to "to research".
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}
STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statuschanged",
    "statusupdated",
    "statusupdate",
}
ISSUE_UPDATE_TRIGGERS = {
    "issueupdated",
    "updatedissue",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue-title update action for to-research transitions.

    The returned action is intentionally data-only so the caller can decide how
    to execute it against Linear.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _new_status(contexts)
    if _normalize_status(new_status) != _normalize_status(TARGET_STATUS):
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely context mappings from outermost to innermost payloads."""

    contexts: list[Mapping[str, Any]] = []

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        contexts.append(value)
        for key in ("triggerContext", "data", "issue", "node", "object"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                visit(nested)

    visit(event)
    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values: list[str] = []
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            text = _text(context.get(key))
            if text:
                trigger_values.append(text)

    normalized_triggers = {_normalize_token(value) for value in trigger_values}
    if normalized_triggers & STATUS_CHANGE_TRIGGERS:
        return True

    if normalized_triggers & ISSUE_UPDATE_TRIGGERS:
        return _updated_fields_include_status(contexts) or _changes_include_status(contexts)

    return False


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        updated_fields = context.get("updatedFields")
        if isinstance(updated_fields, str):
            fields: tuple[Any, ...] = (updated_fields,)
        elif isinstance(updated_fields, (list, tuple, set)):
            fields = tuple(updated_fields)
        else:
            fields = ()

        for field in fields:
            if _normalize_field_name(field) in STATUS_FIELD_NAMES:
                return True

    return False


def _changes_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        changes = context.get("changes")
        if not isinstance(changes, Mapping):
            continue
        for field in changes:
            if _normalize_field_name(field) in STATUS_FIELD_NAMES:
                return True
    return False


def _new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    explicit_value = _first_status_value(contexts, explicit_keys)
    if explicit_value:
        return explicit_value

    changed_status = _status_from_changes(contexts)
    if changed_status:
        return changed_status

    return _first_status_value(contexts, ("status", "state", "workflowState", "workflow_state"))


def _status_from_changes(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        changes = context.get("changes")
        if not isinstance(changes, Mapping):
            continue
        for field, change in changes.items():
            if _normalize_field_name(field) not in STATUS_FIELD_NAMES:
                continue
            if isinstance(change, Mapping):
                for key in ("to", "new", "after", "newValue", "new_value"):
                    status = _status_text(change.get(key))
                    if status:
                        return status
            status = _status_text(change)
            if status:
                return status
    return None


def _first_status_value(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            if key not in context:
                continue
            status = _status_text(context.get(key))
            if status:
                return status
    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _text(value.get("name") or value.get("title") or value.get("label"))
    return _text(value)


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            text = _text(context.get(key))
            if text:
                return text
    return None


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _has_research_prefix(title: str) -> bool:
    return title.strip().lower().startswith(TITLE_PREFIX.lower())


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _split_words(value)
    return " ".join(normalized)


def _normalize_token(value: str) -> str:
    return "".join(_split_words(value))


def _normalize_field_name(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    return _normalize_token(text)


def _split_words(value: str) -> list[str]:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    return [word.lower() for word in re.split(r"[^A-Za-z0-9]+", spaced) if word]


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
