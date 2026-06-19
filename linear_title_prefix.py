"""Build Linear issue-title updates for Cursor research status changes.

The automation receives slightly different payload shapes depending on whether
the source is Cursor's trigger context or a native Linear webhook. This module
normalizes the common shapes and emits a small action object that a caller can
use to update the issue title.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue moves to research.

    The returned action has this shape:

    ```
    {
        "action": "update_issue_title",
        "issueId": "POI-123",
        "title": "Cursor researching: Existing title",
    }
    ```

    Non-status updates, non-research statuses, invalid payloads, and titles that
    already start with the prefix are ignored.
    """

    if not isinstance(event, Mapping):
        return None

    for context in _candidate_contexts(event):
        if not _is_status_change(context):
            continue

        new_status = _extract_new_status(context)
        if _normalize_label(new_status) != RESEARCH_STATUS:
            continue

        issue_id = _extract_issue_id(context)
        title = _extract_title(context)
        if not issue_id or not title:
            continue
        if _has_title_prefix(title):
            return None

        return {
            "action": "update_issue_title",
            "issueId": issue_id,
            "title": f"{TITLE_PREFIX}: {title}",
        }

    return None


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return merged payload views with outer trigger metadata kept available."""

    contexts: list[Mapping[str, Any]] = []

    def add(mapping: Mapping[str, Any]) -> None:
        if mapping not in contexts:
            contexts.append(mapping)

    def visit(mapping: Mapping[str, Any]) -> None:
        add(mapping)

        for context_key in ("automation_trigger_info", "triggerContext", "trigger_context"):
            trigger_context = mapping.get(context_key)
            if isinstance(trigger_context, Mapping):
                add(trigger_context)
                visit(trigger_context)

        data = mapping.get("data")
        if isinstance(data, Mapping):
            merged_data = {**data, **{k: v for k, v in mapping.items() if k != "data"}}
            add(merged_data)

            issue = data.get("issue")
            if isinstance(issue, Mapping):
                add({**issue, **data, **{k: v for k, v in mapping.items() if k != "data"}})

        issue = mapping.get("issue")
        if isinstance(issue, Mapping):
            add({**issue, **{k: v for k, v in mapping.items() if k != "issue"}})

    visit(event)
    return contexts


def _is_status_change(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        context.get("trigger"),
        context.get("webhookType"),
        context.get("action"),
        context.get("type"),
    ]

    if any(_looks_like_status_change(value) for value in trigger_values):
        return True

    if any(_normalize_label(value) in {"issue updated", "updated issue", "update"} for value in trigger_values):
        return _updated_status_fields(context)

    return False


def _looks_like_status_change(value: Any) -> bool:
    normalized = _normalize_label(value)
    return normalized in {
        "status changed",
        "state changed",
        "workflow state changed",
        "issue status changed",
        "issue state changed",
    }


def _updated_status_fields(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields"):
        fields = context.get(key)
        if isinstance(fields, str):
            return _normalize_field_name(fields) in STATUS_FIELD_NAMES
        if isinstance(fields, list):
            return any(_normalize_field_name(field) in STATUS_FIELD_NAMES for field in fields)

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(field) in STATUS_FIELD_NAMES for field in changes)

    return False


def _extract_new_status(context: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    ):
        status = _text_value(context.get(key))
        if status:
            return status

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for field_name in ("status", "state", "workflowState", "workflow_state"):
            change = changes.get(field_name)
            if isinstance(change, Mapping):
                status = _text_value(change.get("to") or change.get("new") or change.get("after"))
                if status:
                    return status
            else:
                status = _text_value(change)
                if status:
                    return status

    for key in ("status", "state", "workflowState", "workflow_state"):
        status = _text_value(context.get(key))
        if status:
            return status

    return None


def _extract_issue_id(context: Mapping[str, Any]) -> str | None:
    for key in ("issueId", "issue_id", "identifier", "key", "id"):
        issue_id = _text_value(context.get(key))
        if issue_id:
            return issue_id
    return None


def _extract_title(context: Mapping[str, Any]) -> str | None:
    for key in ("title", "name"):
        title = _text_value(context.get(key))
        if title:
            return title
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _text_value(value.get(key))
            if text:
                return text

    return None


def _has_title_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_label(value: Any) -> str | None:
    text = _text_value(value)
    if not text:
        return None

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def _normalize_field_name(value: Any) -> str | None:
    text = _text_value(value)
    if not text:
        return None
    return re.sub(r"[^A-Za-z0-9_]+", "", text).casefold()


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is None:
        return 0

    json.dump(action, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
