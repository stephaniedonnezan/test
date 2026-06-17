"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_WORD_SEPARATOR = re.compile(r"[^A-Za-z0-9]+")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action when a status enters research.

    The handler is intentionally side-effect free so the automation runner can
    decide how to apply the returned action.
    """

    if not isinstance(event, Mapping):
        return None

    sources = _payload_sources(event)
    if not _is_status_change_event(sources):
        return None

    status = _new_status(sources)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(sources, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(sources, ("title", "name"))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if not clean_title or clean_title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _payload_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = [event]

    trigger_context = _mapping_value(event, "triggerContext")
    if trigger_context is not None:
        sources.append(trigger_context)

    data = _mapping_value(event, "data")
    if data is not None:
        sources.append(data)
        issue = _mapping_value(data, "issue")
        if issue is not None:
            sources.append(issue)

    direct_issue = _mapping_value(event, "issue")
    if direct_issue is not None:
        sources.append(direct_issue)

    return sources


def _is_status_change_event(sources: list[Mapping[str, Any]]) -> bool:
    trigger_values = [
        value
        for source in sources
        for key in ("trigger", "webhookType", "action", "type", "eventType")
        if (value := _text_value(source.get(key)))
    ]

    if any(_is_direct_status_change(value) for value in trigger_values):
        return True

    has_update_trigger = any(_is_update_trigger(value) for value in trigger_values)
    has_status_marker = any(_has_status_change_marker(source) for source in sources)

    return has_status_marker and (has_update_trigger or not trigger_values)


def _is_direct_status_change(value: str) -> bool:
    normalized = _normalize_words(value)
    return "changed" in normalized and any(
        field in normalized for field in ("status", "state", "workflow state")
    )


def _is_update_trigger(value: str) -> bool:
    normalized = _normalize_words(value)
    return normalized in {"update", "updated", "issue update", "issue updated", "updated issue"}


def _has_status_change_marker(source: Mapping[str, Any]) -> bool:
    for key in (
        "updatedFields",
        "updated_fields",
        "changedFields",
        "changed_fields",
        "changes",
        "updatedFrom",
        "updated_from",
    ):
        if _contains_status_field(source.get(key)):
            return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_is_status_field(key) or _contains_status_field(item) for key, item in value.items())
    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)
    text = _text_value(value)
    return bool(text and _is_status_field(text))


def _is_status_field(value: str) -> bool:
    normalized = _normalize_words(value)
    return any(field in normalized.split() for field in ("status", "state")) or "workflow state" in normalized


def _new_status(sources: list[Mapping[str, Any]]) -> str | None:
    explicit_status = _first_text(
        sources,
        (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "newWorkflowState",
            "new_workflow_state",
            "statusName",
            "stateName",
            "workflowStateName",
        ),
    )
    if explicit_status:
        return explicit_status

    changed_status = _status_from_changes(sources)
    if changed_status:
        return changed_status

    return _first_text(sources, ("status", "state", "workflowState", "workflow_state"))


def _status_from_changes(sources: list[Mapping[str, Any]]) -> str | None:
    for source in sources:
        for key in ("changes", "updatedTo", "updated_to"):
            value = source.get(key)
            status = _status_from_change_value(value)
            if status:
                return status
    return None


def _status_from_change_value(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for key, item in value.items():
        if _is_status_field(str(key)):
            if isinstance(item, Mapping):
                status = _first_text(
                    [item],
                    ("to", "toValue", "to_value", "new", "newValue", "new_value", "name"),
                )
                if status:
                    return status
            status = _text_value(item)
            if status:
                return status

    return None


def _first_text(sources: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for source in sources:
        for key in keys:
            value = _text_value(source.get(key))
            if value and value.strip():
                return value
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value"):
            nested = _text_value(value.get(key))
            if nested:
                return nested
    return None


def _mapping_value(source: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    value = source.get(key)
    return value if isinstance(value, Mapping) else None


def _normalize_words(value: str | None) -> str:
    if not value:
        return ""
    with_camel_breaks = _CAMEL_CASE_BOUNDARY.sub(" ", value)
    separated = _WORD_SEPARATOR.sub(" ", with_camel_breaks)
    return " ".join(separated.casefold().split())


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
