"""Build Linear issue title updates for Cursor research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_CHANGE_VALUES = {
    "status changed",
    "status change",
    "statuschanged",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflowstateid",
    "stateid",
}
_UPDATE_VALUES = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue moves to To Research.

    The automation runtime provides a flat ``triggerContext`` payload, while
    Linear webhooks often nest the same issue data under ``data.issue``. This
    function accepts both shapes and only emits a title update for status-change
    events whose new status normalizes to ``to research``.
    """

    if not isinstance(event, Mapping):
        return None

    context = _merged_context(event)
    if not _is_status_change_event(event, context):
        return None

    status = _extract_new_status(event, context)
    if _normalize_value(status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(event, context)
    title = _extract_title(event, context)
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {stripped_title}",
    }


def _merged_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge likely payload locations, with outer automation fields winning."""

    context: dict[str, Any] = {}
    for source in (
        _mapping_at(event, "data", "issue"),
        _mapping_at(event, "issue"),
        _mapping_at(event, "node"),
        _mapping_at(event, "data"),
        _mapping_at(event, "triggerContext"),
        event,
    ):
        if source:
            context.update(source)
    return context


def _is_status_change_event(
    event: Mapping[str, Any], context: Mapping[str, Any]
) -> bool:
    trigger_values = [
        value
        for key in ("trigger", "webhookType", "action", "type", "eventType")
        for value in _values_for_key(event, key)
    ]
    trigger_values.extend(
        context.get(key)
        for key in ("trigger", "webhookType", "action", "type", "eventType")
    )

    normalized_triggers = {_normalize_value(value) for value in trigger_values if value}
    if normalized_triggers & _STATUS_CHANGE_VALUES:
        return True

    if normalized_triggers & _UPDATE_VALUES:
        return _changed_status_fields(event, context)

    return False


def _changed_status_fields(
    event: Mapping[str, Any], context: Mapping[str, Any]
) -> bool:
    changed_values: list[Any] = []
    for source in (event, context):
        for key in (
            "updatedFields",
            "changedFields",
            "changed_fields",
            "updated_fields",
        ):
            if key in source:
                changed_values.extend(_iter_field_names(source[key]))
        for key in ("changes", "previousValues", "previous_values"):
            if isinstance(source.get(key), Mapping):
                changed_values.extend(source[key].keys())

    normalized_fields = {_normalize_field_name(value) for value in changed_values}
    return bool(normalized_fields & _STATUS_FIELD_NAMES)


def _extract_new_status(
    event: Mapping[str, Any], context: Mapping[str, Any]
) -> Any:
    for source in (context, event):
        for key in (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "status",
            "state",
            "workflowState",
            "workflow_state",
        ):
            value = source.get(key)
            if value is not None:
                return _name_or_value(value)

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = changes.get(key)
            if isinstance(value, Mapping):
                for nested_key in ("to", "after", "newValue", "new_value"):
                    if nested_key in value:
                        return _name_or_value(value[nested_key])
            elif value is not None:
                return _name_or_value(value)

    return None


def _extract_issue_id(
    event: Mapping[str, Any], context: Mapping[str, Any]
) -> str | None:
    for source in _issue_data_sources(event, context):
        value = _first_string(source, ("issueId", "issue_id", "identifier", "key", "id"))
        if value:
            return value
    return None


def _extract_title(event: Mapping[str, Any], context: Mapping[str, Any]) -> str | None:
    for source in _issue_data_sources(event, context):
        value = _first_string(source, ("title", "name"))
        if value:
            return value
    return None


def _issue_data_sources(
    event: Mapping[str, Any], context: Mapping[str, Any]
) -> tuple[Mapping[str, Any], ...]:
    return tuple(
        source
        for source in (
            _mapping_at(event, "triggerContext"),
            _mapping_at(event, "data", "issue"),
            _mapping_at(event, "issue"),
            _mapping_at(event, "node"),
            _mapping_at(event, "data"),
            context,
            event,
        )
        if source
    )


def _first_string(source: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _mapping_at(mapping: Mapping[str, Any], *path: str) -> Mapping[str, Any] | None:
    current: Any = mapping
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, Mapping) else None


def _values_for_key(value: Any, target_key: str) -> list[Any]:
    if isinstance(value, Mapping):
        values = [item for key, item in value.items() if key == target_key]
        for item in value.values():
            values.extend(_values_for_key(item, target_key))
        return values
    if isinstance(value, list):
        values: list[Any] = []
        for item in value:
            values.extend(_values_for_key(item, target_key))
        return values
    return []


def _iter_field_names(value: Any) -> list[Any]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return list(value.keys())
    if isinstance(value, list | tuple | set):
        return list(value)
    return []


def _name_or_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "value", "title"):
            if key in value:
                return value[key]
    return value


def _normalize_field_name(value: Any) -> str:
    return _normalize_value(value).replace(" ", "")


def _normalize_value(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.casefold()


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
