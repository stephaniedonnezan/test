"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statechanged",
    "statechange",
}
_ISSUE_UPDATED_TRIGGERS = {
    "issueupdated",
    "updatedissue",
    "updateissue",
    "issueupdate",
}
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to to-research.

    The automation runner is expected to perform the returned action. Payloads
    from Linear can be flat or nested under keys such as ``triggerContext``,
    ``data``, or ``issue``, so this function normalizes those common shapes.
    """

    if not isinstance(event, Mapping):
        return None

    normalized = _merge_payload_sources(event)
    if not _is_status_change_event(normalized):
        return None

    if _normalize_status(_status_from_payload(normalized)) != TARGET_STATUS:
        return None

    issue_id = _first_text(normalized, ("issueId", "issue_id", "id", "identifier"))
    title = _first_text(normalized, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility alias for automation entrypoints using handler naming."""

    return build_issue_title_update(event)


def _merge_payload_sources(event: Mapping[str, Any]) -> dict[str, Any]:
    data = _mapping_at(event, "data")
    issue = _mapping_at(event, "issue")
    data_issue = _mapping_at(data, "issue")
    trigger_context = _mapping_at(event, "triggerContext")

    merged: dict[str, Any] = {}
    for source in (issue, data_issue, data, trigger_context, event):
        if source:
            merged.update(source)

    return merged


def _mapping_at(source: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if not isinstance(source, Mapping):
        return None

    value = source.get(key)
    return value if isinstance(value, Mapping) else None


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    ]
    normalized_triggers = {
        _normalize_token(value) for value in trigger_values if isinstance(value, str)
    }

    if normalized_triggers & _STATUS_CHANGE_TRIGGERS:
        return True

    if normalized_triggers & _ISSUE_UPDATED_TRIGGERS:
        return _updated_fields_include_status(payload.get("updatedFields")) or (
            _updated_fields_include_status(payload.get("changedFields"))
        )

    return False


def _updated_fields_include_status(updated_fields: Any) -> bool:
    if isinstance(updated_fields, Mapping):
        fields = updated_fields.keys()
    elif isinstance(updated_fields, str):
        fields = [updated_fields]
    elif isinstance(updated_fields, Sequence):
        fields = updated_fields
    else:
        return False

    for field in fields:
        if isinstance(field, Mapping):
            field_name = _first_text(field, ("name", "field", "key"))
        else:
            field_name = str(field)

        if _normalize_token(field_name) in _STATUS_FIELD_NAMES:
            return True

    return False


def _status_from_payload(payload: Mapping[str, Any]) -> Any:
    for key in ("newStatus", "new_status", "status", "state", "workflowState"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            name = _first_text(value, ("name", "title"))
            if name:
                return name
        elif value is not None:
            return value

    return None


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def _has_title_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    return _split_compound_words(value).casefold()


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    return re.sub(r"[^a-z0-9]", "", _split_compound_words(value).casefold())


def _split_compound_words(value: str) -> str:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    spaced = re.sub(r"[_\-\s]+", " ", spaced)
    return spaced.strip()
