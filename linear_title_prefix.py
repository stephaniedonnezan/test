"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "toresearch"
STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
    "workflow",
    "workflowid",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    candidates = list(_candidate_payloads(event))
    if not _is_status_change_event(candidates):
        return None

    new_status = _extract_new_status(candidates)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(candidates, ("issueId", "issue_id", "identifier", "key"))
    if not issue_id:
        issue_id = _first_text(candidates, ("id",))
    title = _first_text(candidates, ("title", "name"))
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _candidate_payloads(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely event/context/issue mappings from common Cursor and Linear payloads."""
    seen: set[int] = set()

    def visit(payload: Any) -> Iterable[Mapping[str, Any]]:
        if not isinstance(payload, Mapping) or id(payload) in seen:
            return
        seen.add(id(payload))
        yield payload

        for key in ("automation_trigger_info", "triggerContext", "trigger_context"):
            child = payload.get(key)
            if isinstance(child, Mapping):
                yield from visit(child)

        data = payload.get("data")
        if isinstance(data, Mapping):
            yield from visit(data)
            issue = data.get("issue")
            if isinstance(issue, Mapping):
                yield from visit(issue)

        issue = payload.get("issue")
        if isinstance(issue, Mapping):
            yield from visit(issue)

    yield from visit(event)


def _is_status_change_event(candidates: Iterable[Mapping[str, Any]]) -> bool:
    event_names: list[str] = []
    status_change_markers: list[Any] = []

    for payload in candidates:
        event_names.extend(
            _text_values(payload, ("trigger", "webhookType", "webhook_type", "action", "type"))
        )
        status_change_markers.extend(
            payload.get(key)
            for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields")
            if key in payload
        )
        for key in ("changes", "changed", "updatedFrom", "updated_from"):
            value = payload.get(key)
            if isinstance(value, Mapping):
                status_change_markers.append(value.keys())
                status_change_markers.append(value)

    normalized_names = {_normalize(name) for name in event_names}
    if any("statuschanged" in name or "statechanged" in name for name in normalized_names):
        return True

    explicit_non_status = normalized_names & {
        "comment",
        "commentcreated",
        "commentupdated",
        "issuecomment",
        "issuecommented",
    }
    if explicit_non_status:
        return False

    if normalized_names & {"update", "updated", "issueupdated", "updatedissue"}:
        return _contains_status_field(status_change_markers)

    return False


def _contains_status_field(markers: Iterable[Any]) -> bool:
    for marker in markers:
        if isinstance(marker, str) and _normalize(marker) in STATUS_FIELD_NAMES:
            return True
        if isinstance(marker, Mapping):
            if any(_normalize(key) in STATUS_FIELD_NAMES for key in marker):
                return True
        if isinstance(marker, Iterable) and not isinstance(marker, (str, bytes, Mapping)):
            if any(isinstance(item, str) and _normalize(item) in STATUS_FIELD_NAMES for item in marker):
                return True
    return False


def _extract_new_status(candidates: Iterable[Mapping[str, Any]]) -> str | None:
    explicit_status_keys = (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    fallback_status_keys = ("status", "state", "workflowState", "workflow_state")

    for payload in candidates:
        for key in explicit_status_keys:
            value = payload.get(key)
            status = _status_text(value)
            if status:
                return status

    for payload in candidates:
        for changes_key in ("changes", "changed"):
            status = _status_from_change_map(payload.get(changes_key))
            if status:
                return status

    for payload in candidates:
        for key in fallback_status_keys:
            status = _status_text(payload.get(key))
            if status:
                return status

    return None


def _status_from_change_map(changes: Any) -> str | None:
    if not isinstance(changes, Mapping):
        return None

    for key, value in changes.items():
        if _normalize(key) not in STATUS_FIELD_NAMES:
            continue
        if isinstance(value, Mapping):
            for new_key in ("newValue", "new_value", "to", "after", "name"):
                status = _status_text(value.get(new_key))
                if status:
                    return status
        status = _status_text(value)
        if status:
            return status

    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        for key in ("name", "label", "title", "status", "state"):
            status = _status_text(value.get(key))
            if status:
                return status
    return None


def _first_text(candidates: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for payload in candidates:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str):
                stripped = value.strip()
                if stripped:
                    return stripped
    return None


def _text_values(payload: Mapping[str, Any], keys: Iterable[str]) -> list[str]:
    return [value for key in keys if isinstance((value := payload.get(key)), str)]


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]", "", value).lower()


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    if action is not None:
        print(json.dumps(action))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
