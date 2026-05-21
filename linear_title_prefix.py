"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_MARKER = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELDS = ("status", "state", "workflowState")
_STATUS_UPDATE_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    context = _merge_issue_context(event)
    if not _is_status_change_event(context):
        return None

    if _normalize_words(_new_status(context)) != TARGET_STATUS:
        return None

    issue_id = _first_text(context, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(context, ("title", "name"))
    if issue_id is None or title is None:
        return None

    stripped_title = title.strip()
    if _has_title_marker(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_MARKER}: {stripped_title}",
    }


def _merge_issue_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Linear/automation payload shapes into one lookup dict."""

    context: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if isinstance(value, Mapping):
            context.update(value)

    merge(event.get("issue"))
    data = event.get("data")
    if isinstance(data, Mapping):
        merge(data.get("issue"))
        merge(data)
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        merge(trigger_context.get("issue"))
        merge(trigger_context)
    merge(event)

    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    event_tokens = (
        context.get("trigger"),
        context.get("webhookType"),
        context.get("action"),
        context.get("type"),
    )
    normalized_tokens = {_normalize_words(token) for token in event_tokens}

    if "status changed" in normalized_tokens or "status change" in normalized_tokens:
        return True

    if normalized_tokens & {"issue updated", "updated issue", "update", "updated"}:
        updated_fields = context.get("updatedFields") or context.get("updated_fields")
        return _updated_fields_include_status(updated_fields)

    return False


def _updated_fields_include_status(updated_fields: Any) -> bool:
    if isinstance(updated_fields, str):
        fields = [updated_fields]
    elif isinstance(updated_fields, Mapping):
        fields = updated_fields.keys()
    elif isinstance(updated_fields, list | tuple | set):
        fields = updated_fields
    else:
        return False

    return any(_normalize_key(field) in _STATUS_UPDATE_FIELDS for field in fields)


def _new_status(context: Mapping[str, Any]) -> str | None:
    for field in ("newStatus", "new_status", "statusName", "status_name"):
        value = _text(context.get(field))
        if value is not None:
            return value

    for field in _STATUS_FIELDS:
        value = context.get(field)
        if isinstance(value, Mapping):
            name = _text(value.get("name"))
            if name is not None:
                return name
        else:
            text = _text(value)
            if text is not None:
                return text

    return None


def _first_text(context: Mapping[str, Any], fields: tuple[str, ...]) -> str | None:
    for field in fields:
        value = _text(context.get(field))
        if value is not None:
            return value
    return None


def _text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _has_title_marker(title: str) -> bool:
    return title.lower().startswith(TITLE_MARKER.lower())


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9_]", "", str(value).replace("-", "_").lower())


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value))
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
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
