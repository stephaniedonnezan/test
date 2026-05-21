"""Build Linear issue title updates for Cursor research automations.

The automation receives Linear status-change payloads in a few related shapes.
This module keeps the decision local and side-effect free: callers pass the
event payload and receive an update action only when the issue moved to
"to research".
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "stateid", "workflowstate", "workflowstateid"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action for matching Linear events.

    Matching requires a status-change/update event whose new status normalizes
    to "to research". Titles already starting with the Cursor prefix are left
    untouched so retries remain idempotent.
    """

    if not isinstance(event, Mapping):
        return None

    issue = _extract_issue(event)
    if not _is_status_change_event(event):
        return None

    status = _extract_new_status(event, issue)
    if _normalize_phrase(status) != TARGET_STATUS:
        return None

    issue_id = _clean_text(_first_value(issue, "id", "issueId", "issue_id", "identifier"))
    title = _clean_text(_first_value(issue, "title"))
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _extract_issue(event: Mapping[str, Any]) -> Mapping[str, Any]:
    """Find the object that contains the issue id and title."""

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")

    for candidate in (trigger_context, issue, data, event):
        if isinstance(candidate, Mapping) and _first_value(candidate, "title"):
            return candidate

    if isinstance(data, Mapping):
        nested_issue = data.get("issue")
        if isinstance(nested_issue, Mapping):
            return nested_issue

    return event


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    values = _event_type_values(event)
    if any(_normalize_event_name(value) in {"statuschanged", "statuschange"} for value in values):
        return True

    is_update_event = any(_normalize_event_name(value) in {"update", "updated", "issueupdated", "updatedissue"} for value in values)
    if not is_update_event:
        return False

    updated_fields = _updated_field_names(event)
    return not updated_fields or bool(updated_fields & STATUS_FIELD_NAMES)


def _event_type_values(event: Mapping[str, Any]) -> list[Any]:
    values: list[Any] = []
    for source in _metadata_sources(event):
        for key in ("trigger", "action", "type", "webhookType", "webhook_type"):
            if key in source:
                values.append(source[key])
    return values


def _metadata_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources = [event]
    for key in ("triggerContext", "webhook", "payload"):
        value = event.get(key)
        if isinstance(value, Mapping):
            sources.append(value)
    return sources


def _updated_field_names(event: Mapping[str, Any]) -> set[str]:
    fields: set[str] = set()
    for source in _metadata_sources(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields.update(_field_names_from_value(source.get(key)))

        updated_from = source.get("updatedFrom") or source.get("updated_from")
        if isinstance(updated_from, Mapping):
            fields.update(_normalize_key(name) for name in updated_from)

    return fields


def _field_names_from_value(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {_normalize_key(value)}
    if isinstance(value, Mapping):
        return {_normalize_key(name) for name in value}
    if isinstance(value, (list, tuple, set)):
        return {_normalize_key(item) for item in value if isinstance(item, str)}
    return set()


def _extract_new_status(event: Mapping[str, Any], issue: Mapping[str, Any]) -> str | None:
    for source in (*_metadata_sources(event), issue):
        status = _first_value(source, "newStatus", "new_status", "newState", "new_state", "statusName", "status_name")
        if status:
            return _clean_text(status)

    for source in (issue, _mapping_value(event, "data"), event):
        status = _status_name_from_mapping(source)
        if status:
            return status

    return None


def _status_name_from_mapping(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for key in ("state", "workflowState", "workflow_state", "status"):
        status = value.get(key)
        if isinstance(status, Mapping):
            name = _first_value(status, "name", "title")
            if name:
                return _clean_text(name)
        elif status:
            return _clean_text(status)

    return None


def _mapping_value(mapping: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else {}


def _first_value(mapping: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return None


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_phrase(value: Any) -> str | None:
    text = _clean_text(value)
    if text is None:
        return None
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _normalize_event_name(value: Any) -> str:
    normalized = _normalize_phrase(value)
    return "" if normalized is None else normalized.replace(" ", "")


def _normalize_key(value: Any) -> str:
    normalized = _normalize_phrase(value)
    return "" if normalized is None else normalized.replace(" ", "")


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
