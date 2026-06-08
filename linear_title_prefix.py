"""Build Linear issue title updates for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}
EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
)
CURRENT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
TRIGGER_KEYS = ("trigger", "webhookType", "webhook_type", "action", "type", "eventType", "event_type")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action for matching research transitions.

    The automation trigger payloads can be flat, nested under ``triggerContext``,
    or shaped like Linear webhook issue update events. This function keeps the
    outward contract small: return an action dict when the title should be
    prefixed, otherwise return ``None``.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_status(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(_issue_candidates(event), ("id", "issueId", "issue_id", "identifier", "key"))
    title = _first_text(_issue_candidates(event), ("title", "name", "summary"))
    if issue_id is None or title is None:
        return None

    if title.casefold().startswith(TITLE_PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_tokens = {_normalize_token(value) for value in _trigger_values(event)}
    if "statuschanged" in trigger_tokens or "statuschange" in trigger_tokens:
        return True

    is_update_event = bool(trigger_tokens & {"update", "updated", "issueupdated", "updatedissue"})
    return is_update_event and _changed_fields_include_status(event)


def _trigger_values(event: Mapping[str, Any]) -> Iterable[Any]:
    for candidate in _metadata_candidates(event):
        for key in TRIGGER_KEYS:
            if key in candidate:
                yield candidate[key]


def _metadata_candidates(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates = [event]
    for key in ("triggerContext", "trigger_context", "data", "webhook"):
        value = event.get(key)
        if isinstance(value, Mapping):
            candidates.append(value)
    return candidates


def _changed_fields_include_status(event: Mapping[str, Any]) -> bool:
    for candidate in _metadata_candidates(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = candidate.get(key)
            if _field_list_includes_status(fields):
                return True

        for key in ("changes", "changed", "updatedFrom", "updated_from"):
            changed = candidate.get(key)
            if isinstance(changed, Mapping) and any(_is_status_field(field) for field in changed):
                return True

    return False


def _field_list_includes_status(fields: Any) -> bool:
    if isinstance(fields, str):
        return _is_status_field(fields)
    if isinstance(fields, Iterable) and not isinstance(fields, (bytes, Mapping)):
        return any(isinstance(field, str) and _is_status_field(field) for field in fields)
    return False


def _is_status_field(field: str) -> bool:
    normalized = _normalize_key(field)
    return (
        normalized in STATUS_FIELD_NAMES
        or "status" in normalized
        or normalized in {"stateid", "workflowstateid", "workflow_state_id"}
    )


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for candidate in _metadata_candidates(event):
        status = _first_status(candidate, EXPLICIT_STATUS_KEYS)
        if status is not None:
            return status

    changed_status = _status_from_changes(event)
    if changed_status is not None:
        return changed_status

    for candidate in _issue_candidates(event):
        status = _first_status(candidate, CURRENT_STATUS_KEYS)
        if status is not None:
            return status

    return None


def _status_from_changes(event: Mapping[str, Any]) -> str | None:
    for candidate in _metadata_candidates(event):
        changes = candidate.get("changes") or candidate.get("changed")
        if not isinstance(changes, Mapping):
            continue

        for field, change in changes.items():
            if not isinstance(field, str) or not _is_status_field(field):
                continue
            status = _coerce_changed_status(change)
            if status is not None:
                return status

    return None


def _coerce_changed_status(change: Any) -> str | None:
    if isinstance(change, str):
        return change.strip() or None

    if isinstance(change, Mapping):
        for key in ("to", "new", "after", "value", "name"):
            if key not in change:
                continue
            status = _coerce_status(change[key])
            if status is not None:
                return status

    return _coerce_status(change)


def _issue_candidates(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext") or event.get("trigger_context")
    if isinstance(trigger_context, Mapping):
        candidates.append(trigger_context)

    candidates.append(event)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            candidates.append(issue)
        candidates.append(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        candidates.append(issue)

    return candidates


def _first_text(candidates: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for candidate in candidates:
        for key in keys:
            value = candidate.get(key)
            if isinstance(value, (str, int)):
                text = str(value).strip()
                if text:
                    return text
    return None


def _first_status(candidate: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        if key not in candidate:
            continue
        status = _coerce_status(candidate[key])
        if status is not None:
            return status
    return None


def _coerce_status(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "status"):
            if key in value:
                status = _coerce_status(value[key])
                if status is not None:
                    return status
    return None


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    words = re.sub(r"[_\-]+", " ", words)
    return re.sub(r"\s+", " ", words).casefold()


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", value.replace("-", "_").casefold())


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]", "", spaced.casefold())


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
