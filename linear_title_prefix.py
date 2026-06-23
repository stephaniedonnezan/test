"""Linear issue title automation for research status transitions.

The public entrypoint is ``build_issue_title_update``. It accepts either the
flat Cursor automation trigger payload or a nested Linear webhook-style payload
and returns an update action when the issue has just moved to "to research".
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Build a title update action for Linear issues entering "to research".

    Returns:
        ``{"action": "update_issue_title", "issueId": ..., "title": ...}``
        when the payload represents a status change to "to research"; otherwise
        ``None``.
    """

    if not isinstance(event, Mapping):
        return None

    candidates = list(_candidate_mappings(event))
    if not _is_status_change_event(candidates):
        return None

    status = _extract_new_status(candidates)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(candidates, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _extract_first_text(candidates, ("title", "name"))
    if issue_id is None or title is None:
        return None

    stripped_title = title.strip()
    if not stripped_title:
        return None

    if _already_prefixed(stripped_title):
        new_title = stripped_title
    else:
        new_title = f"{PREFIX}: {stripped_title}"

    return {"action": "update_issue_title", "issueId": issue_id.strip(), "title": new_title}


def handle_issue_status_changed(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Compatibility alias for automation runtimes that call this name."""

    return build_issue_title_update(event)


def _candidate_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return useful payload layers from outermost metadata to nested issue data."""

    candidates: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in candidates:
            candidates.append(value)

    add(event)
    add(event.get("triggerContext"))
    add(event.get("issue"))

    data = event.get("data")
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("state"))
        add(data.get("workflowState"))

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("data"))
        add(trigger_context.get("issue"))

    return candidates


def _is_status_change_event(candidates: list[Mapping[str, Any]]) -> bool:
    event_names = _event_names(candidates)
    if any(_is_direct_status_change_name(name) for name in event_names):
        return True

    if _updated_fields_include_status(candidates):
        return True

    return any(_change_mapping_includes_status(candidate) for candidate in candidates)


def _event_names(candidates: list[Mapping[str, Any]]) -> list[str]:
    names: list[str] = []
    for candidate in candidates:
        for key in ("trigger", "webhookType", "action", "type"):
            value = candidate.get(key)
            if isinstance(value, str):
                names.append(value)
    return names


def _is_direct_status_change_name(name: str) -> bool:
    compact = _normalize_compact(name)
    return compact in {
        "statuschanged",
        "statuschange",
        "statusupdated",
        "statechanged",
        "statechange",
        "workflowstatechanged",
        "workflowstatechange",
    }


def _updated_fields_include_status(candidates: list[Mapping[str, Any]]) -> bool:
    for candidate in candidates:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = candidate.get(key)
            if _field_collection_includes_status(fields):
                return True
    return False


def _field_collection_includes_status(fields: Any) -> bool:
    if isinstance(fields, str):
        return _is_status_field_name(fields)
    if isinstance(fields, Mapping):
        return any(_is_status_field_name(str(key)) for key in fields)
    if isinstance(fields, list | tuple | set):
        return any(_is_status_field_name(str(field)) for field in fields)
    return False


def _change_mapping_includes_status(candidate: Mapping[str, Any]) -> bool:
    for key in ("changes", "changed", "updatedFrom", "updated_from"):
        changes = candidate.get(key)
        if isinstance(changes, Mapping) and any(_is_status_field_name(str(field)) for field in changes):
            return True
    return False


def _is_status_field_name(value: str) -> bool:
    return _normalize_compact(value) in _STATUS_FIELD_NAMES


def _extract_new_status(candidates: list[Mapping[str, Any]]) -> str | None:
    for candidate in candidates:
        for key in _NEW_STATUS_KEYS:
            status = _text_or_name(candidate.get(key))
            if status is not None:
                return status

    for candidate in candidates:
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _text_or_name(candidate.get(key))
            if status is not None:
                return status

    return None


def _extract_first_text(candidates: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        for key in keys:
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "id"):
            nested = value.get(key)
            if isinstance(nested, str):
                return nested
    return None


def _normalize_words(value: str | None) -> str | None:
    if value is None:
        return None
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    spaced = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return " ".join(spaced.lower().split())


def _normalize_compact(value: str) -> str:
    normalized = _normalize_words(value)
    return "" if normalized is None else normalized.replace(" ", "")


def _already_prefixed(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
