"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"
TITLE_PREFIX_RE = re.compile(rf"^\s*{re.escape(TITLE_PREFIX)}\b", re.IGNORECASE)
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statusupdated",
    "statechanged",
    "workflowstatechanged",
}
GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action when an issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _new_status(contexts)
    if _normalize(status) != _normalize(RESEARCH_STATUS):
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if TITLE_PREFIX_RE.match(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return event, trigger, issue, and change payloads in precedence order."""
    contexts: list[Mapping[str, Any]] = []

    def collect(value: Any) -> None:
        if not isinstance(value, Mapping) or value in contexts:
            return
        contexts.append(value)
        for key in ("triggerContext", "data", "issue", "state", "workflowState", "status"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                collect(nested)
        for key in ("changes", "change", "updatedFrom", "updatedTo"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                collect(nested)

    collect(event)
    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    if _has_direct_status_change_trigger(contexts):
        return True

    if not _has_generic_update_trigger(contexts):
        return False

    return _mentions_status_field(contexts)


def _has_direct_status_change_trigger(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            value = context.get(key)
            if isinstance(value, str) and _normalize(value) in STATUS_CHANGE_TRIGGERS:
                return True
    return False


def _has_generic_update_trigger(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            value = context.get(key)
            if isinstance(value, str) and _normalize(value) in GENERIC_UPDATE_TRIGGERS:
                return True
    return False


def _mentions_status_field(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "changedFields"):
            fields = context.get(key)
            if isinstance(fields, str):
                if _normalize(fields) in STATUS_FIELDS:
                    return True
            elif isinstance(fields, list):
                if any(isinstance(field, str) and _normalize(field) in STATUS_FIELDS for field in fields):
                    return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            for key in changes:
                if isinstance(key, str) and _normalize(key) in STATUS_FIELDS:
                    return True

    return False


def _new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        status = _first_text(
            (context,),
            (
                "newStatus",
                "new_status",
                "statusName",
                "stateName",
                "workflowStateName",
                "toStatus",
                "toState",
            ),
        )
        if status:
            return status

    for context in contexts:
        changes = context.get("changes")
        status = _status_from_changes(changes)
        if status:
            return status

    for context in contexts:
        for key in ("status", "state", "workflowState"):
            value = context.get(key)
            status = _text_or_name(value)
            if status:
                return status

    return None


def _status_from_changes(changes: Any) -> str | None:
    if not isinstance(changes, Mapping):
        return None

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = changes.get(key)
        if isinstance(value, Mapping):
            status = _first_text((value,), ("newValue", "new", "to", "name"))
            if status:
                return status
            after = value.get("after")
            status = _text_or_name(after)
            if status:
                return status
        else:
            status = _text_or_name(value)
            if status:
                return status

    return None


def _first_text(contexts: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, Mapping):
        return _first_text((value,), ("name", "title", "value"))
    return None


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    with_spaces = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[^a-z0-9]+", "", with_spaces.casefold())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
