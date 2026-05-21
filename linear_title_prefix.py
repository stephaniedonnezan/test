"""Build Linear issue title updates for research-status automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflow status"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when an issue moves to "to research"."""
    if not isinstance(event, Mapping):
        return None

    sources = _event_sources(event)
    if not _is_status_change_event(sources):
        return None

    status = _extract_status(sources)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(sources)
    title = _extract_title(sources)
    if issue_id is None or title is None:
        return None

    normalized_issue_id = str(issue_id).strip()
    normalized_title = str(title).strip()
    if not normalized_issue_id or not normalized_title:
        return None

    if normalized_title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": normalized_issue_id,
        "title": f"{TITLE_PREFIX}: {normalized_title}",
    }


def _event_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect likely issue and metadata objects from flat or nested payloads."""
    sources: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in sources:
            sources.append(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")
    payload = event.get("payload")

    add(trigger_context)
    add(issue)
    if isinstance(data, Mapping):
        add(data.get("issue"))
    if isinstance(payload, Mapping):
        add(payload.get("issue"))
    add(data)
    add(payload)
    add(event)

    return sources


def _is_status_change_event(sources: list[Mapping[str, Any]]) -> bool:
    for source in sources:
        for key in ("trigger", "webhookType", "action", "type", "eventType"):
            normalized_value = _normalize_words(source.get(key))
            compact_value = normalized_value.replace(" ", "")
            if compact_value in {
                "statuschanged",
                "statuschange",
                "statechanged",
                "statechange",
                "workflowstatechanged",
                "workflowstatuschanged",
            }:
                return True

    if _is_issue_update_event(sources):
        return _changed_fields_include_status(sources)

    return False


def _is_issue_update_event(sources: list[Mapping[str, Any]]) -> bool:
    for source in sources:
        for key in ("trigger", "webhookType", "action", "type", "eventType"):
            normalized_value = _normalize_words(source.get(key))
            if normalized_value in {"update", "updated", "issue updated", "updated issue"}:
                return True
    return False


def _changed_fields_include_status(sources: list[Mapping[str, Any]]) -> bool:
    for source in sources:
        for key in (
            "updatedFields",
            "changedFields",
            "updated_fields",
            "changed_fields",
            "updatedProperties",
            "changedProperties",
        ):
            if any(_normalize_words(field) in STATUS_FIELD_NAMES for field in _field_names(source.get(key))):
                return True
    return False


def _field_names(value: Any) -> Iterable[Any]:
    if value is None:
        return ()
    if isinstance(value, Mapping):
        return value.keys()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Iterable):
        names: list[Any] = []
        for item in value:
            if isinstance(item, Mapping):
                names.extend(item.get(key) for key in ("name", "key", "field"))
            else:
                names.append(item)
        return names
    return ()


def _extract_status(sources: list[Mapping[str, Any]]) -> Any:
    explicit_status_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowStatus",
        "new_workflow_status",
        "newWorkflowState",
        "new_workflow_state",
        "toStatus",
        "to_status",
        "toState",
        "to_state",
    )
    for source in sources:
        status = _first_present(source, explicit_status_keys)
        if status is not None:
            return _name_or_value(status)

    for source in sources:
        for key in ("state", "workflowState", "workflow_status", "workflowStatus", "status"):
            status = source.get(key)
            if status is not None:
                return _name_or_value(status)

    return None


def _extract_issue_id(sources: list[Mapping[str, Any]]) -> Any:
    for source in sources:
        issue_id = _first_present(source, ("issueId", "issue_id", "identifier", "id", "uuid"))
        if issue_id is not None:
            return issue_id
    return None


def _extract_title(sources: list[Mapping[str, Any]]) -> Any:
    for source in sources:
        title = source.get("title")
        if title is not None:
            return title
    return None


def _first_present(source: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = source.get(key)
        if value is not None:
            return value
    return None


def _name_or_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _first_present(value, ("name", "title", "label", "value", "id"))
    return value


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
