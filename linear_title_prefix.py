"""Build Linear issue title updates for Cursor research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGE_FIELDS = {"status", "state", "workflowstate", "workflow_status"}
TRIGGER_FIELDS = ("trigger", "webhookType", "action", "type")
EXPLICIT_STATUS_FIELDS = ("newStatus", "new_status", "newState", "new_state")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue moves to research.

    The handler accepts both Cursor's flat automation trigger context and common
    nested Linear webhook payloads. It intentionally returns a data object instead
    of calling Linear directly so the surrounding automation can decide how to
    execute side effects.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _first_explicit_new_status(contexts) or _first_fallback_status(contexts)
    if _normalize_text(new_status) != _normalize_text(TARGET_STATUS):
        return None

    issue = _issue_context(contexts)
    issue_id = _clean_string(_first_value(issue, ("id", "issueId", "issue_id", "identifier")))
    title = _clean_string(_first_value(issue, ("title", "name")))
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {"action": "update_issue_title", "issueId": issue_id, "title": f"{TITLE_PREFIX}: {title}"}


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = [event]

    for key in ("triggerContext", "data", "issue", "state", "workflowState", "status"):
        value = event.get(key)
        if isinstance(value, Mapping):
            contexts.extend(_contexts(value))

    return _dedupe_contexts(contexts)


def _dedupe_contexts(contexts: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    seen: set[int] = set()
    unique: list[Mapping[str, Any]] = []
    for context in contexts:
        identity = id(context)
        if identity not in seen:
            seen.add(identity)
            unique.append(context)
    return unique


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    updated_fields_present = False

    for context in contexts:
        for field in TRIGGER_FIELDS:
            trigger = _normalize_text(context.get(field))
            if trigger in {"statuschanged", "statuschange", "statusupdated", "statusupdate"}:
                return True
            if trigger in {"issueupdated", "updatedissue", "update", "updated"}:
                updated_fields_present = True

        updated_fields = context.get("updatedFields") or context.get("updated_fields")
        changed_fields = context.get("changedFields") or context.get("changed_fields")
        if _contains_status_field(updated_fields) or _contains_status_field(changed_fields):
            updated_fields_present = True

    return updated_fields_present


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_text(value) in STATUS_CHANGE_FIELDS

    if isinstance(value, Mapping):
        return any(_contains_status_field(key) for key in value.keys())

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _first_explicit_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        value = _first_value(context, EXPLICIT_STATUS_FIELDS)
        if value is not None:
            return _clean_string(value)
    return None


def _first_fallback_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = context.get(key)
            if isinstance(value, Mapping):
                name = _first_value(value, ("name", "title"))
                if name is not None:
                    return _clean_string(name)
            elif value is not None:
                return _clean_string(value)
    return None


def _issue_context(contexts: Iterable[Mapping[str, Any]]) -> Mapping[str, Any]:
    for context in contexts:
        issue = context.get("issue")
        if isinstance(issue, Mapping):
            return issue

    for context in contexts:
        if _first_value(context, ("id", "issueId", "issue_id", "identifier")) is not None:
            return context

    return {}


def _first_value(context: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = context.get(key)
        if value is not None:
            return value
    return None


def _clean_string(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _normalize_text(value: Any) -> str:
    text = _clean_string(value)
    if not text:
        return ""
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    return re.sub(r"[^a-z0-9]+", "", words.lower())


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def main() -> int:
    """Read a JSON event from stdin and print the computed action, if any."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
