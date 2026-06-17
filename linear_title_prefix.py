"""Build Linear issue title updates for Cursor research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}
_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
    "workflowstate changed",
    "workflowstate change",
}
_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action for Linear moves into To Research.

    The automation runner can pass either the flat Cursor ``triggerContext``
    payload or a nested Linear webhook payload. The function returns a small
    action object and leaves actually calling Linear to the caller.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize_text(_new_status(event)) != TARGET_STATUS:
        return None

    issue_id = _first_string_value(_issue_sources(event), ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_string_value(_issue_sources(event), ("title", "name"))
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_names = {_normalize_text(value) for value in _trigger_values(event)}
    trigger_names.discard("")

    if trigger_names & _DIRECT_STATUS_CHANGE_TRIGGERS:
        return True

    if trigger_names & _GENERIC_UPDATE_TRIGGERS:
        return _has_status_change_metadata(event) or _has_explicit_new_status(event)

    return False


def _trigger_values(event: Mapping[str, Any]) -> Iterable[Any]:
    for source in _metadata_sources(event):
        for key in ("trigger", "action", "event", "eventType", "type", "webhookType"):
            if key in source:
                yield source[key]


def _metadata_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []
    for value in (event, event.get("triggerContext"), event.get("data")):
        if isinstance(value, Mapping):
            sources.append(value)
    return sources


def _new_status(event: Mapping[str, Any]) -> Any:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "statusName",
        "stateName",
        "workflowStateName",
    )

    value = _first_value(_all_sources(event), explicit_keys)
    if value is not None:
        return _name_like_value(value)

    value = _status_from_change_maps(event)
    if value is not None:
        return _name_like_value(value)

    for source in _issue_sources(event):
        value = _first_value((source,), ("status", "state", "workflowState", "workflow_state"))
        if value is not None:
            return _name_like_value(value)

    return None


def _has_explicit_new_status(event: Mapping[str, Any]) -> bool:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "statusName",
        "stateName",
        "workflowStateName",
    )
    return _first_value(_all_sources(event), explicit_keys) is not None


def _status_from_change_maps(event: Mapping[str, Any]) -> Any:
    for source in _all_sources(event):
        for key in ("changes", "change", "updated"):
            changes = source.get(key)
            if not isinstance(changes, Mapping):
                continue
            for field_name, change in changes.items():
                if _normalize_field_name(field_name) not in _STATUS_FIELD_NAMES:
                    continue
                if isinstance(change, Mapping):
                    for value_key in ("to", "new", "after", "current", "name", "title"):
                        if change.get(value_key) is not None:
                            return change[value_key]
                elif change is not None:
                    return change
    return None


def _has_status_change_metadata(event: Mapping[str, Any]) -> bool:
    for source in _all_sources(event):
        for key in ("updatedFields", "changedFields", "changed_fields", "fields"):
            fields = source.get(key)
            if _contains_status_field(fields):
                return True

        for key in ("changes", "change", "updated", "updatedFrom", "previous"):
            changes = source.get(key)
            if isinstance(changes, Mapping) and any(
                _normalize_field_name(field) in _STATUS_FIELD_NAMES for field in changes
            ):
                return True

    return False


def _contains_status_field(fields: Any) -> bool:
    if isinstance(fields, str):
        return _normalize_field_name(fields) in _STATUS_FIELD_NAMES

    if isinstance(fields, Mapping):
        field_name = fields.get("name") or fields.get("field") or fields.get("key")
        return _normalize_field_name(field_name) in _STATUS_FIELD_NAMES

    if isinstance(fields, Iterable):
        return any(_contains_status_field(field) for field in fields)

    return False


def _issue_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []
    trigger_context = event.get("triggerContext")
    data = event.get("data")

    for value in (
        trigger_context,
        event.get("issue"),
        data.get("issue") if isinstance(data, Mapping) else None,
        data,
        event,
    ):
        if isinstance(value, Mapping) and value not in sources:
            sources.append(value)

    return sources


def _all_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []
    for value in (event, event.get("triggerContext"), event.get("issue"), event.get("data")):
        if isinstance(value, Mapping) and value not in sources:
            sources.append(value)
            issue = value.get("issue")
            if isinstance(issue, Mapping) and issue not in sources:
                sources.append(issue)
    return sources


def _first_string_value(sources: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    value = _first_value(sources, keys)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _first_value(sources: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> Any:
    for source in sources:
        for key in keys:
            value = source.get(key)
            if value is not None:
                return value
    return None


def _name_like_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _first_value((value,), ("name", "title", "label", "status", "state"))
    return value


def _has_research_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(TITLE_PREFIX)}\b", title, flags=re.IGNORECASE) is not None


def _normalize_field_name(value: Any) -> str:
    return _normalize_text(value).replace(" ", "")


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    json.dump(update, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
