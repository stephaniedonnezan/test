"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflowstatus"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    status = _new_status(context)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _issue_id(context)
    title = _issue_title(context)
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Cursor/Linear webhook shapes without losing outer metadata."""
    context: dict[str, Any] = {}

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        context.update(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        context.update({key: value for key, value in data.items() if key not in context})
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            context.update({key: value for key, value in issue.items() if key not in context})

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        context.update({key: value for key, value in issue.items() if key not in context})

    issue_id = _extract_issue_id(event)
    title = _extract_issue_title(event)
    context.update(event)
    context.pop("triggerContext", None)
    if issue_id:
        context["_issueId"] = issue_id
    if title:
        context["_issueTitle"] = title
    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    event_names = [
        context.get("trigger"),
        context.get("webhookType"),
        context.get("action"),
        context.get("type"),
    ]
    normalized_names = {_normalize_token(name) for name in event_names if name is not None}

    if normalized_names.intersection({"statuschanged", "statuschange", "issuestatuschanged"}):
        return True

    if normalized_names.intersection({"issueupdated", "updatedissue", "update", "updated"}):
        return _changed_status_fields(context)

    return False


def _changed_status_fields(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields"):
        fields = context.get(key)
        if isinstance(fields, list | tuple | set):
            if any(_is_status_field(field) for field in fields):
                return True
        elif _is_status_field(fields):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_is_status_field(field) for field in changes)

    return False


def _new_status(context: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "statusName",
        "status_name",
    ):
        value = _text_or_name(context.get(key))
        if value:
            return value

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for field, change in changes.items():
            if _is_status_field(field):
                value = _change_target(change)
                if value:
                    return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _text_or_name(context.get(key))
        if value:
            return value

    return None


def _change_target(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("to", "toValue", "newValue", "after", "value", "name"):
            value = _text_or_name(change.get(key))
            if value:
                return value
    return _text_or_name(change)


def _issue_id(context: Mapping[str, Any]) -> str | None:
    for key in ("_issueId", "issueId", "issue_id", "identifier", "key", "id"):
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _issue_title(context: Mapping[str, Any]) -> str | None:
    for key in ("_issueTitle", "title"):
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, Mapping):
        name = value.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None


def _is_status_field(field: Any) -> bool:
    normalized = _normalize_token(field)
    return normalized in STATUS_FIELDS


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    normalized = re.sub(r"[_\-\s]+", " ", spaced).strip().casefold()
    return normalized or None


def _normalize_token(value: Any) -> str | None:
    normalized = _normalize_text(value)
    if normalized is None:
        return None
    return normalized.replace(" ", "")


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    data = event.get("data")
    issue = event.get("issue")
    nested_issue = data.get("issue") if isinstance(data, Mapping) else None

    sources = [
        event.get("triggerContext"),
        nested_issue,
        issue,
        data,
    ]
    if not any(isinstance(source, Mapping) for source in (data, nested_issue, issue)):
        sources.append(event)

    for source in sources:
        if not isinstance(source, Mapping):
            continue
        for key in ("issueId", "issue_id", "identifier", "key", "id"):
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _extract_issue_title(event: Mapping[str, Any]) -> str | None:
    data = event.get("data")
    issue = event.get("issue")
    nested_issue = data.get("issue") if isinstance(data, Mapping) else None

    for source in (event.get("triggerContext"), nested_issue, issue, data, event):
        if not isinstance(source, Mapping):
            continue
        value = source.get("title")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
