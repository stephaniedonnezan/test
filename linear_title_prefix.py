"""Build title updates for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "toresearch"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    mappings = list(_candidate_mappings(event))
    if not _is_status_change_event(mappings):
        return None

    new_status = _new_status(mappings)
    if _compact(new_status) != TARGET_STATUS:
        return None

    issue_id = _issue_id(mappings)
    title = _issue_title(mappings)
    if issue_id is None or title is None:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _candidate_mappings(event: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    candidates: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in candidates:
            candidates.append(value)

    add(event.get("triggerContext"))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data)

    add(event.get("issue"))
    add(event)

    # A few Linear payloads carry status metadata in nested objects. Keep these
    # after issue-like mappings so issue id/title extraction remains stable.
    for mapping in tuple(candidates):
        add(mapping.get("state"))
        add(mapping.get("workflowState"))
        add(mapping.get("status"))

    return tuple(candidates)


def _is_status_change_event(mappings: list[Mapping[str, Any]]) -> bool:
    values = _values_for_keys(mappings, ("trigger", "webhookType", "action", "type"))
    if any(_is_direct_status_change(value) for value in values):
        return True

    if any(_is_issue_update(value) for value in values):
        return _updated_fields_include_status(mappings)

    return False


def _is_direct_status_change(value: Any) -> bool:
    compacted = _compact(value)
    return compacted in {
        "statuschanged",
        "statuschange",
        "statechanged",
        "statechange",
        "workflowstatechanged",
        "workflowstatechange",
    }


def _is_issue_update(value: Any) -> bool:
    compacted = _compact(value)
    return compacted in {"update", "issueupdated", "updatedissue"}


def _updated_fields_include_status(mappings: list[Mapping[str, Any]]) -> bool:
    for value in _values_for_keys(
        mappings,
        ("updatedFields", "updated_fields", "changedFields", "changed_fields", "changes"),
    ):
        for field_name in _field_names(value):
            compacted = _compact(field_name)
            if compacted in STATUS_FIELD_NAMES:
                return True
            if any(compacted.startswith(field) for field in STATUS_FIELD_NAMES):
                return True
    return False


def _field_names(value: Any) -> tuple[Any, ...]:
    if isinstance(value, Mapping):
        return tuple(value.keys())
    if isinstance(value, (list, tuple, set)):
        names: list[Any] = []
        for item in value:
            if isinstance(item, Mapping):
                names.extend(item.keys())
            else:
                names.append(item)
        return tuple(names)
    if isinstance(value, str):
        return tuple(part.strip() for part in value.split(","))
    return ()


def _new_status(mappings: list[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "toStatus",
        "to_status",
    )
    explicit = _first_string(mappings, explicit_keys)
    if explicit is not None:
        return explicit

    for key in ("state", "workflowState", "status"):
        for mapping in mappings:
            value = mapping.get(key)
            name = _name_from_status_value(value)
            if name is not None:
                return name

    return _first_string(mappings, ("status",))


def _name_from_status_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        name = value.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _issue_id(mappings: list[Mapping[str, Any]]) -> str | None:
    return _first_string(mappings, ("issueId", "issue_id", "identifier", "id"))


def _issue_title(mappings: list[Mapping[str, Any]]) -> str | None:
    return _first_string(mappings, ("title",))


def _first_string(mappings: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for mapping in mappings:
        for key in keys:
            value = mapping.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _values_for_keys(mappings: list[Mapping[str, Any]], keys: tuple[str, ...]) -> tuple[Any, ...]:
    values: list[Any] = []
    for mapping in mappings:
        values.extend(mapping.get(key) for key in keys if key in mapping)
    return tuple(values)


def _compact(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", separated).lower().split()
    return "".join(words)


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
