"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELDS = ("newStatus", "new_status", "status", "state", "workflowState")
ISSUE_ID_FIELDS = ("id", "issueId", "issue_id", "identifier")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action when the issue enters research.

    The handler accepts Cursor automation trigger payloads as well as common
    nested Linear webhook payloads. It intentionally returns a declarative
    action object so the caller can perform the actual Linear mutation.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_context_stack(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _first_status(contexts)
    if _normalize_text(new_status) != RESEARCH_STATUS:
        return None

    issue_id = _first_string(contexts, ISSUE_ID_FIELDS)
    title = _first_string(contexts, ("title",))
    if issue_id is None or title is None:
        return None

    stripped_title = title.strip()
    if _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _context_stack(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield payload contexts from most specific metadata to issue data."""

    trigger_context = _mapping_value(event, "triggerContext")
    if trigger_context is not None:
        yield trigger_context

    yield event

    data = _mapping_value(event, "data")
    if data is not None:
        yield data

    issue = _mapping_value(event, "issue")
    if issue is not None:
        yield issue

    if data is not None:
        issue_from_data = _mapping_value(data, "issue")
        if issue_from_data is not None:
            yield issue_from_data


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    direct_event_names: list[str] = []
    updated_fields: list[str] = []

    for context in contexts:
        for field in ("trigger", "event", "eventType", "webhookType"):
            value = context.get(field)
            if isinstance(value, str):
                direct_event_names.append(value)

        action = context.get("action")
        if isinstance(action, str):
            direct_event_names.append(action)

        updated_fields.extend(_string_list(context.get("updatedFields")))
        updated_fields.extend(_string_list(context.get("updated_fields")))

    normalized_event_names = {_normalize_text(value) for value in direct_event_names}
    if "status changed" in normalized_event_names:
        return True

    if normalized_event_names.intersection({"update", "updated", "issue updated", "updated issue"}):
        normalized_fields = {_normalize_text(field) for field in updated_fields}
        return bool(normalized_fields.intersection({"status", "state", "workflow state"}))

    return False


def _first_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for field in STATUS_FIELDS:
            value = context.get(field)
            if isinstance(value, str) and value.strip():
                return value
            if isinstance(value, Mapping):
                name = value.get("name")
                if isinstance(name, str) and name.strip():
                    return name
    return None


def _first_string(contexts: Iterable[Mapping[str, Any]], fields: Iterable[str]) -> str | None:
    for context in contexts:
        for field in fields:
            value = context.get(field)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _mapping_value(context: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    value = context.get(key)
    if isinstance(value, Mapping):
        return value
    return None


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""

    with_camel_spacing = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", with_camel_spacing).lower().split()
    return " ".join(words)


def _has_research_prefix(title: str) -> bool:
    return _normalize_text(title).startswith(_normalize_text(TITLE_PREFIX))


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
