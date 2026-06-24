"""Build Linear issue-title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    metadata = _collect_metadata(event)
    issue = _collect_issue_data(event)

    if not _is_status_change(metadata):
        return None

    new_status = _status_value(metadata) or _status_value(issue)
    if _normalize_text(new_status) != _normalize_text(TARGET_STATUS):
        return None

    issue_id = _first_text(issue, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(issue, ("title", "name"))
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{RESEARCH_PREFIX}: {title}",
    }


def _collect_metadata(event: Mapping[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for context in _candidate_contexts(event):
        metadata.update(_select_fields(context, _metadata_keys(context)))
    return metadata


def _collect_issue_data(event: Mapping[str, Any]) -> dict[str, Any]:
    issue: dict[str, Any] = {}
    for context in _candidate_contexts(event):
        issue.update(_select_fields(context, ("issueId", "issue_id", "identifier", "key", "id", "title", "name")))
        nested_issue = _mapping_at(context, "issue")
        if nested_issue is not None:
            issue.update(_select_fields(nested_issue, ("issueId", "issue_id", "identifier", "key", "id", "title", "name")))
            issue.update(_select_fields(nested_issue, ("status", "state", "workflowState", "workflow_state")))
        issue.update(_select_fields(context, ("status", "state", "workflowState", "workflow_state")))
    return issue


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(context: Any) -> None:
        if isinstance(context, Mapping):
            contexts.append(context)

    add(event)
    trigger_context = _mapping_at(event, "triggerContext") or _mapping_at(event, "trigger_context")
    add(trigger_context)

    automation_info = _mapping_at(event, "automation_trigger_info") or _mapping_at(event, "automationTriggerInfo")
    if automation_info is not None:
        add(automation_info)
        add(_mapping_at(automation_info, "triggerContext") or _mapping_at(automation_info, "trigger_context"))

    data = _mapping_at(event, "data")
    if data is not None:
        add(data)
        add(_mapping_at(data, "issue"))

    return contexts


def _is_status_change(metadata: Mapping[str, Any]) -> bool:
    event_names = [
        _normalize_text(value)
        for key in ("trigger", "webhookType", "webhook_type", "action", "type")
        if (value := metadata.get(key)) is not None
    ]

    if any(name in {"statuschanged", "statuschange", "status_changed", "status changed"} for name in event_names):
        return True

    if any(name in {"issue updated", "updated issue", "update", "updated"} for name in event_names):
        return _updated_status_fields(metadata)

    return False


def _updated_status_fields(metadata: Mapping[str, Any]) -> bool:
    updated_fields = metadata.get("updatedFields") or metadata.get("updated_fields")
    if _contains_status_field(updated_fields):
        return True

    changes = metadata.get("changes") or metadata.get("changed") or metadata.get("updated")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(field) in STATUS_FIELD_NAMES for field in changes)
    return _contains_status_field(changes)


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        return any(_contains_status_field(field) for field in value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_status_field(item) for item in value)
    return False


def _status_value(values: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "toStatus", "to_status", "status", "state", "workflowState", "workflow_state"):
        value = values.get(key)
        if isinstance(value, Mapping):
            text = _first_text(value, ("name", "title", "label"))
            if text:
                return text
        elif value is not None:
            text = _clean_text(value)
            if text:
                return text
    return None


def _metadata_keys(context: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(
        key
        for key in (
            "trigger",
            "webhookType",
            "webhook_type",
            "action",
            "type",
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "status",
            "state",
            "workflowState",
            "workflow_state",
            "updatedFields",
            "updated_fields",
            "changes",
            "changed",
            "updated",
        )
        if key in context
    )


def _select_fields(context: Mapping[str, Any], keys: Sequence[str]) -> dict[str, Any]:
    return {key: context[key] for key in keys if key in context}


def _mapping_at(context: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    value = context.get(key)
    return value if isinstance(value, Mapping) else None


def _first_text(values: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        if key in values:
            text = _clean_text(values[key])
            if text:
                return text
    return None


def _clean_text(value: Any) -> str | None:
    if value is None or isinstance(value, (Mapping, Sequence)) and not isinstance(value, (str, bytes, bytearray)):
        return None
    text = str(value).strip()
    return text or None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(RESEARCH_PREFIX.casefold())


def _normalize_text(value: Any) -> str:
    text = _clean_text(value)
    if text is None:
        return ""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return re.sub(r"[\W_]+", " ", text.casefold()).strip()


def _normalize_field_name(value: Any) -> str:
    text = _clean_text(value)
    if text is None:
        return ""
    return re.sub(r"[\W_]+", "", text.casefold())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
