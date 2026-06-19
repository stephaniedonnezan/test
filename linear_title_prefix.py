"""Build Linear issue-title updates for Cursor research status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update when a Linear issue changes status to To Research."""
    if not isinstance(event, Mapping):
        return None

    payloads = _payloads(event)
    if not _is_status_change_event(payloads):
        return None

    status = _find_status(payloads)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _find_text(payloads, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _find_text(payloads, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely payload objects from most specific to least specific."""
    payloads: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in payloads:
            payloads.append(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")

    add(trigger_context)
    add(event)
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))
    add(issue)

    return payloads


def _is_status_change_event(payloads: Sequence[Mapping[str, Any]]) -> bool:
    trigger_values = _find_metadata_values(payloads)
    for value in trigger_values:
        normalized = _normalize(value)
        if normalized in {
            "status changed",
            "status change",
            "status updated",
            "status update",
            "state changed",
            "state change",
            "workflow state changed",
            "workflow state change",
        }:
            return True
        if "status" in normalized and ("changed" in normalized or "change" in normalized):
            return True

    update_event = any(
        _normalize(value) in {"update", "updated", "issue update", "issue updated", "updated issue"}
        for value in trigger_values
    )
    return update_event and _has_status_field_change(payloads)


def _find_metadata_values(payloads: Sequence[Mapping[str, Any]]) -> list[Any]:
    values: list[Any] = []
    for payload in payloads:
        for key in ("trigger", "webhookType", "action", "type"):
            if key in payload:
                values.append(payload[key])
    return values


def _has_status_field_change(payloads: Sequence[Mapping[str, Any]]) -> bool:
    for payload in payloads:
        for key in ("updatedFields", "changedFields", "changedAttributes"):
            if _contains_status_field(payload.get(key)):
                return True

        changes = payload.get("changes")
        if isinstance(changes, Mapping):
            if any(_is_status_field(key) for key in changes):
                return True
        elif _contains_status_field(changes):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    normalized = _normalize(value).replace(" ", "")
    return normalized in STATUS_FIELDS or "status" in normalized or normalized == "state"


def _find_status(payloads: Sequence[Mapping[str, Any]]) -> Any:
    explicit_keys = (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    for payload in payloads:
        value = _find_in_mapping(payload, explicit_keys)
        if value:
            return value

    changed_status = _find_changed_status(payloads)
    if changed_status:
        return changed_status

    for payload in payloads:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = payload.get(key)
            if isinstance(value, Mapping):
                nested = _find_in_mapping(value, ("name", "title", "status", "state"))
                if nested:
                    return nested
            elif value:
                return value

    return None


def _find_changed_status(payloads: Sequence[Mapping[str, Any]]) -> Any:
    for payload in payloads:
        changes = payload.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for key, change in changes.items():
            if not _is_status_field(key):
                continue
            if isinstance(change, Mapping):
                value = _find_in_mapping(
                    change,
                    ("to", "new", "after", "newValue", "new_value", "name", "title"),
                )
                if value:
                    return value
            elif change:
                return change

    return None


def _find_text(payloads: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for key in keys:
        for payload in payloads:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value
            if value is not None and not isinstance(value, (Mapping, Sequence)):
                return str(value)
    return None


def _find_in_mapping(payload: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        value = payload.get(key)
        if value:
            return value
    return None


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
