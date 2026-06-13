"""Build title updates for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    contexts = _payload_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _extract_new_status(contexts)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(contexts, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _payload_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")

    # Prefer explicit automation metadata over nested issue data.
    add(trigger_context)
    add(event)
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))
    add(issue)
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("issue"))

    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    contexts = list(contexts)
    for context in contexts:
        for key in ("trigger", "event", "eventType", "webhookType", "action", "type"):
            if _normalize_event_name(context.get(key)) in {
                "statuschanged",
                "issuestatuschanged",
                "statechanged",
                "workflowstatechanged",
            }:
                return True

    has_update_event = any(_is_update_event(context) for context in contexts)
    return has_update_event and _updated_status_fields_present(contexts)


def _is_update_event(context: Mapping[str, Any]) -> bool:
    for key in ("trigger", "event", "eventType", "action", "type"):
        normalized = _normalize_event_name(context.get(key))
        if normalized in {"update", "updated", "issueupdated", "updatedissue"}:
            return True
    return False


def _updated_status_fields_present(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(context.get(key)):
                return True
        updated_from = context.get("updatedFrom") or context.get("updated_from")
        if isinstance(updated_from, Mapping) and _contains_status_field(updated_from.keys()):
            return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_event_name(value) in _STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        return any(_contains_status_field(key) for key in value)
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    contexts = list(contexts)

    explicit_status = _first_text(
        contexts,
        ("newStatus", "new_status", "newState", "new_state", "toStatus", "to_status"),
    )
    if explicit_status:
        return explicit_status

    direct_status = _first_text(contexts, ("status",))
    if direct_status:
        return direct_status

    for context in contexts:
        for key in ("state", "workflowState", "workflow_state", "status"):
            value = context.get(key)
            if isinstance(value, Mapping):
                name = _text(value.get("name")) or _text(value.get("title"))
                if name:
                    return name
            text = _text(value)
            if text:
                return text
    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _text(context.get(key))
            if value:
                return value
    return None


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _normalize_words(value: str | None) -> str | None:
    if value is None:
        return None
    camel_spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", camel_spaced).strip().lower()
    return re.sub(r"\s+", " ", normalized)


def _normalize_event_name(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    return re.sub(r"[^a-z0-9]+", "", _normalize_words(text) or "")


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if not update:
        return 1

    print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
