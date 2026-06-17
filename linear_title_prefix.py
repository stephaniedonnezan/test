"""Build Linear issue title updates for Cursor research automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "status",
    "state",
    "workflowState",
    "workflow_state",
)
_STATUS_FIELD_NAMES = {"status", "state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _new_status(event)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _issue_id(event)
    title = _issue_title(event)
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    if _has_direct_status_change_trigger(event):
        return True

    if not _has_update_trigger(event):
        return False

    return _changed_fields_include_status(event)


def _has_direct_status_change_trigger(event: Mapping[str, Any]) -> bool:
    for mapping in _metadata_mappings(event):
        for key in ("trigger", "action", "type", "webhookType", "webhook_type"):
            normalized = _normalize_text(mapping.get(key))
            if "chang" in normalized and (
                "status" in normalized
                or "state" in normalized
                or "workflow state" in normalized
            ):
                return True
    return False


def _has_update_trigger(event: Mapping[str, Any]) -> bool:
    update_tokens = {
        "update",
        "updated",
        "issue update",
        "issue updated",
        "updated issue",
    }

    for mapping in _metadata_mappings(event):
        for key in ("trigger", "action", "type", "webhookType", "webhook_type"):
            if _normalize_text(mapping.get(key)) in update_tokens:
                return True
    return False


def _changed_fields_include_status(event: Mapping[str, Any]) -> bool:
    for mapping in _metadata_mappings(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = mapping.get(key)
            if isinstance(fields, str):
                if _field_mentions_status(fields):
                    return True
            elif isinstance(fields, Iterable):
                for field in fields:
                    if _field_mentions_status(field):
                        return True

        for key in ("changes", "changed", "updatedFrom", "updated_from"):
            changes = mapping.get(key)
            if isinstance(changes, Mapping):
                for field in changes:
                    if _field_mentions_status(field):
                        return True

    return False


def _field_mentions_status(field: Any) -> bool:
    if isinstance(field, Mapping):
        candidates = (
            field.get("field"),
            field.get("name"),
            field.get("key"),
            field.get("path"),
        )
    else:
        candidates = (field,)

    for candidate in candidates:
        normalized = _normalize_text(candidate)
        compact = normalized.replace(" ", "")
        if compact in _STATUS_FIELD_NAMES:
            return True
        if compact in {"statusid", "stateid", "workflowstateid"}:
            return True

    return False


def _new_status(event: Mapping[str, Any]) -> str | None:
    for mapping in _candidate_mappings(event):
        for key in _STATUS_KEYS:
            if key in mapping:
                status = _string_value(mapping[key])
                if status:
                    return status
    return None


def _issue_id(event: Mapping[str, Any]) -> str | None:
    for mapping in _candidate_mappings(event):
        for key in ("issueId", "issue_id", "id", "identifier", "key"):
            value = _string_value(mapping.get(key))
            if value:
                return value
    return None


def _issue_title(event: Mapping[str, Any]) -> str | None:
    for mapping in _candidate_mappings(event):
        value = _string_value(mapping.get("title"))
        if value:
            return value
    return None


def _candidate_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and not any(value is item for item in candidates):
            candidates.append(value)

    add(event.get("triggerContext"))
    add(event)
    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data)
    add(event.get("issue"))

    return candidates


def _metadata_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates = _candidate_mappings(event)
    data = event.get("data")
    if isinstance(data, Mapping):
        add_state = data.get("state")
        if isinstance(add_state, Mapping) and not any(add_state is item for item in candidates):
            candidates.append(add_state)
    return candidates


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "displayName", "display_name"):
            nested = _string_value(value.get(key))
            if nested:
                return nested

    return None


def _normalize_text(value: Any) -> str:
    text = _string_value(value)
    if not text:
        return ""

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    """Read a JSON event from stdin and print the title update action."""
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
