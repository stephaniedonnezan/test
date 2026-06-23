"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
)
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "statusName",
    "status_name",
    "status",
    "state",
    "workflowState",
    "workflow_state",
)
_TITLE_KEYS = ("title", "name", "summary")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_STATUS_FIELD_COMPACT_NAMES = {"status", "state", "workflowstate", "workflowstatus"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to To Research.

    Cursor automations provide a flat ``triggerContext`` payload, while Linear
    webhooks commonly nest issue details under ``data.issue``. This function
    accepts both shapes and returns ``None`` for events that should not update
    the issue title.
    """

    if not isinstance(event, Mapping):
        return None

    records = list(_records_from_event(event))
    if not _is_status_change_event(records):
        return None

    new_status = _extract_new_status(records)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    title = _extract_first_text(records, _TITLE_KEYS)
    if not title or _has_research_prefix(title):
        return None

    issue_id = _extract_issue_id(records)
    if not issue_id:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _records_from_event(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely metadata and issue records in priority order."""

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    event_issue = event.get("issue")
    data_issue = data.get("issue") if isinstance(data, Mapping) else None

    for candidate in (trigger_context, data_issue, event_issue, data, event):
        if isinstance(candidate, Mapping):
            yield candidate


def _is_status_change_event(records: list[Mapping[str, Any]]) -> bool:
    if any(
        _is_direct_status_change_marker(record.get(key))
        for record in records
        for key in _TRIGGER_KEYS
        if key in record
    ):
        return True

    has_update_marker = any(
        _is_update_marker(record.get(key))
        for record in records
        for key in _TRIGGER_KEYS
        if key in record
    )
    return has_update_marker and _updated_fields_include_status(records)


def _is_direct_status_change_marker(value: Any) -> bool:
    normalized = _normalize(value)
    compact = normalized.replace(" ", "")
    return compact in {"statuschanged", "statuschange"} or (
        "status" in normalized and "changed" in normalized
    )


def _is_update_marker(value: Any) -> bool:
    compact = _normalize(value).replace(" ", "")
    return compact in {"update", "updated", "issueupdate", "issueupdated", "updatedissue"}


def _updated_fields_include_status(records: list[Mapping[str, Any]]) -> bool:
    for record in records:
        for key in _UPDATED_FIELD_KEYS:
            if _contains_status_field(record.get(key)):
                return True

        changes = record.get("changes")
        if isinstance(changes, Mapping) and any(_is_status_field(key) for key in changes):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            _is_status_field(key) or _contains_status_field(item)
            for key, item in value.items()
        )

    if isinstance(value, (list, tuple, set)):
        return any(_contains_status_field(item) for item in value)

    return _is_status_field(value)


def _is_status_field(value: Any) -> bool:
    return _normalize(value).replace(" ", "") in _STATUS_FIELD_COMPACT_NAMES


def _extract_new_status(records: list[Mapping[str, Any]]) -> str:
    for record in records:
        changes = record.get("changes")
        if isinstance(changes, Mapping):
            for field, change in changes.items():
                if _is_status_field(field):
                    changed_status = _extract_changed_value(change)
                    if changed_status:
                        return changed_status

    return _extract_first_text(records, _NEW_STATUS_KEYS)


def _extract_changed_value(value: Any) -> str:
    if not isinstance(value, Mapping):
        return _as_text(value)

    for key in ("to", "toValue", "to_value", "new", "newValue", "new_value", "after", "current"):
        if key in value:
            text = _as_text(value[key])
            if text:
                return text

    return _as_text(value)


def _extract_first_text(records: list[Mapping[str, Any]], keys: Iterable[str]) -> str:
    for record in records:
        for key in keys:
            if key in record:
                text = _as_text(record[key])
                if text:
                    return text
    return ""


def _extract_issue_id(records: list[Mapping[str, Any]]) -> str:
    return _extract_first_text(records, _ISSUE_ID_KEYS)


def _as_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value", "id", "identifier", "key"):
            if key in value:
                text = _as_text(value[key])
                if text:
                    return text
        return ""

    return str(value).strip()


def _normalize(value: Any) -> str:
    text = _as_text(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return text.casefold().strip()


def _has_research_prefix(title: str) -> bool:
    return title.lstrip().casefold().startswith(TITLE_PREFIX.casefold())


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
