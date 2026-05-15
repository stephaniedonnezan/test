"""Build Linear issue title updates for research status changes.

The automation host can pass slightly different webhook shapes depending on
where the event originated.  This module keeps the public behavior small:
return an issue title update only when a Linear issue status changes to
"to research".
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action for Linear "to research" status changes."""
    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_label(new_status) != "to research":
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_issue_title(event)
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_research_prefix(stripped_title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    for context in _iter_mappings(event):
        for key in ("trigger", "event", "eventType", "event_type"):
            if _normalize_label(context.get(key)) in {
                "status changed",
                "status change",
                "state changed",
                "workflow state changed",
            }:
                return True

        for key in ("action", "type", "webhookType", "webhook_type"):
            event_type = _normalize_label(context.get(key))
            if event_type in {"issue updated", "updated issue", "update"}:
                if _updated_fields_include_status(context):
                    return True

    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        updated_fields = context.get(key)
        if _field_collection_includes_status(updated_fields):
            return True

    changes = context.get("changes") or context.get("updated")
    return _field_collection_includes_status(changes)


def _field_collection_includes_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_normalize_label(key) in _STATUS_FIELD_NAMES for key in value.keys())

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_normalize_label(item) in _STATUS_FIELD_NAMES for item in value)

    return _normalize_label(value) in _STATUS_FIELD_NAMES


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "toStatus",
        "to_status",
    )

    for context in _iter_mappings(event):
        status = _first_text_value(context, explicit_keys)
        if status:
            return status

    fallback_keys = ("status", "state", "workflowState", "workflow_state")
    for context in _iter_mappings(event):
        status = _first_text_value(context, fallback_keys)
        if status:
            return status

    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for context in _iter_issue_contexts(event):
        issue_id = _first_text_value(context, ("id", "issueId", "issue_id", "identifier"))
        if issue_id:
            return issue_id.strip()

    return None


def _extract_issue_title(event: Mapping[str, Any]) -> str | None:
    for context in _iter_issue_contexts(event):
        title = _first_text_value(context, ("title",))
        if title and title.strip():
            return title

    return None


def _iter_issue_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    yield event

    for key in ("triggerContext", "trigger_context", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            yield value

    for key in ("data", "payload"):
        value = event.get(key)
        if not isinstance(value, Mapping):
            continue

        nested_issue = value.get("issue")
        if isinstance(nested_issue, Mapping):
            yield nested_issue

        yield value

    yield from _iter_recursive_issue_like_mappings(event)


def _iter_recursive_issue_like_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        if "title" in value and any(
            key in value for key in ("id", "issueId", "issue_id", "identifier")
        ):
            yield value

        for child in value.values():
            yield from _iter_recursive_issue_like_mappings(child)
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for child in value:
            yield from _iter_recursive_issue_like_mappings(child)


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _iter_mappings(child)
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for child in value:
            yield from _iter_mappings(child)


def _first_text_value(context: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, Mapping):
            value = value.get("name") or value.get("title")

        if isinstance(value, (str, int)):
            text = str(value).strip()
            if text:
                return text

    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_label(value: Any) -> str:
    if not isinstance(value, (str, int)):
        return ""

    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def main() -> int:
    update = build_issue_title_update(json.load(sys.stdin))
    print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
