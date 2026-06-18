"""Build Linear issue title updates for Cursor research status changes.

The automation host can call ``build_issue_title_update`` with either the flat
Cursor trigger payload or a nested Linear webhook payload. When the issue moves
to "to research", the function returns a small action dictionary describing the
title update to apply.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate"}
DIRECT_STATUS_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statusupdated",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}
GENERIC_UPDATE_TRIGGERS = {"update", "updated", "issueupdated", "updatedissue"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue enters research.

    The returned action has this shape::

        {
            "action": "update_issue_title",
            "issueId": "POI-123",
            "title": "Cursor researching: Existing title",
        }

    Non-status changes, changes to other statuses, missing issue metadata, and
    titles that are already prefixed are ignored.
    """

    if not isinstance(event, Mapping):
        return None

    candidates = _candidate_payloads(event)
    if not _is_status_change_event(candidates):
        return None

    new_status = _find_new_status(candidates)
    if _normalize_token(new_status) != _normalize_token(TARGET_STATUS):
        return None

    issue_id = _find_first_text(candidates, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _find_first_text(candidates, ("title", "name"))

    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _already_prefixed(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _candidate_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return useful payload scopes from outermost metadata to nested issue data."""

    candidates: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in candidates:
            candidates.append(value)

    add(event)
    for key in ("triggerContext", "webhook", "data"):
        add(event.get(key))

    containers = list(candidates)
    for container in containers:
        for key in ("issue", "state", "workflowState", "workflow_state"):
            add(container.get(key))
        data = container.get("data")
        if isinstance(data, Mapping):
            add(data.get("issue"))
            add(data.get("state"))
            add(data.get("workflowState"))

    return candidates


def _is_status_change_event(candidates: Sequence[Mapping[str, Any]]) -> bool:
    trigger_values: list[str] = []
    for payload in candidates:
        for key in ("trigger", "webhookType", "webhook_type", "action", "type"):
            text = _as_text(payload.get(key))
            if text:
                trigger_values.append(text)

    normalized_triggers = {_normalize_token(value) for value in trigger_values}
    if normalized_triggers & DIRECT_STATUS_TRIGGERS:
        return True

    if normalized_triggers & GENERIC_UPDATE_TRIGGERS:
        return _updated_fields_include_status(candidates)

    return False


def _updated_fields_include_status(candidates: Sequence[Mapping[str, Any]]) -> bool:
    for payload in candidates:
        for key in ("updatedFields", "updated_fields"):
            if _field_collection_mentions_status(payload.get(key)):
                return True

        changes = payload.get("changes")
        if isinstance(changes, Mapping):
            for field_name, change in changes.items():
                if _is_status_field(field_name):
                    return True
                if isinstance(change, Mapping) and any(
                    _is_status_field(name) for name in change.keys()
                ):
                    return True
        elif _field_collection_mentions_status(changes):
            return True

    return False


def _field_collection_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value.keys())

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_field_collection_mentions_status(item) for item in value)

    return False


def _find_new_status(candidates: Sequence[Mapping[str, Any]]) -> str | None:
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
    status_keys = ("status", "state", "workflowState", "workflow_state")

    status = _find_first_text(candidates, explicit_status_keys)
    if status:
        return status

    for payload in candidates:
        changes = payload.get("changes")
        status = _status_from_changes(changes)
        if status:
            return status

    for payload in candidates:
        for key in status_keys:
            status = _status_value(payload.get(key))
            if status:
                return status

    return None


def _status_from_changes(changes: Any) -> str | None:
    if not isinstance(changes, Mapping):
        return None

    for key, value in changes.items():
        if not _is_status_field(key):
            continue

        if isinstance(value, Mapping):
            for new_key in ("to", "new", "newValue", "new_value", "after", "name"):
                status = _status_value(value.get(new_key))
                if status:
                    return status

        status = _status_value(value)
        if status:
            return status

    return None


def _status_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _find_first_text((value,), ("name", "title", "status", "state", "workflowState"))

    return _as_text(value)


def _find_first_text(candidates: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for payload in candidates:
        for key in keys:
            value = payload.get(key)
            text = _status_value(value) if key in {"status", "state", "workflowState"} else _as_text(value)
            if text:
                return text

    return None


def _already_prefixed(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _is_status_field(value: Any) -> bool:
    return _normalize_token(value) in STATUS_FIELD_NAMES


def _normalize_token(value: Any) -> str:
    text = _as_text(value)
    if not text:
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text.strip())
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return "".join(text.lower().split())


def _as_text(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


def main() -> int:
    """Read a JSON event from stdin and print the update action, if any."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
