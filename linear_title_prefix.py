"""Build Linear issue title update actions for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
CHANGE_FIELD_NAMES = frozenset(
    {"status", "statusid", "state", "stateid", "workflowstate", "workflowstateid", "workflow_state"}
)


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue moves to research.

    The automation trigger can provide a compact ``triggerContext`` payload or a
    nested Linear webhook payload. This function keeps side effects outside the
    handler by returning a serializable action for the caller to execute.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _payload(event)
    if not _is_status_change_event(payload):
        return None

    status = _new_status(payload)
    if _normalize_status(status) != TARGET_STATUS:
        return None

    title = _text_value(_first_value(payload, ("title", "name")))
    issue_id = _issue_id(payload)
    if not title or not issue_id:
        return None

    stripped_title = title.strip()
    if _has_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {stripped_title}",
    }


def _payload(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    _merge_nested(payload, event.get("data"))
    _merge_nested(payload, event.get("issue"))
    _merge_nested(payload, event.get("triggerContext"))
    _merge_nested(payload, event)
    return payload


def _merge_nested(payload: dict[str, Any], value: Any) -> None:
    if not isinstance(value, Mapping):
        return

    data = value.get("data")
    if isinstance(data, Mapping):
        _merge_nested(payload, data)

    issue = value.get("issue")
    if isinstance(issue, Mapping):
        _merge_nested(payload, issue)

    state = value.get("state")
    if isinstance(state, Mapping) and "status" not in value:
        _copy_name(payload, "status", state)

    workflow_state = value.get("workflowState") or value.get("workflow_state")
    if isinstance(workflow_state, Mapping) and "workflowState" not in value:
        _copy_name(payload, "workflowState", workflow_state)

    for key, item in value.items():
        if key not in {"data", "issue"}:
            payload[key] = item


def _copy_name(payload: dict[str, Any], key: str, value: Mapping[str, Any]) -> None:
    name = _text_value(value.get("name"))
    if name:
        payload[key] = name


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_names = (
        _first_value(payload, ("trigger", "event", "eventType", "webhookType", "action", "type")),
        _first_value(payload, ("triggerType",)),
    )

    for name in event_names:
        normalized = _normalize_token(name)
        if normalized in {"statuschanged", "statuschange", "statusupdated", "statechanged"}:
            return True
        if normalized in {"status_changed", "status_change", "status_updated", "state_changed"}:
            return True

    if _updated_fields_include_status(payload):
        action = _normalize_token(_first_value(payload, ("action", "trigger", "event", "type")))
        if action in {"update", "updated", "issueupdated", "updatedissue", "issue_update", "issue_updated", "updated_issue"}:
            return True

    return False


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    updated_fields = _first_value(payload, ("updatedFields", "updated_fields", "changedFields", "changed_fields"))
    if _field_collection_mentions_status(updated_fields):
        return True

    changes = _first_value(payload, ("changes", "changed", "updates"))
    if isinstance(changes, Mapping):
        return any(_field_name_mentions_status(key) for key in changes)
    if isinstance(changes, Iterable) and not isinstance(changes, (str, bytes)):
        return any(_change_mentions_status(change) for change in changes)

    return False


def _field_collection_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _field_name_mentions_status(value)
    if isinstance(value, Mapping):
        return any(_field_name_mentions_status(key) for key in value)
    if isinstance(value, Iterable):
        return any(_field_name_mentions_status(item) for item in value)
    return False


def _change_mentions_status(change: Any) -> bool:
    if isinstance(change, Mapping):
        return _field_name_mentions_status(_first_value(change, ("field", "name", "key", "property")))
    return _field_name_mentions_status(change)


def _field_name_mentions_status(value: Any) -> bool:
    normalized = _normalize_token(value)
    return normalized in CHANGE_FIELD_NAMES


def _new_status(payload: Mapping[str, Any]) -> str | None:
    direct_status = _text_value(
        _first_value(
            payload,
            (
                "newStatus",
                "new_status",
                "toStatus",
                "to_status",
                "statusName",
                "status_name",
                "stateName",
                "state_name",
                "workflowStateName",
                "workflow_state_name",
            ),
        )
    )
    if direct_status:
        return direct_status

    changes = _first_value(payload, ("changes", "changed", "updates"))
    changed_status = _status_from_changes(changes)
    if changed_status:
        return changed_status

    for key in ("status", "state", "workflowState", "workflow_state"):
        status = _status_name(payload.get(key))
        if status:
            return status

    return None


def _status_from_changes(changes: Any) -> str | None:
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _field_name_mentions_status(key):
                status = _status_name(value) or _status_name(_mapping_value(value, ("new", "to", "after")))
                if status:
                    return status
    elif isinstance(changes, Iterable) and not isinstance(changes, (str, bytes)):
        for change in changes:
            if isinstance(change, Mapping) and _change_mentions_status(change):
                status = _status_name(_first_value(change, ("newValue", "new_value", "to", "after", "value")))
                if status:
                    return status
    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _text_value(
            _first_value(value, ("name", "title", "label", "newValue", "new_value", "to", "after", "value"))
        )
    return _text_value(value)


def _issue_id(payload: Mapping[str, Any]) -> str | None:
    return _text_value(_first_value(payload, ("issueId", "issue_id", "identifier", "key", "id")))


def _first_value(payload: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def _mapping_value(value: Any, keys: tuple[str, ...]) -> Any:
    if isinstance(value, Mapping):
        return _first_value(value, keys)
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_status(value: Any) -> str:
    text = _text_value(value)
    if not text:
        return ""
    return re.sub(r"[\s_-]+", " ", _split_camel_case(text).casefold()).strip()


def _normalize_token(value: Any) -> str:
    text = _text_value(value)
    if not text:
        return ""
    return re.sub(r"[^a-z0-9_]+", "", _split_camel_case(text).casefold().replace("-", "_").replace(" ", "_"))


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
