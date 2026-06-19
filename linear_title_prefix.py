"""Build Linear issue-title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
PREFIXED_TITLE_TEMPLATE = f"{PREFIX}: {{title}}"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_status", "workflow status"}


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _lookup(mapping: Mapping[str, Any], *keys: str) -> Any:
    normalized_keys = {_normalize(key).replace(" ", "") for key in keys}

    for key, value in mapping.items():
        if _normalize(key).replace(" ", "") in normalized_keys:
            return value

    return None


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _status_name(value: Any) -> str:
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state"):
            nested_value = _lookup(value, key)
            if nested_value is not None:
                return str(nested_value)
        return ""

    return "" if value is None else str(value)


def _changed_field_names(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        return {_normalize(key).replace(" ", "") for key in value}

    if isinstance(value, (list, tuple, set)):
        return {_normalize(item).replace(" ", "") for item in value}

    if isinstance(value, str):
        return {_normalize(value).replace(" ", "")}

    return set()


def _has_status_change_metadata(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "changedFields", "updated_fields", "changed_fields"):
        field_names = _changed_field_names(_lookup(payload, key))
        if field_names & {_normalize(field).replace(" ", "") for field in STATUS_FIELDS}:
            return True

    for key in ("changes", "changed", "previousValues", "previous_values"):
        changes = _lookup(payload, key)
        if isinstance(changes, Mapping):
            field_names = _changed_field_names(changes)
            if field_names & {_normalize(field).replace(" ", "") for field in STATUS_FIELDS}:
                return True

    return False


def _event_names(payload: Mapping[str, Any]) -> list[str]:
    names: list[str] = []
    for key in ("trigger", "webhookType", "action", "type", "eventType", "event"):
        value = _lookup(payload, key)
        if value is not None:
            names.append(_normalize(value))
    return names


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_names = _event_names(payload)

    if any(name in {"status changed", "status change", "state changed", "workflow state changed"} for name in event_names):
        return True

    if any(name in {"issue updated", "updated issue", "update"} for name in event_names):
        return _has_status_change_metadata(payload)

    return _has_status_change_metadata(payload)


def _candidate_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    payloads: list[Mapping[str, Any]] = [event]

    trigger_context = _as_mapping(_lookup(event, "triggerContext", "trigger_context"))
    if trigger_context:
        payloads.insert(0, trigger_context)

    data = _as_mapping(_lookup(event, "data"))
    if data:
        payloads.append(data)

    issue = _as_mapping(_lookup(event, "issue"))
    if issue:
        payloads.append(issue)

    data_issue = _as_mapping(_lookup(data, "issue")) if data else {}
    if data_issue:
        payloads.append(data_issue)

    # Keep order stable while removing duplicate object references.
    deduped: list[Mapping[str, Any]] = []
    seen: set[int] = set()
    for payload in payloads:
        payload_id = id(payload)
        if payload_id not in seen:
            deduped.append(payload)
            seen.add(payload_id)

    return deduped


def _merged_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for payload in reversed(_candidate_payloads(event)):
        merged.update(payload)
    return merged


def _new_status(payload: Mapping[str, Any]) -> str:
    for key in ("newStatus", "new_status", "newState", "new_state", "toStatus", "to_status"):
        value = _lookup(payload, key)
        if value is not None:
            return _status_name(value)

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _lookup(payload, key)
        if value is not None:
            return _status_name(value)

    changes = _lookup(payload, "changes", "changed")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            change = _lookup(changes, key)
            if isinstance(change, Mapping):
                for nested_key in ("newValue", "new_value", "to", "after"):
                    value = _lookup(change, nested_key)
                    if value is not None:
                        return _status_name(value)
            elif change is not None:
                return _status_name(change)

    return ""


def _issue_id(payload: Mapping[str, Any]) -> str:
    for key in ("issueId", "issue_id", "id", "identifier", "key"):
        value = _lookup(payload, key)
        if value is not None:
            issue_id = str(value).strip()
            if issue_id:
                return issue_id
    return ""


def _issue_title(payload: Mapping[str, Any]) -> str:
    for key in ("title", "name"):
        value = _lookup(payload, key)
        if value is not None:
            title = str(value).strip()
            if title:
                return title
    return ""


def _has_prefix(title: str) -> bool:
    return _normalize(title).startswith(_normalize(PREFIX))


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to "to research"."""

    if not isinstance(event, Mapping):
        return None

    payload = _merged_payload(event)

    if not _is_status_change_event(payload):
        return None

    if _normalize(_new_status(payload)) != _normalize(TARGET_STATUS):
        return None

    issue_id = _issue_id(payload)
    title = _issue_title(payload)
    if not issue_id or not title:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": title if _has_prefix(title) else PREFIXED_TITLE_TEMPLATE.format(title=title),
    }


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
