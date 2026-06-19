"""Build Linear issue title updates for Cursor research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflowstatus"}
STATUS_CHANGED_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}
UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue enters To Research."""

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)

    if not _is_status_change(payload):
        return None

    if _normalize_status(_extract_status(payload)) != _normalize_status(RESEARCH_STATUS):
        return None

    issue_id = _first_text(payload, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    for key in ("issue", "data", "triggerContext"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            payload.update(_flatten_payload(nested))

    for key, value in event.items():
        if key not in {"issue", "data", "triggerContext"}:
            payload[key] = value

    return payload


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    event_names = _event_names(payload)
    if any(name in STATUS_CHANGED_TRIGGERS for name in event_names):
        return True

    if event_names and any(name in UPDATE_TRIGGERS for name in event_names):
        return _changed_status_field(payload)

    return _changed_status_field(payload) or bool(_first_text(payload, ("newStatus", "new_status")))


def _event_names(payload: Mapping[str, Any]) -> set[str]:
    names: set[str] = set()
    for key in ("trigger", "webhookType", "action", "type", "event"):
        value = payload.get(key)
        if isinstance(value, str):
            names.add(_normalize_token(value))
    return names


def _changed_status_field(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "changedFields", "updated_from", "updatedFrom"):
        if _contains_status_field(payload.get(key)):
            return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_token(str(key)) in STATUS_FIELDS for key in changes)

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_token(value) in STATUS_FIELDS

    if isinstance(value, Mapping):
        return any(_normalize_token(str(key)) in STATUS_FIELDS for key in value)

    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return any(_contains_status_field(item) for item in value)

    return False


def _extract_status(payload: Mapping[str, Any]) -> str | None:
    status = _first_text(
        payload,
        (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "newWorkflowState",
            "new_workflow_state",
        ),
    )
    if status:
        return status

    for key in ("status", "state", "workflowState", "workflowStatus"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            nested = _first_text(value, ("name", "title", "label"))
            if nested:
                return nested
        elif isinstance(value, str):
            return value.strip()

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflowStatus"):
            value = changes.get(key)
            if isinstance(value, Mapping):
                status = _first_text(value, ("to", "after", "new", "name"))
                if status:
                    return status

    return None


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text
    return None


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    return " ".join(_split_words(value))


def _normalize_token(value: str) -> str:
    return "".join(_split_words(value))


def _split_words(value: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    return [word.lower() for word in re.split(r"[^A-Za-z0-9]+", spaced) if word]


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
