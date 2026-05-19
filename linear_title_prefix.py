"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when an issue moves to To Research.

    The automation runtime provides a compact ``triggerContext`` payload, while
    Linear webhooks commonly use nested ``data``/``issue`` objects. This function
    accepts both shapes and returns a side-effect-free action for the caller to
    apply.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if issue_id is None or title is None:
        return None

    issue_id_text = str(issue_id).strip()
    title_text = str(title).strip()
    if not issue_id_text or not title_text or _has_research_prefix(title_text):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id_text,
        "title": f"{PREFIX}: {title_text}",
    }


handle_issue_status_changed = build_issue_title_update


def _is_status_change(event: Mapping[str, Any]) -> bool:
    event_values = [_normalize_words(value) for value in _event_type_values(event)]

    if any(
        value in {"status changed", "status change", "state changed", "workflow state changed"}
        or value.endswith(" status changed")
        for value in event_values
    ):
        return True

    issue_update = any(
        value in {"update", "updated", "issue updated", "updated issue"} for value in event_values
    ) and (
        any(value == "issue" or value.endswith(" issue") for value in event_values)
        or _mapping_at(event, "issue") is not None
        or _mapping_at(_mapping_at(event, "data"), "issue") is not None
    )

    return issue_update and _has_status_field_change(event)


def _event_type_values(event: Mapping[str, Any]) -> Iterable[Any]:
    keys = ("trigger", "triggerType", "webhookType", "action", "type", "eventType")

    for source in _metadata_sources(event):
        for key in keys:
            value = source.get(key)
            if value is not None:
                yield value


def _has_status_field_change(event: Mapping[str, Any]) -> bool:
    field_keys = (
        "updatedFields",
        "updated_fields",
        "changedFields",
        "changed_fields",
        "updatedFrom",
        "updated_from",
        "changes",
    )

    for source in _metadata_sources(event):
        for key in field_keys:
            if any(_is_status_field_name(name) for name in _changed_field_names(source.get(key))):
                return True

    return False


def _changed_field_names(value: Any) -> Iterable[Any]:
    if value is None:
        return

    if isinstance(value, Mapping):
        yield from value.keys()
        for key in ("field", "fieldName", "name", "key", "property", "path"):
            nested_value = value.get(key)
            if nested_value is not None:
                yield nested_value
        return

    if isinstance(value, str):
        yield value
        return

    if isinstance(value, Iterable):
        for item in value:
            if isinstance(item, Mapping):
                yield from _changed_field_names(item)
            else:
                yield item


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_field_name(value)
    return normalized in {
        "status",
        "state",
        "stateid",
        "workflowstate",
        "workflowstateid",
    }


def _extract_new_status(event: Mapping[str, Any]) -> Any:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "toStatus",
        "to_status",
        "statusName",
        "stateName",
        "workflowStateName",
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    for source in _status_sources(event):
        value = _first_named_value(source, explicit_keys)
        if value is not None:
            return value

    for source in _status_sources(event):
        value = _first_named_value(source, fallback_keys)
        if value is not None:
            return value

    return None


def _extract_issue_id(event: Mapping[str, Any]) -> Any:
    return _first_plain_value(_issue_sources(event), ("id", "issueId", "issue_id", "identifier"))


def _extract_title(event: Mapping[str, Any]) -> Any:
    return _first_plain_value(_issue_sources(event), ("title", "name"))


def _first_plain_value(sources: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> Any:
    for source in sources:
        for key in keys:
            value = source.get(key)
            if value is not None:
                return value
    return None


def _first_named_value(source: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = _name_or_value(source.get(key))
        if value is not None:
            return value
    return None


def _name_or_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return value.get("name") or value.get("title") or value.get("label")
    return value


def _metadata_sources(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    yield event
    trigger_context = _mapping_at(event, "triggerContext")
    if trigger_context is not None:
        yield trigger_context
    data = _mapping_at(event, "data")
    if data is not None:
        yield data
    issue = _mapping_at(event, "issue")
    if issue is not None:
        yield issue
    data_issue = _mapping_at(data, "issue")
    if data_issue is not None:
        yield data_issue


def _status_sources(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    trigger_context = _mapping_at(event, "triggerContext")
    if trigger_context is not None:
        yield trigger_context

    yield event

    data = _mapping_at(event, "data")
    if data is not None:
        yield data

    issue = _mapping_at(event, "issue")
    if issue is not None:
        yield issue

    data_issue = _mapping_at(data, "issue")
    if data_issue is not None:
        yield data_issue


def _issue_sources(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    trigger_context = _mapping_at(event, "triggerContext")
    if trigger_context is not None:
        yield trigger_context

    data = _mapping_at(event, "data")
    data_issue = _mapping_at(data, "issue")
    if data_issue is not None:
        yield data_issue

    issue = _mapping_at(event, "issue")
    if issue is not None:
        yield issue

    if data is not None:
        yield data

    yield event


def _mapping_at(source: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if not isinstance(source, Mapping):
        return None
    value = source.get(key)
    return value if isinstance(value, Mapping) else None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""
    text = _CAMEL_BOUNDARY.sub(" ", str(value))
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def _normalize_field_name(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"[^a-z0-9]", "", _normalize_words(value))


def main() -> int:
    payload = json.load(sys.stdin)
    result = build_issue_title_update(payload)
    if result is not None:
        json.dump(result, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
