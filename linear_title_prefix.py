"""Build Linear issue title update actions for Cursor research automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = frozenset({"status", "state", "workflowstate", "workflow state"})


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue enters research.

    The Cursor automation trigger can pass either a flat ``triggerContext`` shape
    or a nested Linear webhook shape. This function accepts both and returns a
    serializable action for the caller to perform.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _payload(event)
    if not _is_status_change(payload):
        return None

    status = _new_status(payload)
    if _normalize(status) != _normalize(TARGET_STATUS):
        return None

    issue = _issue_payload(payload)
    issue_id = _string_from_keys(issue, ("identifier", "issueId", "issue_id", "key", "id"))
    title = _string_from_keys(issue, ("title", "name"))

    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context
    return event


def _issue_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    data = payload.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            return _merge_issue_with_metadata(issue, data, payload)
        if _looks_like_issue(data):
            return _merge_issue_with_metadata(data, payload)

    issue = payload.get("issue")
    if isinstance(issue, Mapping):
        return _merge_issue_with_metadata(issue, payload)

    return payload


def _merge_issue_with_metadata(
    issue: Mapping[str, Any], *metadata_sources: Mapping[str, Any]
) -> dict[str, Any]:
    merged = dict(issue)
    for source in metadata_sources:
        for key, value in source.items():
            if key not in {"data", "issue"}:
                merged[key] = value
    return merged


def _looks_like_issue(value: Mapping[str, Any]) -> bool:
    return any(key in value for key in ("title", "identifier", "issueId", "issue_id", "key"))


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    event_names = tuple(_event_names(payload))
    if any("status changed" == name or "statuschanged" == name for name in event_names):
        return True

    if any(name in {"issue updated", "updated issue", "update", "updated"} for name in event_names):
        return _changed_status_fields(payload)

    return _changed_status_fields(payload) and _new_status(payload) is not None


def _event_names(payload: Mapping[str, Any]) -> Iterable[str]:
    for key in ("trigger", "webhookType", "action", "type", "eventType", "event"):
        value = payload.get(key)
        if isinstance(value, str):
            normalized = _normalize(value)
            if normalized:
                yield normalized


def _changed_status_fields(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "changedFields"):
        fields = payload.get(key)
        if _field_collection_mentions_status(fields):
            return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        if any(_is_status_field(field) for field in changes):
            return True
    elif isinstance(changes, Iterable) and not isinstance(changes, (str, bytes)):
        for change in changes:
            if isinstance(change, Mapping) and _is_status_field(
                _string_from_keys(change, ("field", "name", "key"))
            ):
                return True

    return False


def _field_collection_mentions_status(fields: Any) -> bool:
    if isinstance(fields, str):
        return _is_status_field(fields)
    if isinstance(fields, Iterable) and not isinstance(fields, (str, bytes)):
        return any(_is_status_field(str(field)) for field in fields)
    return False


def _is_status_field(field: Any) -> bool:
    normalized = _normalize(field)
    return normalized in STATUS_FIELD_NAMES


def _new_status(payload: Mapping[str, Any]) -> str | None:
    direct = _string_from_keys(
        payload,
        (
            "newStatus",
            "new_status",
            "statusName",
            "stateName",
            "workflowStateName",
        ),
    )
    if direct:
        return direct

    changes = payload.get("changes")
    changed_status = _status_from_changes(changes)
    if changed_status:
        return changed_status

    issue = _issue_payload(payload)
    for key in ("status", "state", "workflowState"):
        value = issue.get(key)
        status = _status_name(value)
        if status:
            return status

    return None


def _status_from_changes(changes: Any) -> str | None:
    if isinstance(changes, Mapping):
        for field, change in changes.items():
            if _is_status_field(field):
                return _status_name_from_change(change)
    elif isinstance(changes, Iterable) and not isinstance(changes, (str, bytes)):
        for change in changes:
            if isinstance(change, Mapping) and _is_status_field(
                _string_from_keys(change, ("field", "name", "key"))
            ):
                return _status_name_from_change(change)
    return None


def _status_name_from_change(change: Any) -> str | None:
    if isinstance(change, Mapping):
        return _string_from_keys(change, ("to", "newValue", "after", "value", "name"))
    return _status_name(change)


def _status_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _string_from_keys(value, ("name", "title", "label"))
    if isinstance(value, str):
        return value
    return None


def _string_from_keys(payload: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_research_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(TITLE_PREFIX)}\b", title, re.IGNORECASE) is not None


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
