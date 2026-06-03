"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}
_DIRECT_STATUS_CHANGE_SIGNALS = {
    "statuschange",
    "statuschanged",
    "statechange",
    "statechanged",
    "workflowstatechange",
    "workflowstatechanged",
}
_ISSUE_UPDATE_SIGNALS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return the Linear title update action for a qualifying status change.

    The automation passes flat trigger contexts, while Linear webhooks often wrap
    issue details under `data.issue`. This function accepts both shapes and
    returns None when the event is unrelated or the title is already prefixed.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize_status(_new_status(event)) != TARGET_STATUS:
        return None

    issue_id = _string_value(_first_value(event, ("id", "issueId", "issue_id", "identifier")))
    title = _string_value(_first_value(event, ("title", "name")))
    if not issue_id or not title:
        return None

    if title.casefold().startswith(TITLE_PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    signal_values = []
    for payload in _candidate_payloads(event):
        for key in ("trigger", "triggerType", "webhookType", "action", "type"):
            value = payload.get(key)
            if isinstance(value, str):
                signal_values.append(value)

    normalized_signals = {_compact_signal(value) for value in signal_values}
    if normalized_signals & _DIRECT_STATUS_CHANGE_SIGNALS:
        return True

    if normalized_signals & _ISSUE_UPDATE_SIGNALS:
        return _has_status_change_details(event)

    return False


def _new_status(event: Mapping[str, Any]) -> str | None:
    explicit_status = _first_value(
        event,
        (
            "newStatus",
            "new_status",
            "statusName",
            "status_name",
            "newState",
            "new_state",
        ),
        include_issue=False,
    )
    if isinstance(explicit_status, Mapping):
        explicit_status = explicit_status.get("name")
    status = _string_value(explicit_status)
    if status:
        return status

    direct_status = _first_value(event, ("status",))
    if isinstance(direct_status, Mapping):
        direct_status = direct_status.get("name")
    status = _string_value(direct_status)
    if status:
        return status

    for payload in _candidate_payloads(event):
        for key in ("state", "workflowState", "workflow_state"):
            nested_value = payload.get(key)
            if isinstance(nested_value, Mapping):
                status = _string_value(nested_value.get("name"))
                if status:
                    return status

    return None


def _first_value(
    event: Mapping[str, Any],
    keys: Iterable[str],
    *,
    include_issue: bool = True,
) -> Any:
    for payload in _candidate_payloads(event, include_issue=include_issue):
        for key in keys:
            if key in payload:
                return payload[key]
    return None


def _candidate_payloads(
    event: Mapping[str, Any],
    *,
    include_issue: bool = True,
) -> list[Mapping[str, Any]]:
    payloads: list[Mapping[str, Any]] = []

    trigger_context = _mapping_value(event.get("triggerContext"))
    if trigger_context is not None:
        payloads.append(trigger_context)

    payloads.append(event)

    data = _mapping_value(event.get("data"))
    if data is not None:
        payloads.append(data)
        data_issue = _mapping_value(data.get("issue"))
        if include_issue and data_issue is not None:
            payloads.append(data_issue)

    issue = _mapping_value(event.get("issue"))
    if include_issue and issue is not None:
        payloads.append(issue)

    return payloads


def _has_status_change_details(event: Mapping[str, Any]) -> bool:
    for payload in _candidate_payloads(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            value = payload.get(key)
            if _field_collection_mentions_status(value):
                return True

        for key in ("updatedFrom", "updated_from", "changes"):
            value = payload.get(key)
            if _mapping_mentions_status(value):
                return True
            if _field_collection_mentions_status(value):
                return True

    return False


def _field_collection_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        if _mapping_mentions_status(value):
            return True
        for key in ("field", "name", "key"):
            field_name = value.get(key)
            if isinstance(field_name, str) and _is_status_field(field_name):
                return True
        return False

    if isinstance(value, Iterable):
        return any(_field_collection_mentions_status(item) for item in value)

    return False


def _mapping_mentions_status(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False

    for key in value:
        if isinstance(key, str) and _is_status_field(key):
            return True
    return False


def _is_status_field(value: str) -> bool:
    return _compact_signal(value) in _STATUS_FIELD_NAMES


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None

    with_camel_boundaries = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", with_camel_boundaries)
    return re.sub(r"\s+", " ", normalized).strip().casefold()


def _compact_signal(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", value).casefold()


def _mapping_value(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _string_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    stripped = value.strip()
    return stripped or None


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
