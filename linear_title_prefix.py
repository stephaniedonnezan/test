"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action for issues moved to To Research."""
    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalized_status(_new_status(event)) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(event, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(event, ("title", "issueTitle", "issue_title"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{RESEARCH_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    markers = [
        _normalized_marker(value)
        for context in _context_mappings(event)
        for key in ("trigger", "webhookType", "action", "type")
        if (value := context.get(key)) is not None
    ]

    if any(marker in {"statuschanged", "statechanged", "workflowstatechanged"} for marker in markers):
        return True

    generic_update_markers = {"update", "updated", "issueupdated", "updatedissue"}
    if any(marker in generic_update_markers for marker in markers):
        return _mentions_status_field(event)

    return False


def _mentions_status_field(event: Mapping[str, Any]) -> bool:
    saw_updated_fields = False
    for field in _updated_fields(event):
        saw_updated_fields = True
        if _normalized_field(field) in STATUS_FIELDS:
            return True

    saw_changes = False
    for context in _context_mappings(event):
        changes = context.get("changes") or context.get("changedFields")
        if isinstance(changes, Mapping):
            saw_changes = True
            if any(_normalized_field(field) in STATUS_FIELDS for field in changes):
                return True

    if saw_updated_fields or saw_changes:
        return False

    return any(
        context.get(key) is not None
        for context in _context_mappings(event)
        for key in ("newStatus", "new_status", "newState", "new_state", "toStatus", "targetStatus")
    )


def _new_status(event: Mapping[str, Any]) -> Any:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "toStatus",
        "targetStatus",
    )
    for context in _context_mappings(event):
        for key in explicit_keys:
            if key in context:
                return context[key]

    for context in _context_mappings(event):
        changes = context.get("changes") or context.get("changedFields")
        if not isinstance(changes, Mapping):
            continue

        for field, change in changes.items():
            if _normalized_field(field) not in STATUS_FIELDS:
                continue

            if isinstance(change, Mapping):
                for key in ("to", "new", "after", "current"):
                    if key in change:
                        return change[key]
            return change

    for context in _context_mappings(event):
        for key in ("status", "state", "workflowState", "workflow_state"):
            if key in context:
                return context[key]

    return None


def _updated_fields(event: Mapping[str, Any]) -> Iterable[Any]:
    for context in _context_mappings(event):
        fields = context.get("updatedFields") or context.get("updated_fields")
        if isinstance(fields, str):
            yield fields
        elif isinstance(fields, Iterable):
            for field in fields:
                if isinstance(field, Mapping):
                    yield field.get("name") or field.get("field") or field.get("key")
                else:
                    yield field


def _context_mappings(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield trigger_context

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            yield issue
        yield data

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue

    yield event


def _first_text(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for context in _context_mappings(event):
        for key in keys:
            value = context.get(key)
            if isinstance(value, str):
                value = value.strip()
                if value:
                    return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(RESEARCH_PREFIX.lower())


def _normalized_status(value: Any) -> str | None:
    text = _status_text(value)
    if text is None:
        return None
    return _normalized_words(text)


def _status_text(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, str):
        return value

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "status", "state", "workflowState", "value"):
            text = _status_text(value.get(key))
            if text:
                return text
        return None

    return str(value)


def _normalized_marker(value: Any) -> str:
    text = _status_text(value)
    if text is None:
        return ""
    return re.sub(r"[^a-z0-9]+", "", _normalized_words(text) or "")


def _normalized_field(value: Any) -> str:
    text = _status_text(value)
    if text is None:
        return ""
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _normalized_words(value: str) -> str:
    split_camel = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", split_camel).strip().lower()
    return " ".join(words.split())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
