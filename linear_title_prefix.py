"""Build Linear issue title update actions for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
TITLE_SEPARATOR = ": "
STATUS_FIELD_NAMES = frozenset({"status", "state", "workflowstate", "workflow_status"})


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to To Research.

    The automation trigger can provide either a flat Cursor ``triggerContext``
    payload or a nested Linear webhook payload. This function intentionally
    returns a declarative action instead of calling Linear directly so it can be
    used from tests, CLIs, or an external automation runner.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _coerce_payload(event)
    if not _is_status_change_event(payload):
        return None

    if _normalize_status(_new_status(payload)) != _normalize_status(TARGET_STATUS):
        return None

    issue_id = _string_value(_first_value(payload, ("issueId", "issue_id", "identifier", "key", "id")))
    title = _string_value(_first_value(payload, ("title", "name")))
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}{TITLE_SEPARATOR}{title}",
    }


def _coerce_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Linear/Cursor webhook shapes into one lookup payload."""

    payload: dict[str, Any] = {}

    for key in ("issue", "data", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            payload.update(_coerce_payload(value))

    state = event.get("state")
    if isinstance(state, Mapping):
        payload.setdefault("status", _first_value(state, ("name", "id", "type")))

    workflow_state = event.get("workflowState")
    if isinstance(workflow_state, Mapping):
        payload.setdefault("workflowState", _first_value(workflow_state, ("name", "id", "type")))

    for key, value in event.items():
        if isinstance(value, Mapping) and key in {"issue", "data", "triggerContext", "state", "workflowState"}:
            continue
        payload[key] = value

    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_names = (
        _first_value(payload, ("trigger", "webhookType", "action", "type")),
        payload.get("event"),
    )
    normalized_names = {_normalize_token(name) for name in event_names if _string_value(name)}

    if any("statuschanged" in name or "statechanged" in name for name in normalized_names):
        return True

    if any(name in {"update", "updated", "issueupdated", "updatedissue"} for name in normalized_names):
        return _changed_fields_include_status(payload)

    return False


def _changed_fields_include_status(payload: Mapping[str, Any]) -> bool:
    changed_values = _first_value(payload, ("updatedFields", "changedFields", "changes", "changed"))

    if isinstance(changed_values, Mapping):
        return any(_normalize_field_name(key) in STATUS_FIELD_NAMES for key in changed_values)

    if isinstance(changed_values, str):
        return _normalize_field_name(changed_values) in STATUS_FIELD_NAMES

    if isinstance(changed_values, Iterable):
        for value in changed_values:
            if isinstance(value, Mapping):
                field_name = _first_value(value, ("field", "fieldName", "name", "key"))
                if _normalize_field_name(field_name) in STATUS_FIELD_NAMES:
                    return True
            elif _normalize_field_name(value) in STATUS_FIELD_NAMES:
                return True

    return False


def _new_status(payload: Mapping[str, Any]) -> Any:
    explicit_status = _first_value(
        payload,
        (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "statusName",
            "status_name",
        ),
    )
    if explicit_status is not None:
        return explicit_status

    changes = _first_value(payload, ("changes", "changed"))
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_status"):
            value = changes.get(key)
            if isinstance(value, Mapping):
                changed_to = _first_value(value, ("to", "new", "newValue", "name", "after"))
                if changed_to is not None:
                    return _status_name(changed_to)
            elif value is not None:
                return _status_name(value)

    return _first_value(payload, ("status", "state", "workflowState", "workflow_status"))


def _status_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _first_value(value, ("name", "id", "type"))
    return value


def _first_value(mapping: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            return value
    return None


def _string_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_status(value: Any) -> str:
    text = _string_value(_status_name(value))
    if not text:
        return ""
    return _normalize_words(text)


def _normalize_field_name(value: Any) -> str:
    text = _string_value(value)
    return _normalize_token(text) if text else ""


def _normalize_token(value: Any) -> str:
    text = _string_value(value)
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]", "", _split_camel_case(text).lower())


def _normalize_words(value: str) -> str:
    text = _split_camel_case(value)
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    """Read a JSON event from stdin and print an update action when needed."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON input: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
