"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
    "issue status changed",
    "issue state changed",
}
_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_TRIGGER_KEYS = (
    "trigger",
    "webhookType",
    "webhook_type",
    "action",
    "type",
    "event",
    "eventType",
    "event_type",
)
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "toStatus",
    "to_status",
    "toState",
    "to_state",
)
_STATUS_KEYS = (
    "status",
    "state",
    "workflowState",
    "workflow_state",
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to to research.

    The Cursor automation payload is flat under ``triggerContext`` while Linear
    webhooks commonly nest the issue under ``data.issue``. This function accepts
    both shapes and returns ``None`` for non-matching events.
    """

    if not isinstance(event, Mapping):
        return None

    maps = list(_candidate_maps(event))
    if not _is_status_change_event(maps):
        return None

    if _normalize_text(_find_new_status(maps)) != TARGET_STATUS:
        return None

    issue_id = _find_issue_id(maps)
    title = _find_title(maps)
    if not issue_id or not title:
        return None

    title = title.strip()
    if _normalize_text(title).startswith(_normalize_text(PREFIX)):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _candidate_maps(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield useful event maps from outermost trigger metadata to issue data."""

    yield event

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield trigger_context

    data = event.get("data")
    if isinstance(data, Mapping):
        yield data
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            yield issue

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue

    payload = event.get("payload")
    if isinstance(payload, Mapping):
        yield payload


def _is_status_change_event(maps: Sequence[Mapping[str, Any]]) -> bool:
    triggers = {_normalize_text(value) for item in maps for value in _trigger_values(item)}
    if triggers & _DIRECT_STATUS_TRIGGERS:
        return True

    if triggers & _GENERIC_UPDATE_TRIGGERS:
        return any(_mentions_status_change(item) for item in maps)

    return False


def _trigger_values(item: Mapping[str, Any]) -> Iterable[Any]:
    for key in _TRIGGER_KEYS:
        if key in item:
            yield item[key]


def _mentions_status_change(item: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = item.get(key)
        if _fields_mention_status(fields):
            return True

    for key in ("field", "changedField", "changed_field"):
        if _is_status_field(item.get(key)):
            return True

    for key in ("changes", "change", "changelog"):
        changes = item.get(key)
        if isinstance(changes, Mapping):
            if any(_is_status_field(field) for field in changes):
                return True
        elif _fields_mention_status(changes):
            return True

    return False


def _fields_mention_status(fields: Any) -> bool:
    if isinstance(fields, str):
        return _is_status_field(fields)
    if isinstance(fields, Mapping):
        return any(
            _is_status_field(key) or _is_status_field(value.get("field"))
            for key, value in fields.items()
            if isinstance(value, Mapping)
        ) or any(_is_status_field(key) for key in fields)
    if _is_iterable(fields):
        return any(
            _is_status_field(field.get("field") or field.get("name") or field.get("key"))
            if isinstance(field, Mapping)
            else _is_status_field(field)
            for field in fields
        )
    return False


def _is_status_field(value: Any) -> bool:
    normalized = _normalize_text(value)
    compact = normalized.replace(" ", "")
    return compact in {
        "status",
        "statusid",
        "state",
        "stateid",
        "workflowstate",
        "workflowstateid",
        "workflowstatus",
    }


def _find_new_status(maps: Sequence[Mapping[str, Any]]) -> str | None:
    for item in maps:
        for key in _NEW_STATUS_KEYS:
            if key in item:
                status = _status_text(item[key])
                if status:
                    return status

    for item in maps:
        status = _status_from_change_metadata(item)
        if status:
            return status

    for item in maps:
        for key in _STATUS_KEYS:
            if key in item:
                status = _status_text(item[key])
                if status:
                    return status

    return None


def _status_from_change_metadata(item: Mapping[str, Any]) -> str | None:
    for key in ("changes", "change", "changelog"):
        changes = item.get(key)
        if not isinstance(changes, Mapping):
            continue

        for field, change in changes.items():
            if not _is_status_field(field):
                continue
            status = _status_text(change)
            if status:
                return status

    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = item.get(key)
        if not _is_iterable(fields):
            continue

        for field in fields:
            if not isinstance(field, Mapping):
                continue
            field_name = field.get("field") or field.get("name") or field.get("key")
            if not _is_status_field(field_name):
                continue
            status = _status_text(field)
            if status:
                return status

    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        for key in (
            "to",
            "new",
            "newValue",
            "new_value",
            "after",
            "name",
            "title",
            "label",
            "status",
            "state",
            "workflowState",
            "workflow_state",
        ):
            if key in value:
                status = _status_text(value[key])
                if status:
                    return status
    return None


def _find_issue_id(maps: Sequence[Mapping[str, Any]]) -> str | None:
    for key in ("issueId", "issue_id", "identifier", "key", "id"):
        for item in maps:
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _find_title(maps: Sequence[Mapping[str, Any]]) -> str | None:
    for key in ("title", "name"):
        for item in maps:
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip().lower()


def _is_iterable(value: Any) -> bool:
    return isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping))


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
