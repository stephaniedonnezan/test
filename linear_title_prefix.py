"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CONTAINER_KEYS = ("triggerContext", "payload", "data", "issue", "node", "resource")
_EXPLICIT_STATUS_KEYS = (
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
_STATUS_FALLBACK_KEYS = ("status", "state", "workflowState", "workflow_state")
_TRIGGER_KEYS = ("trigger", "event", "eventType", "webhookType", "type", "action")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
    "changes",
    "changed",
    "updated",
    "updatedFrom",
    "updated_from",
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    candidates = list(_candidate_mappings(event))
    if not _is_status_change(candidates):
        return None

    new_status = _extract_new_status(candidates)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_text(candidates, ("issueId", "issue_id", "id", "identifier"))
    title = _extract_text(candidates, ("title",))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if clean_title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _candidate_mappings(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    seen: set[int] = set()

    def walk(value: Any) -> Iterable[Mapping[str, Any]]:
        if not isinstance(value, Mapping):
            return

        value_id = id(value)
        if value_id in seen:
            return
        seen.add(value_id)

        yield value
        for key in _CONTAINER_KEYS:
            yield from walk(value.get(key))

    yield from walk(event)


def _is_status_change(candidates: Iterable[Mapping[str, Any]]) -> bool:
    candidates = list(candidates)
    for candidate in candidates:
        for key in _TRIGGER_KEYS:
            if _is_status_changed_label(candidate.get(key)):
                return True

    update_seen = any(
        _is_update_label(candidate.get(key))
        for candidate in candidates
        for key in _TRIGGER_KEYS
    )
    return update_seen and any(_updated_fields_include_status(candidate) for candidate in candidates)


def _extract_new_status(candidates: Iterable[Mapping[str, Any]]) -> str | None:
    candidates = list(candidates)
    explicit_status = _extract_named_value(candidates, _EXPLICIT_STATUS_KEYS)
    if explicit_status:
        return explicit_status

    return _extract_named_value(candidates, _STATUS_FALLBACK_KEYS)


def _extract_text(candidates: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        for key in keys:
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _extract_named_value(candidates: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        for key in keys:
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                return value
            if isinstance(value, Mapping):
                name = value.get("name")
                if isinstance(name, str) and name.strip():
                    return name
    return None


def _is_status_changed_label(value: Any) -> bool:
    normalized = _normalize_text(value)
    return normalized in {
        "status changed",
        "state changed",
        "workflow state changed",
        "issue status changed",
        "issue state changed",
        "issue workflow state changed",
    }


def _is_update_label(value: Any) -> bool:
    normalized = _normalize_text(value)
    return normalized in {"update", "updated", "issue update", "issue updated", "updated issue"}


def _updated_fields_include_status(candidate: Mapping[str, Any]) -> bool:
    for key in _UPDATED_FIELD_KEYS:
        value = candidate.get(key)
        if _contains_status_field(value):
            return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        return any(_is_status_field(key) or _contains_status_field(item) for key, item in value.items())

    if isinstance(value, Iterable):
        return any(
            _contains_status_field(item)
            if isinstance(item, (Mapping, list, tuple, set))
            else _is_status_field(item)
            for item in value
        )

    return False


def _is_status_field(value: Any) -> bool:
    normalized = _normalize_text(value)
    return normalized in {
        "status",
        "status id",
        "state",
        "state id",
        "workflow state",
        "workflow state id",
    }


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    lowered = re.sub(r"[^A-Za-z0-9]+", " ", spaced).lower()
    return " ".join(lowered.split())


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
