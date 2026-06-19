"""Build Linear issue title updates for research-status automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newStatusName",
    "new_status_name",
    "statusName",
    "status_name",
)
_STATUS_KEYS = _EXPLICIT_STATUS_KEYS + ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TRIGGER_KEYS = ("trigger", "webhookType", "webhook_type", "action", "type")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research.

    The function is intentionally side-effect free so webhook runners can decide
    how to apply the returned update.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_iter_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    status = _extract_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_string(contexts, _ISSUE_ID_KEYS)
    title = _extract_first_string(contexts, ("title", "issueTitle", "issue_title"))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if _has_research_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _iter_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely metadata and issue objects from flat or nested payloads."""

    yield event

    trigger_context = _mapping_at(event, "triggerContext")
    if trigger_context is not None:
        yield trigger_context

    issue = _mapping_at(event, "issue")
    if issue is not None:
        yield issue

    data = _mapping_at(event, "data")
    if data is not None:
        yield data
        data_issue = _mapping_at(data, "issue")
        if data_issue is not None:
            yield data_issue


def _mapping_at(source: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    value = source.get(key)
    return value if isinstance(value, Mapping) else None


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = [
        _normalize(context[key])
        for context in contexts
        for key in _TRIGGER_KEYS
        if key in context
    ]

    if any(value in {"status changed", "status change", "state changed"} for value in trigger_values):
        return True

    if any(value in {"update", "updated", "issue updated", "updated issue"} for value in trigger_values):
        return _updated_fields_include_status(contexts)

    return False


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _field_collection_includes_status(context.get(key)):
                return True

        for key in ("changes", "changed", "updatedFrom", "updated_from"):
            if _change_map_includes_status(context.get(key)):
                return True

    return False


def _field_collection_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _field_name_is_status(value)

    if isinstance(value, Mapping):
        return any(_field_name_is_status(key) for key in value)

    if isinstance(value, Iterable):
        return any(_field_name_is_status(item) for item in value)

    return False


def _change_map_includes_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_field_name_is_status(key) for key in value)
    return False


def _field_name_is_status(value: Any) -> bool:
    return _normalize_field_name(value) in _STATUS_FIELDS


def _normalize_field_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _normalize(value))


def _extract_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for key_group in (_EXPLICIT_STATUS_KEYS, _STATUS_KEYS):
        for context in contexts:
            for key in key_group:
                value = _string_or_name(context.get(key))
                if value:
                    return value
    return None


def _extract_first_string(contexts: list[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _string_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        name = value.get("name")
        if isinstance(name, str):
            return name
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize(value: Any) -> str:
    text = "" if value is None else str(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
