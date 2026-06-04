"""Build Linear issue title updates for issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_ISSUE_ID_KEYS = ("id", "issueId", "issue_id", "identifier")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    The automation can receive either a flat trigger context or a nested Linear
    webhook payload. This function keeps the output intentionally small so the
    caller can decide how to apply the returned update action.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_mapping_contexts(event))
    if not _is_status_change_to_research(contexts):
        return None

    issue_id = _first_text(contexts, _ISSUE_ID_KEYS)
    title = _first_text(contexts, ("title", "name"))
    if issue_id is None or title is None:
        return None

    trimmed_title = title.strip()
    if not trimmed_title or _has_research_prefix(trimmed_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {trimmed_title}",
    }


def _is_status_change_to_research(contexts: list[Mapping[str, Any]]) -> bool:
    return _is_status_change_event(contexts) and _new_status(contexts) == TARGET_STATUS


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    event_names = {
        normalized
        for context in contexts
        for key in ("trigger", "webhookType", "eventType", "action", "type")
        if (normalized := _normalize(context.get(key)))
    }

    if any(_is_status_changed_name(name) for name in event_names):
        return True

    if any(name in {"update", "issue update", "issue updated", "updated issue"} for name in event_names):
        return _updated_fields_include_status(contexts)

    return False


def _is_status_changed_name(name: str) -> bool:
    return name in {
        "status changed",
        "status change",
        "state changed",
        "state change",
        "workflow state changed",
        "workflow state change",
    }


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = context.get(key)
            if isinstance(fields, str):
                field_values: Iterable[Any] = [fields]
            elif isinstance(fields, Iterable) and not isinstance(fields, (bytes, Mapping)):
                field_values = fields
            else:
                continue

            for field in field_values:
                if _normalize(field) in _STATUS_FIELDS:
                    return True

    return False


def _new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for key in _EXPLICIT_STATUS_KEYS:
        value = _first_text(contexts, (key,))
        if value is not None:
            return _normalize(value)

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = context.get(key)
            if isinstance(value, Mapping):
                name = _text(value.get("name"))
                if name is not None:
                    return _normalize(name)
            else:
                text = _text(value)
                if text is not None:
                    return _normalize(text)

    return None


def _mapping_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def add(value: Any) -> None:
        if not isinstance(value, Mapping) or id(value) in seen:
            return
        seen.add(id(value))
        contexts.append(value)
        for key in ("triggerContext", "data", "issue", "payload", "webhook"):
            add(value.get(key))

    add(event)
    return contexts


def _first_text(contexts: list[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            text = _text(context.get(key))
            if text is not None:
                return text
    return None


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize(value: Any) -> str | None:
    text = _text(value)
    if text is None:
        return None

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split()) or None


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
