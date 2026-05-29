"""Build title updates for Linear issues entering the research state."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action for status changes to To Research.

    The automation payload can be a flat Cursor trigger context or a nested
    Linear webhook payload. Non-matching events return ``None``.
    """

    if not isinstance(event, Mapping):
        return None

    sources = _source_mappings(event)
    if not _is_status_change_event(sources):
        return None

    status = _new_status(sources)
    if _normalize_value(status) != TARGET_STATUS:
        return None

    issue_id = _first_string(sources, ("issueId", "issue_id", "identifier", "id"))
    title = _first_string(sources, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _source_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload mappings in priority order from issue-specific to outer."""

    trigger_context = _mapping_value(event, "triggerContext")
    data = _mapping_value(event, "data")
    trigger_data = _mapping_value(trigger_context, "data") if trigger_context else None

    candidates = [
        _mapping_value(trigger_context, "issue") if trigger_context else None,
        _mapping_value(trigger_data, "issue") if trigger_data else None,
        _mapping_value(data, "issue") if data else None,
        _mapping_value(event, "issue"),
        trigger_data,
        data,
        trigger_context,
        event,
    ]

    sources: list[Mapping[str, Any]] = []
    for candidate in candidates:
        if candidate and candidate not in sources:
            sources.append(candidate)
    return sources


def _is_status_change_event(sources: Iterable[Mapping[str, Any]]) -> bool:
    event_values: list[str] = []
    updated_fields: list[str] = []

    for source in sources:
        for key in ("trigger", "webhookType", "triggerType", "action", "type"):
            value = source.get(key)
            if isinstance(value, str):
                event_values.append(value)
        updated_fields.extend(_updated_field_names(source))

    normalized_events = {_normalize_value(value) for value in event_values}
    if any(value in {"status changed", "statuschange", "status changed"} for value in normalized_events):
        return True
    if any(value in {"status changed", "status_changed"} for value in event_values):
        return True

    has_update_event = any(
        value in {"update", "updated", "issue updated", "updated issue"} for value in normalized_events
    )
    return has_update_event and any(_is_status_field(field) for field in updated_fields)


def _updated_field_names(source: Mapping[str, Any]) -> list[str]:
    fields: list[str] = []
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        value = source.get(key)
        if isinstance(value, Mapping):
            fields.extend(str(field) for field in value)
        elif isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            fields.extend(str(field) for field in value)

    changes = source.get("changes")
    if isinstance(changes, Mapping):
        fields.extend(str(field) for field in changes)

    updated_from = source.get("updatedFrom")
    if isinstance(updated_from, Mapping):
        fields.extend(str(field) for field in updated_from)

    return fields


def _new_status(sources: Iterable[Mapping[str, Any]]) -> str | None:
    for source in sources:
        status = _first_string(source, ("newStatus", "new_status", "statusName", "stateName"))
        if status:
            return status

    for source in sources:
        for key in ("state", "workflowState", "workflow_state", "status"):
            value = source.get(key)
            if isinstance(value, Mapping):
                name = _first_string(value, ("name", "title"))
                if name:
                    return name
            elif isinstance(value, str):
                return value

    return None


def _first_string(sources: Iterable[Mapping[str, Any]] | Mapping[str, Any], keys: Iterable[str]) -> str | None:
    if isinstance(sources, Mapping):
        source_iterable: Iterable[Mapping[str, Any]] = (sources,)
    else:
        source_iterable = sources

    for source in source_iterable:
        for key in keys:
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _mapping_value(source: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    value = source.get(key)
    return value if isinstance(value, Mapping) else None


def _normalize_value(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    spaced = re.sub(r"[-_]+", " ", spaced)
    return re.sub(r"\s+", " ", spaced).strip().lower()


def _is_status_field(field: str) -> bool:
    normalized = _normalize_value(field).replace(" ", "")
    return normalized in STATUS_FIELD_NAMES or normalized.endswith("stateid")


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    payload = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(payload)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
