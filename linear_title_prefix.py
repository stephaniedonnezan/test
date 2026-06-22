"""Build title update actions for Linear issue research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGE_FIELDS = {"status", "state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when an event enters research.

    The helper accepts several Cursor and Linear webhook shapes so callers can
    pass the original payload directly. It returns ``None`` when the event is
    unrelated, incomplete, or already has the desired title prefix.
    """

    if not isinstance(event, Mapping):
        return None

    payloads = _candidate_payloads(event)
    if not any(_is_status_change_payload(payload) for payload in payloads):
        return None
    if not any(_is_target_status(status) for status in _candidate_new_statuses(payloads)):
        return None

    issue = _find_issue_payload(payloads)
    issue_id = _clean_text(_first_present(issue, ("id", "identifier", "issueId", "issue_id")))
    title = _clean_text(_first_present(issue, ("title", "name")))

    if not issue_id or not title or _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _candidate_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return plausible event/issue containers from common webhook shapes."""

    payloads: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in payloads:
            payloads.append(value)

    add(event)

    trigger_context = event.get("triggerContext")
    add(trigger_context)

    automation_trigger_info = event.get("automation_trigger_info")
    if isinstance(automation_trigger_info, Mapping):
        add(automation_trigger_info)
        add(automation_trigger_info.get("triggerContext"))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data)
        add(data.get("issue"))

    add(event.get("issue"))

    return payloads


def _is_status_change_payload(payload: Mapping[str, Any]) -> bool:
    trigger = _clean_text(_first_present(payload, ("trigger", "event")))
    trigger_key = _normalise_key(trigger)
    if trigger_key in {
        "statuschanged",
        "statuschange",
        "statechanged",
        "statechange",
        "workflowstatechanged",
        "workflowstatechange",
    }:
        return True

    if trigger:
        return False

    if _clean_text(payload.get("webhookType")).lower() == "issue":
        if _first_present(payload, ("newStatus", "status", "state", "workflowState")) is not None:
            return True

    changed_fields = payload.get("updatedFields") or payload.get("changedFields")
    if _mentions_status_field(changed_fields):
        return True

    changes = payload.get("changes") or payload.get("updatedFrom") or payload.get("updated_from")
    if _mentions_status_field(changes):
        return True

    action_key = _normalise_key(_clean_text(payload.get("action")))
    if action_key in {"update", "updated"}:
        return _first_present(payload, ("newStatus", "status", "state", "workflowState")) is not None

    return False


def _candidate_new_statuses(payloads: Iterable[Mapping[str, Any]]) -> list[str]:
    statuses: list[str] = []
    for payload in payloads:
        statuses.extend(_extract_status_values(payload))
        changes = payload.get("changes")
        if isinstance(changes, Mapping):
            statuses.extend(_extract_status_values_from_changes(changes))
    return statuses


def _extract_status_values(payload: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("newStatus", "status", "state", "workflowState", "workflow_state"):
        value = payload.get(key)
        if value is not None:
            values.extend(_text_values(value))
    return values


def _extract_status_values_from_changes(changes: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for key, value in changes.items():
        if _normalise_key(str(key)) not in STATUS_CHANGE_FIELDS:
            continue
        if isinstance(value, Mapping):
            for next_key in ("to", "new", "newValue", "after", "toValue"):
                if next_key in value:
                    values.extend(_text_values(value[next_key]))
        else:
            values.extend(_text_values(value))
    return values


def _text_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        values = []
        for key in ("name", "title", "label", "value"):
            if key in value:
                values.extend(_text_values(value[key]))
        return values
    return []


def _find_issue_payload(payloads: Iterable[Mapping[str, Any]]) -> Mapping[str, Any]:
    for payload in payloads:
        if _first_present(payload, ("id", "identifier", "issueId", "issue_id")) is not None:
            if _first_present(payload, ("title", "name")) is not None:
                return payload
    return {}


def _first_present(payload: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


def _mentions_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalise_key(value) in STATUS_CHANGE_FIELDS
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
        return any(_mentions_status_field(item) for item in value)
    if isinstance(value, Mapping):
        return any(_normalise_key(str(key)) in STATUS_CHANGE_FIELDS for key in value)
    return False


def _is_target_status(status: str) -> bool:
    return _normalise_status(status) == _normalise_status(TARGET_STATUS)


def _has_title_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(TITLE_PREFIX)}\b", title, flags=re.IGNORECASE) is not None


def _clean_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _normalise_status(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _split_camel_case(value).lower())


def _normalise_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _split_camel_case(value).lower())


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
