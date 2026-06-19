"""Build title-update actions for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}
_DIRECT_STATUS_CHANGE_EVENTS = {
    "status change",
    "status changed",
    "issue status change",
    "issue status changed",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research.

    The automation trigger can arrive as a flat Cursor ``triggerContext`` payload
    or as a nested Linear webhook payload. Non-matching events return ``None`` so
    callers can safely skip downstream Linear API calls.
    """

    if not isinstance(event, Mapping):
        return None

    candidates = _collect_mappings(event)
    if not _is_status_change_event(candidates):
        return None

    new_status = _extract_new_status(candidates)
    if _normalize_value(new_status) != _normalize_value(RESEARCH_STATUS):
        return None

    issue_id = _extract_issue_id(candidates)
    title = _extract_title(candidates)
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _collect_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect likely webhook context maps from outer to inner priority."""

    candidates: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        identity = id(value)
        if identity in seen:
            return
        seen.add(identity)
        candidates.append(value)

        for key in (
            "triggerContext",
            "payload",
            "data",
            "issue",
            "resource",
            "object",
            "node",
            "state",
            "workflowState",
            "status",
        ):
            visit(value.get(key))

    visit(event)
    return candidates


def _is_status_change_event(candidates: Iterable[Mapping[str, Any]]) -> bool:
    saw_generic_update = False

    for candidate in candidates:
        for key in ("trigger", "webhookType", "eventType", "action", "type"):
            normalized = _normalize_value(candidate.get(key))
            if not normalized:
                continue
            if normalized in _DIRECT_STATUS_CHANGE_EVENTS:
                return True
            if "status" in normalized and ("change" in normalized or "changed" in normalized):
                return True
            if normalized in _GENERIC_UPDATE_EVENTS:
                saw_generic_update = True

    return saw_generic_update and _status_field_changed(candidates)


def _status_field_changed(candidates: Iterable[Mapping[str, Any]]) -> bool:
    for candidate in candidates:
        for key in ("updatedFields", "changedFields"):
            if _field_list_includes_status(candidate.get(key)):
                return True

        for key in ("changes", "changed", "updated"):
            if _changes_include_status(candidate.get(key)):
                return True

        field = candidate.get("field") or candidate.get("fieldName") or candidate.get("name")
        if _is_status_field(field):
            return True

    return False


def _field_list_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        return any(_is_status_field(field) for field in value)

    if isinstance(value, Iterable):
        for item in value:
            if isinstance(item, Mapping):
                field = item.get("field") or item.get("fieldName") or item.get("name")
                if _is_status_field(field):
                    return True
            elif _is_status_field(item):
                return True

    return False


def _changes_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value)

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for item in value:
            if isinstance(item, Mapping):
                field = item.get("field") or item.get("fieldName") or item.get("name")
                if _is_status_field(field):
                    return True

    return False


def _extract_new_status(candidates: Iterable[Mapping[str, Any]]) -> str | None:
    explicit_status_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "newWorkflowStateName",
        "new_workflow_state_name",
        "statusName",
        "stateName",
    )

    for candidate in candidates:
        value = _first_string_value(candidate, explicit_status_keys)
        if value:
            return value

    for candidate in candidates:
        value = _status_from_changes(candidate.get("changes"))
        if value:
            return value

    for candidate in candidates:
        for key in ("status", "state", "workflowState"):
            value = _string_or_named_value(candidate.get(key))
            if value:
                return value

    return None


def _status_from_changes(changes: Any) -> str | None:
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _is_status_field(key):
                return _string_or_named_value_from_keys(
                    value,
                    ("newValue", "new_value", "to", "after", "value", "name"),
                )

    if isinstance(changes, Iterable) and not isinstance(changes, (str, bytes)):
        for item in changes:
            if not isinstance(item, Mapping):
                continue
            field = item.get("field") or item.get("fieldName") or item.get("name")
            if _is_status_field(field):
                value = _string_or_named_value_from_keys(
                    item,
                    ("newValue", "new_value", "to", "after", "value"),
                )
                if value:
                    return value

    return None


def _extract_issue_id(candidates: Iterable[Mapping[str, Any]]) -> str | None:
    for candidate in candidates:
        value = _first_string_value(
            candidate,
            ("issueId", "issue_id", "identifier", "key", "id"),
        )
        if value:
            return value
    return None


def _extract_title(candidates: Iterable[Mapping[str, Any]]) -> str | None:
    for candidate in candidates:
        value = _first_string_value(candidate, ("title", "issueTitle", "issue_title"))
        if value:
            return value
    return None


def _first_string_value(mapping: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _string_or_named_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    return _string_or_named_value_from_keys(value, ("name", "title"))


def _string_or_named_value_from_keys(value: Any, keys: Iterable[str]) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in keys:
            if key not in value:
                continue
            nested_value = _string_or_named_value(value.get(key))
            if nested_value:
                return nested_value

    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _is_status_field(value: Any) -> bool:
    return _normalize_value(value) in _STATUS_FIELD_NAMES


def _normalize_value(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    with_spaces = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    with_spaces = re.sub(r"[_\-/]+", " ", with_spaces)
    return re.sub(r"\s+", " ", with_spaces).strip().casefold()


def main() -> int:
    """Read a JSON event from stdin and print the update action, if any."""

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 2

    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
