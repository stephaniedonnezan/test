"""Build Linear issue-title updates for Cursor research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newStatusName",
    "new_status_name",
    "toStatus",
    "to_status",
    "afterStatus",
    "after_status",
)
_CURRENT_STATUS_KEYS = (
    "status",
    "statusName",
    "status_name",
    "state",
    "stateName",
    "state_name",
    "workflowState",
    "workflow_state",
)
_STATUS_CHANGE_FIELD_NAMES = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
    "workflowstatus",
    "workflowstatusid",
}
_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statusupdated",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}
_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue-title update action when the event enters research."""

    if not isinstance(event, Mapping):
        return None

    if not _is_research_status_change(event):
        return None

    title = _first_text(_candidate_contexts(event), ("title", "name"))
    issue_id = _first_text(
        _candidate_contexts(event),
        ("issueId", "issue_id", "identifier", "key", "id"),
    )

    if not title or not issue_id:
        return None

    stripped_title = title.strip()
    if stripped_title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {stripped_title}",
    }


def _is_research_status_change(event: Mapping[str, Any]) -> bool:
    status = _new_status(event)
    if _normalize_status(status) != TARGET_STATUS:
        return False

    if _has_direct_status_change_trigger(event):
        return True

    if _has_generic_update_trigger(event) and _has_status_change_metadata(event):
        return True

    return False


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            contexts.append(issue)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        contexts.append(issue)

    if isinstance(data, Mapping):
        contexts.append(data)

    contexts.append(event)
    return contexts


def _new_status(event: Mapping[str, Any]) -> str | None:
    contexts = _candidate_contexts(event)
    status = _first_status_value(contexts, _EXPLICIT_STATUS_KEYS)
    if status:
        return status

    status = _status_from_change_maps(contexts)
    if status:
        return status

    return _first_status_value(contexts, _CURRENT_STATUS_KEYS)


def _first_status_value(
    contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]
) -> str | None:
    for key in keys:
        for context in contexts:
            if key not in context:
                continue
            value = _status_text(context[key])
            if value:
                return value
    return None


def _status_from_change_maps(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in ("changes", "changedFields", "change"):
            changes = context.get(key)
            if not isinstance(changes, Mapping):
                continue
            for field_name, value in changes.items():
                if not _is_status_change_field(str(field_name)):
                    continue
                status = _status_text_from_change(value)
                if status:
                    return status
    return None


def _status_text_from_change(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "new", "after", "newValue", "new_value", "value", "name"):
            status = _status_text(value.get(key))
            if status:
                return status
    return _status_text(value)


def _has_direct_status_change_trigger(event: Mapping[str, Any]) -> bool:
    return any(
        _trigger_token(value) in _DIRECT_STATUS_CHANGE_TRIGGERS
        for value in _trigger_values(event)
    )


def _has_generic_update_trigger(event: Mapping[str, Any]) -> bool:
    return any(
        _trigger_token(value) in _GENERIC_UPDATE_TRIGGERS for value in _trigger_values(event)
    )


def _trigger_values(event: Mapping[str, Any]) -> Iterable[Any]:
    for context in _candidate_contexts(event):
        for key in ("trigger", "webhookType", "action", "event", "eventType", "type"):
            if key in context:
                yield context[key]


def _has_status_change_metadata(event: Mapping[str, Any]) -> bool:
    for context in _candidate_contexts(event):
        for key in ("updatedFields", "changedFields", "fields"):
            fields = context.get(key)
            if isinstance(fields, str) and _is_status_change_field(fields):
                return True
            if isinstance(fields, Iterable) and not isinstance(fields, (str, bytes, Mapping)):
                for field in fields:
                    if _is_status_change_field(_field_name(field)):
                        return True

        for key in ("changes", "change", "updatedFrom", "previousValues", "previous_values"):
            changes = context.get(key)
            if isinstance(changes, Mapping):
                if any(_is_status_change_field(str(field)) for field in changes):
                    return True

    return False


def _field_name(field: Any) -> str:
    if isinstance(field, Mapping):
        for key in ("name", "field", "key"):
            value = field.get(key)
            if value:
                return str(value)
    return str(field)


def _is_status_change_field(field_name: str) -> bool:
    return _field_token(field_name) in _STATUS_CHANGE_FIELD_NAMES


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for key in keys:
        for context in contexts:
            value = context.get(key)
            text = _plain_text(value)
            if text:
                return text
    return None


def _plain_text(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value"):
            text = _status_text(value.get(key))
            if text:
                return text
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


def _normalize_status(value: str | None) -> str:
    if not value:
        return ""
    with_spaces = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", with_spaces).strip().lower()
    return re.sub(r"\s+", " ", normalized)


def _trigger_token(value: Any) -> str:
    text = _status_text(value) or ""
    return re.sub(r"[^a-z0-9]+", "", _normalize_status(text))


def _field_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is None:
        return 1
    print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
