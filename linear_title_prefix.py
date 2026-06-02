"""Build Linear issue title updates for issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
TITLE_SEPARATOR = ": "

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}
_TRIGGER_KEYS = {"trigger", "webhooktype", "webhook_type", "action", "type"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    context = _build_context(event)
    if not _is_status_change_event(context):
        return None

    new_status = _extract_new_status(context)
    if _normalize_text(new_status) != _normalize_text(TARGET_STATUS):
        return None

    issue_id = _extract_first_text(context, ("id", "issueId", "issue_id", "identifier"))
    title = _extract_first_text(context, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        prefixed_title = title
    else:
        prefixed_title = f"{TITLE_PREFIX}{TITLE_SEPARATOR}{title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": prefixed_title,
    }


def _build_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common automation and Linear webhook nesting into one lookup map."""

    context: dict[str, Any] = {}
    issue = _first_mapping_at_path(event, ("data", "issue"))
    data = _get_mapping(event, "data")
    trigger_context = _get_mapping(event, "triggerContext")

    for layer in (issue, data, trigger_context, event):
        if layer:
            context.update(layer)

    if issue:
        context["issue"] = issue
    if data:
        context["data"] = data
    if trigger_context:
        context["triggerContext"] = trigger_context

    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        value
        for key, value in context.items()
        if _normalize_key(key) in _TRIGGER_KEYS and isinstance(value, str)
    ]

    if any(_normalize_text(value) in {"status changed", "status change"} for value in trigger_values):
        return True

    if any(_normalize_text(value) in {"issue updated", "updated issue", "update", "updated"} for value in trigger_values):
        return _updated_fields_include_status(context)

    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    updated_fields = _extract_updated_fields(context)
    if not updated_fields:
        return False

    return any(_normalize_key(field) in _STATUS_FIELD_NAMES for field in updated_fields)


def _extract_updated_fields(context: Mapping[str, Any]) -> list[str]:
    values: list[Any] = []
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if key in context:
            values.append(context[key])

    data = _get_mapping(context, "data")
    if data:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if key in data:
                values.append(data[key])

    field_names: list[str] = []
    for value in values:
        if isinstance(value, str):
            field_names.append(value)
        elif isinstance(value, Mapping):
            field_names.extend(str(key) for key in value.keys())
        elif isinstance(value, Iterable):
            field_names.extend(str(item) for item in value)

    return field_names


def _extract_new_status(context: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "toStatus", "to_status", "status"):
        value = _extract_text_or_name(context.get(key))
        if value:
            return value

    for key in ("state", "workflowState", "workflow_state"):
        value = _extract_text_or_name(context.get(key))
        if value:
            return value

    return None


def _extract_first_text(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _extract_text_or_name(context.get(key))
        if value:
            return value
    return None


def _extract_text_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "id", "identifier"):
            nested = _extract_text_or_name(value.get(key))
            if nested:
                return nested

    return None


def _first_mapping_at_path(source: Mapping[str, Any], path: tuple[str, ...]) -> Mapping[str, Any] | None:
    current: Any = source
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, Mapping) else None


def _get_mapping(source: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    value = source.get(key)
    return value if isinstance(value, Mapping) else None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", str(value))
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    if result is not None:
        json.dump(result, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
