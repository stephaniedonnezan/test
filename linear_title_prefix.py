"""Build Linear issue title update actions for research-status transitions.

The module is intentionally side-effect free: it reads a webhook/automation
event and returns the title update a caller should apply through Linear.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_STATUS = "to research"
RESEARCH_TITLE_PREFIX = "Cursor researching"

_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_PREFIX_RE = re.compile(r"^\s*cursor\s+researching\b", re.IGNORECASE)
_STATUS_FIELD_TOKENS = {"status", "state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue enters research.

    The returned object is suitable for automation code that performs the
    actual Linear API call:
    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _find_status(event)
    if _normalize_status(new_status) != RESEARCH_STATUS:
        return None

    issue_id = _find_issue_id(event)
    title = _find_title(event)
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{RESEARCH_TITLE_PREFIX}: {title.strip()}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    if any(_is_direct_status_change_value(value) for value in _event_type_values(event)):
        return True

    if _updated_fields_include_status(event):
        return any(_is_generic_issue_update_value(value) for value in _event_type_values(event))

    return False


def _event_type_values(event: Mapping[str, Any]) -> Iterable[Any]:
    for mapping in _priority_mappings(event):
        for key in ("trigger", "action", "type", "eventType", "webhookType"):
            if key in mapping:
                yield mapping[key]


def _is_direct_status_change_value(value: Any) -> bool:
    token = _normalize_token(value)
    if not token:
        return False

    if token in {
        "statuschanged",
        "statuschange",
        "statechanged",
        "statechange",
        "workflowstatechanged",
        "workflowstatechange",
    }:
        return True

    return (
        ("status" in token or "state" in token)
        and ("changed" in token or "change" in token)
    )


def _is_generic_issue_update_value(value: Any) -> bool:
    token = _normalize_token(value)
    return token in {"update", "updated", "issueupdate", "issueupdated", "updatedissue"}


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for mapping in _iter_mappings(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = mapping.get(key)
            if isinstance(fields, str) and _is_status_field(fields):
                return True
            if isinstance(fields, Iterable) and not isinstance(fields, (str, bytes, Mapping)):
                if any(_is_status_field(field) for field in fields):
                    return True

        for key in ("changes", "changed"):
            changes = mapping.get(key)
            if isinstance(changes, Mapping):
                if any(_is_status_field(field) for field in changes):
                    return True
            elif isinstance(changes, Iterable) and not isinstance(changes, (str, bytes)):
                if any(_is_status_field(field) for field in changes):
                    return True

    return False


def _is_status_field(value: Any) -> bool:
    return _normalize_token(value) in _STATUS_FIELD_TOKENS


def _find_status(event: Mapping[str, Any]) -> str | None:
    for mapping in _priority_mappings(event):
        for key in (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "newStateName",
            "new_state_name",
            "newWorkflowState",
            "new_workflow_state",
            "newWorkflowStateName",
            "new_workflow_state_name",
            "statusName",
            "status_name",
            "stateName",
            "state_name",
            "workflowStateName",
            "workflow_state_name",
        ):
            status = _coerce_status(mapping.get(key))
            if status:
                return status

    for mapping in _iter_mappings(event):
        for key in ("changes", "changed"):
            changes = mapping.get(key)
            if isinstance(changes, Mapping):
                for field, value in changes.items():
                    if _is_status_field(field):
                        status = _coerce_status(value)
                        if status:
                            return status

    for mapping in _priority_mappings(event):
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _coerce_status(mapping.get(key))
            if status:
                return status

    return None


def _coerce_status(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if isinstance(value, Mapping):
        for key in ("name", "newValue", "new_value", "new", "to", "after", "status", "state"):
            status = _coerce_status(value.get(key))
            if status:
                return status

    return None


def _find_issue_id(event: Mapping[str, Any]) -> str | None:
    return _find_string_value(event, ("issueId", "issue_id", "identifier", "key", "id"))


def _find_title(event: Mapping[str, Any]) -> str | None:
    return _find_string_value(event, ("title",))


def _find_string_value(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for mapping in _priority_mappings(event):
        for key in keys:
            value = mapping.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    return None


def _priority_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    mappings: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and not any(value is existing for existing in mappings):
            mappings.append(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")

    add(trigger_context)
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("issue"))
        add(trigger_context.get("data"))

    add(event)

    if isinstance(data, Mapping):
        add(data.get("issue"))
    add(issue)
    add(data)

    return mappings


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested in value.values():
            yield from _iter_mappings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _iter_mappings(nested)


def _has_research_prefix(title: str) -> bool:
    return bool(_PREFIX_RE.match(title))


def _normalize_status(value: Any) -> str:
    if value is None:
        return ""

    spaced = _CAMEL_BOUNDARY_RE.sub(" ", str(value))
    words = re.sub(r"[^A-Za-z0-9]+", " ", spaced).casefold().split()
    return " ".join(words)


def _normalize_token(value: Any) -> str:
    if value is None:
        return ""

    spaced = _CAMEL_BOUNDARY_RE.sub(" ", str(value))
    return re.sub(r"[^A-Za-z0-9]+", "", spaced).casefold()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
