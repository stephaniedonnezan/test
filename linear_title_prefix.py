"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

STATUS_FIELD_NAMES = {
    "status",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
    "workflowstatus",
    "workflowstatusid",
}

STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "state changed",
    "workflow state changed",
}

UPDATE_EVENTS = {
    "update",
    "updated",
    "issue",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue title update when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    candidates = _candidate_mappings(event)
    if not _is_status_change_event(candidates):
        return None

    new_status = _extract_status(candidates)
    if _normalize_label(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_string(candidates, ("id", "issueId", "issue_id", "identifier"))
    title = _extract_first_string(candidates, ("title", "name"))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if not clean_title or clean_title.casefold().startswith(TITLE_PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility alias for automation entry points named after the trigger."""

    return build_issue_title_update(event)


def _candidate_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely payload sections, ordered from issue details to outer metadata."""

    candidates: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and not any(value is candidate for candidate in candidates):
            candidates.append(value)

    for container in (event.get("triggerContext"), event.get("data"), event.get("issue")):
        if isinstance(container, Mapping):
            add(container.get("issue"))
            add(container.get("data"))
            add(container)

    add(event)
    return candidates


def _is_status_change_event(candidates: Iterable[Mapping[str, Any]]) -> bool:
    saw_update_event = False

    for candidate in candidates:
        for key in ("trigger", "event", "action", "type", "webhookType"):
            normalized_event = _normalize_label(candidate.get(key))
            if normalized_event in STATUS_CHANGE_EVENTS:
                return True
            if normalized_event in UPDATE_EVENTS:
                saw_update_event = True

    return saw_update_event and _updated_fields_include_status(candidates)


def _updated_fields_include_status(candidates: Iterable[Mapping[str, Any]]) -> bool:
    for candidate in candidates:
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
            "updatedFrom",
            "updated_from",
        ):
            if _fields_include_status(candidate.get(key)):
                return True
    return False


def _fields_include_status(value: Any) -> bool:
    if isinstance(value, str):
        return _field_name_indicates_status(value)

    if isinstance(value, Mapping):
        return any(_field_name_indicates_status(field) for field in value)

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
        for item in value:
            if _fields_include_status(item):
                return True

    return False


def _field_name_indicates_status(field: Any) -> bool:
    return isinstance(field, str) and _normalize_key(field) in STATUS_FIELD_NAMES


def _extract_status(candidates: Iterable[Mapping[str, Any]]) -> str | None:
    explicit_status = _extract_first_string(
        candidates,
        (
            "newStatus",
            "new_status",
            "statusName",
            "stateName",
            "workflowStateName",
            "workflowStatusName",
        ),
    )
    if explicit_status:
        return explicit_status

    for candidate in candidates:
        for key in ("status", "state", "workflowState", "workflow_state", "workflowStatus"):
            status = _status_name(candidate.get(key))
            if status:
                return status

    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested

    return None


def _extract_first_string(candidates: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for candidate in candidates:
        for key in keys:
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _normalize_label(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.casefold()).strip()


def _normalize_key(value: str) -> str:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[^a-z0-9]+", "", spaced.casefold())


def main() -> int:
    """Read a JSON payload from stdin and print the title update action."""

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
