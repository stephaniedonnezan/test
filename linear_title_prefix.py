"""Build Linear issue title updates for Cursor research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update when a Linear issue enters research status."""

    if not isinstance(event, Mapping):
        return None

    context = _payload_context(event)
    if not _is_status_change(context):
        return None

    new_status = _extract_new_status(context)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(context, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(context, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _payload_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor and Linear webhook nesting into one lookup context."""

    context: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if isinstance(value, Mapping):
            context.update(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue_from_data = data.get("issue") if isinstance(data, Mapping) else None

    merge(issue_from_data)
    merge(data)
    merge(trigger_context)
    merge(event)

    return context


def _is_status_change(context: Mapping[str, Any]) -> bool:
    trigger_values = _trigger_values(context)
    if any(_compact_words(value).endswith("statuschanged") for value in trigger_values):
        return True
    if any(_compact_words(value).endswith("statechanged") for value in trigger_values):
        return True

    if not any(_compact_words(value) in {"update", "updated", "issueupdated", "updatedissue"} for value in trigger_values):
        return False

    updated_fields = context.get("updatedFields") or context.get("updated_fields")
    if _contains_status_field(updated_fields):
        return True

    changes = context.get("changes") or context.get("changed")
    if isinstance(changes, Mapping):
        return any(_field_name_is_status(key) for key in changes)

    return False


def _trigger_values(context: Mapping[str, Any]) -> list[Any]:
    return [
        context.get("trigger"),
        context.get("webhookType"),
        context.get("action"),
        context.get("type"),
        context.get("eventType"),
        context.get("event_type"),
    ]


def _extract_new_status(context: Mapping[str, Any]) -> str:
    for key in ("newStatus", "new_status", "toStatus", "to_status", "statusName", "status_name"):
        text = _text(context.get(key))
        if text:
            return text

    changes = context.get("changes") or context.get("changed")
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _field_name_is_status(key):
                text = _status_from_change(value)
                if text:
                    return text

    for key in ("status", "state", "workflowState", "workflow_state"):
        text = _status_text(context.get(key))
        if text:
            return text

    return ""


def _status_from_change(value: Any) -> str:
    if isinstance(value, Mapping):
        for key in ("to", "new", "after", "toValue", "newValue"):
            text = _status_text(value.get(key))
            if text:
                return text

    return _status_text(value)


def _status_text(value: Any) -> str:
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state", "label"):
            text = _text(value.get(key))
            if text:
                return text

    return _text(value)


def _first_text(context: Mapping[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        text = _text(context.get(key))
        if text:
            return text
    return ""


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _field_name_is_status(value)
    if isinstance(value, (list, tuple, set)):
        return any(_contains_status_field(item) for item in value)
    if isinstance(value, Mapping):
        return any(_field_name_is_status(key) or _contains_status_field(item) for key, item in value.items())
    return False


def _field_name_is_status(name: Any) -> bool:
    return _compact_words(name) in STATUS_FIELDS


def _normalize_words(value: Any) -> str:
    text = _text(value)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).strip().lower()
    return re.sub(r"\s+", " ", text)


def _compact_words(value: Any) -> str:
    return _normalize_words(value).replace(" ", "")


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
