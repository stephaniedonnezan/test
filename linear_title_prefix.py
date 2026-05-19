"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    context = _merged_context(event)
    if not _is_status_change_event(context):
        return None

    status = _new_status(context)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(context, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(context, ("title", "name"))
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _merged_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common automation and Linear webhook payload shapes."""
    contexts: list[Mapping[str, Any]] = []

    trigger_context = _mapping_value(event, "triggerContext")
    data = _mapping_value(event, "data")
    top_level_issue = _mapping_value(event, "issue")
    data_issue = _mapping_value(data, "issue") if data else None

    # Issue data is intentionally lower precedence than trigger metadata because
    # nested issue objects can contain the old status in update webhooks.
    for candidate in (data_issue, top_level_issue, data, trigger_context, event):
        if candidate is not None:
            contexts.append(candidate)

    merged: dict[str, Any] = {}
    for context in contexts:
        merged.update(context)

    return merged


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        context.get("trigger"),
        context.get("webhookType"),
        context.get("action"),
        context.get("type"),
    ]
    normalized_values = {_normalize_text(value) for value in trigger_values if value}

    if any(value in {"status changed", "status change"} for value in normalized_values):
        return True

    if "issue updated" in normalized_values or "updated issue" in normalized_values or "update" in normalized_values:
        return _updated_status_fields(context)

    return False


def _updated_status_fields(context: Mapping[str, Any]) -> bool:
    fields = (
        context.get("updatedFields")
        or context.get("updated_fields")
        or context.get("changedFields")
        or context.get("changed_fields")
    )

    if isinstance(fields, str):
        candidates = [fields]
    elif isinstance(fields, Mapping):
        candidates = list(fields.keys())
    elif isinstance(fields, list | tuple | set):
        candidates = list(fields)
    else:
        return False

    return any(_normalize_key(field) in STATUS_FIELD_NAMES for field in candidates)


def _new_status(context: Mapping[str, Any]) -> str | None:
    explicit = _first_text(context, ("newStatus", "new_status", "statusName", "status_name"))
    if explicit:
        return explicit

    for field in ("status", "state", "workflowState", "workflow_state"):
        value = context.get(field)
        if isinstance(value, Mapping):
            name = _first_text(value, ("name", "title"))
            if name:
                return name
        elif isinstance(value, str):
            text = value.strip()
            if text:
                return text

    return None


def _mapping_value(mapping: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if not isinstance(mapping, Mapping):
        return None
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else None


def _first_text(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text
        elif value is not None and not isinstance(value, Mapping):
            text = str(value).strip()
            if text:
                return text
    return None


def _has_prefix(title: str) -> bool:
    return title.strip().lower().startswith(PREFIX.lower())


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _camel_to_words(str(value)).lower())


def _normalize_text(value: Any) -> str:
    words = _camel_to_words(str(value))
    return re.sub(r"[^a-z0-9]+", " ", words.lower()).strip()


def _camel_to_words(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
