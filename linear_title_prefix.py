"""Build Linear issue title updates for Cursor research-status automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "workflowstate",
    "state id",
    "stateid",
    "status id",
    "statusid",
    "workflow state id",
    "workflowstateid",
}

_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "state updated",
    "workflow state changed",
    "workflow state change",
    "workflow state updated",
}

_GENERIC_UPDATE_EVENTS = {
    "issue updated",
    "updated issue",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue moves to To Research.

    The function accepts the flat Cursor `triggerContext` payload shape as well as
    common nested Linear webhook shapes. It returns a small declarative action so
    the caller can perform the actual Linear API mutation.
    """

    if not isinstance(event, Mapping):
        return None

    sources = list(_iter_payload_sources(event))
    if not _is_status_change_event(sources):
        return None

    new_status = _extract_new_status(sources)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(sources, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _extract_first_text(sources, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _iter_payload_sources(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely payload layers, with trigger context before nested issue data."""

    seen: set[int] = set()

    def add(value: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            yield value

    yield from add(event)

    automation_info = event.get("automation_trigger_info") or event.get("automationTriggerInfo")
    yield from add(automation_info)

    trigger_context = event.get("triggerContext")
    yield from add(trigger_context)
    if isinstance(automation_info, Mapping):
        yield from add(automation_info.get("triggerContext"))

    data = event.get("data")
    yield from add(data)
    if isinstance(data, Mapping):
        yield from add(data.get("issue"))

    yield from add(event.get("issue"))


def _is_status_change_event(sources: Iterable[Mapping[str, Any]]) -> bool:
    source_list = list(sources)
    event_names = {
        _normalize(source.get(key))
        for source in source_list
        for key in ("trigger", "action", "type", "webhookType", "webhook_type")
    }
    event_names.discard("")

    if event_names & _STATUS_CHANGE_EVENTS:
        return True

    if event_names & _GENERIC_UPDATE_EVENTS:
        return _changed_fields_include_status(source_list)

    return False


def _changed_fields_include_status(sources: Iterable[Mapping[str, Any]]) -> bool:
    for source in sources:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _fields_include_status(source.get(key)):
                return True

        for key in ("changes", "updatedFrom", "updated_from", "previousValues", "previous_values"):
            changes = source.get(key)
            if isinstance(changes, Mapping) and _fields_include_status(changes.keys()):
                return True

    return False


def _fields_include_status(fields: Any) -> bool:
    if isinstance(fields, str):
        fields = [fields]

    if not isinstance(fields, Iterable):
        return False

    for field in fields:
        if _normalize(field) in _STATUS_FIELD_NAMES:
            return True

    return False


def _extract_new_status(sources: Iterable[Mapping[str, Any]]) -> str | None:
    source_list = list(sources)

    status = _extract_first_text(
        source_list,
        (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "statusName",
            "status_name",
            "stateName",
            "state_name",
            "workflowStateName",
            "workflow_state_name",
        ),
    )
    if status:
        return status

    status = _extract_status_from_changes(source_list)
    if status:
        return status

    for source in source_list:
        for key in ("state", "workflowState", "workflow_state", "status"):
            value = source.get(key)
            if isinstance(value, Mapping):
                status = _extract_first_text([value], ("name", "title"))
                if status:
                    return status
            elif isinstance(value, str) and value.strip():
                return value

    return None


def _extract_status_from_changes(sources: Iterable[Mapping[str, Any]]) -> str | None:
    for source in sources:
        changes = source.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for key, value in changes.items():
            if _normalize(key) not in _STATUS_FIELD_NAMES:
                continue

            if isinstance(value, Mapping):
                status = _extract_first_text([value], ("new", "to", "after", "name", "title"))
                if status:
                    return status
            elif isinstance(value, str) and value.strip():
                return value

    return None


def _extract_first_text(sources: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for source in sources:
        for key in keys:
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lstrip().lower().startswith(PREFIX.lower())


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()


def main() -> int:
    payload = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(payload), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
