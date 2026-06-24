"""Build Linear issue-title update actions for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to to-research."""

    if not isinstance(event, Mapping):
        return None

    mappings = list(_iter_relevant_mappings(event))
    if not _is_status_change_event(mappings):
        return None

    status = _first_text(
        mappings,
        (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "status",
            "state",
            "workflowState",
            "workflow_state",
        ),
    ) or _status_from_changes(mappings)
    if _normalize_label(status) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(mappings, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(mappings, ("title", "name"))
    if not issue_id or not title:
        return None

    trimmed_title = title.strip()
    if _has_research_prefix(trimmed_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{RESEARCH_PREFIX}: {trimmed_title}",
    }


def _iter_relevant_mappings(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield payload layers from most specific automation metadata to issue data."""

    yield event

    trigger_context = _mapping_value(event, "triggerContext")
    if trigger_context:
        yield trigger_context

    automation_info = _mapping_value(event, "automation_trigger_info")
    automation_context = _mapping_value(automation_info, "triggerContext") if automation_info else None
    if automation_context:
        yield automation_context

    data = _mapping_value(event, "data")
    if data:
        yield data
        data_issue = _mapping_value(data, "issue")
        if data_issue:
            yield data_issue

    issue = _mapping_value(event, "issue")
    if issue:
        yield issue

    node = _mapping_value(event, "node")
    if node:
        yield node


def _is_status_change_event(mappings: list[Mapping[str, Any]]) -> bool:
    trigger_values = _all_text(
        mappings,
        ("trigger", "action", "type", "webhookType", "webhook_type", "eventType", "event_type"),
    )
    if any(_is_direct_status_trigger(value) for value in trigger_values):
        return True

    if any(_looks_like_issue_update(value) for value in trigger_values):
        return _updated_fields_include_status(mappings) or _changes_include_status(mappings)

    return False


def _is_direct_status_trigger(value: str) -> bool:
    normalized = _normalize_label(value)
    return normalized in {
        "status changed",
        "status change",
        "state changed",
        "workflow state changed",
    }


def _looks_like_issue_update(value: str) -> bool:
    normalized = _normalize_label(value)
    return normalized in {
        "issue updated",
        "updated issue",
        "update",
        "updated",
        "issue update",
    }


def _updated_fields_include_status(mappings: list[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = mapping.get(key)
            if isinstance(fields, str) and _normalize_key(fields) in STATUS_FIELD_NAMES:
                return True
            if isinstance(fields, Iterable) and not isinstance(fields, (str, bytes, Mapping)):
                for field in fields:
                    if _normalize_key(_extract_text(field)) in STATUS_FIELD_NAMES:
                        return True
    return False


def _changes_include_status(mappings: list[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        for key in ("changes", "changed", "updates"):
            changes = mapping.get(key)
            if isinstance(changes, Mapping):
                if any(_normalize_key(str(field)) in STATUS_FIELD_NAMES for field in changes):
                    return True
                if _normalize_key(_extract_text(changes.get("field"))) in STATUS_FIELD_NAMES:
                    return True
            elif isinstance(changes, Iterable) and not isinstance(changes, (str, bytes)):
                for change in changes:
                    if isinstance(change, Mapping):
                        field = change.get("field") or change.get("name") or change.get("key")
                        if _normalize_key(_extract_text(field)) in STATUS_FIELD_NAMES:
                            return True
    return False


def _status_from_changes(mappings: list[Mapping[str, Any]]) -> str | None:
    for mapping in mappings:
        for key in ("changes", "changed", "updates"):
            changes = mapping.get(key)
            if isinstance(changes, Mapping):
                for field, value in changes.items():
                    if _normalize_key(str(field)) in STATUS_FIELD_NAMES:
                        return _changed_value_text(value)
                field = changes.get("field") or changes.get("name") or changes.get("key")
                if _normalize_key(_extract_text(field)) in STATUS_FIELD_NAMES:
                    return _changed_value_text(changes)
            elif isinstance(changes, Iterable) and not isinstance(changes, (str, bytes)):
                for change in changes:
                    if not isinstance(change, Mapping):
                        continue
                    field = change.get("field") or change.get("name") or change.get("key")
                    if _normalize_key(_extract_text(field)) in STATUS_FIELD_NAMES:
                        return _changed_value_text(change)
    return None


def _changed_value_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "newValue", "new_value", "new", "after", "value", "currentValue"):
            text = _extract_text(value.get(key))
            if text:
                return text
    return _extract_text(value)


def _first_text(mappings: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        for mapping in mappings:
            text = _extract_text(mapping.get(key))
            if text:
                return text
    return None


def _all_text(mappings: list[Mapping[str, Any]], keys: tuple[str, ...]) -> list[str]:
    values: list[str] = []
    for mapping in mappings:
        for key in keys:
            text = _extract_text(mapping.get(key))
            if text:
                values.append(text)
    return values


def _mapping_value(mapping: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    value = mapping.get(key) if isinstance(mapping, Mapping) else None
    return value if isinstance(value, Mapping) else None


def _extract_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "status", "identifier", "id", "key"):
            text = _extract_text(value.get(key))
            if text:
                return text
        return None
    return str(value).strip() or None


def _normalize_label(value: str | None) -> str:
    if not value:
        return ""
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^a-zA-Z0-9]+", " ", separated).lower().split()
    return " ".join(words)


def _normalize_key(value: str | None) -> str:
    return _normalize_label(value).replace(" ", "")


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(RESEARCH_PREFIX.lower())


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update:
        json.dump(update, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
