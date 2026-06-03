"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = frozenset(
    {"status", "statusid", "state", "stateid", "workflowstate", "workflowstateid"}
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    payload = _payload(event)
    if not _is_status_change_event(payload):
        return None

    if _normalize_text(_new_status(payload)) != TARGET_STATUS:
        return None

    data = _mapping_value(payload, "data")
    issue = _issue(payload)
    issue_id = _clean_text(
        _first_value(issue, data, payload, keys=("id", "issueId", "issue_id", "identifier"))
    )
    title = _clean_text(_first_value(issue, data, payload, keys=("title",)))
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context
    return event


def _issue(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in ("issue", "data"):
        nested = payload.get(key)
        if isinstance(nested, Mapping):
            issue = nested.get("issue")
            if isinstance(issue, Mapping):
                return issue
            if key == "issue" or _first_value(nested, keys=("id", "identifier", "title")) is not None:
                return nested
    return {}


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_values = _collect_event_values(payload)
    if any(
        value in {"status changed", "status change", "status updated", "status update"}
        for value in event_values
    ):
        return True

    if any(value in {"update", "updated", "issue updated", "updated issue"} for value in event_values):
        return _updated_status_field(payload)

    return False


def _collect_event_values(value: Any) -> list[str]:
    values: list[str] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized_key = _normalize_key(key)
            if normalized_key in {"trigger", "webhooktype", "action", "type"}:
                normalized_value = _normalize_text(nested)
                if normalized_value:
                    values.append(normalized_value)
            elif normalized_key in {"triggercontext", "data"} and isinstance(nested, Mapping):
                values.extend(_collect_event_values(nested))
    return values


def _updated_status_field(payload: Mapping[str, Any]) -> bool:
    data = _mapping_value(payload, "data")
    updated_fields = _first_value(
        payload,
        data,
        keys=("updatedFields", "updated_fields", "changedFields", "changed_fields"),
    )
    if isinstance(updated_fields, str):
        fields = [updated_fields]
    elif isinstance(updated_fields, list | tuple | set):
        fields = list(updated_fields)
    elif isinstance(updated_fields, Mapping):
        fields = list(updated_fields)
    else:
        return False

    return any(_normalize_key(field) in STATUS_FIELD_NAMES for field in fields)


def _new_status(payload: Mapping[str, Any]) -> Any:
    data = _mapping_value(payload, "data")
    issue = _issue(payload)

    explicit = _first_value(payload, data, keys=("newStatus", "new_status", "toStatus", "to_status"))
    if explicit is not None:
        return _status_label(explicit)

    for source in (payload, data, issue):
        value = _nested_name(source, ("state", "workflowState", "workflow_state", "status"))
        if value is not None:
            return value

    direct = _first_value(payload, data, issue, keys=("status", "state", "workflowState", "workflow_state"))
    return _status_label(direct)


def _nested_name(source: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        nested = source.get(key)
        if isinstance(nested, Mapping):
            label = _status_label(nested)
            if label is not None:
                return label
    return None


def _status_label(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value

    return _first_value(value, keys=("name", "title", "label"))


def _first_value(*sources: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    normalized_keys = {_normalize_key(key) for key in keys}
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        for key, value in source.items():
            if _normalize_key(key) in normalized_keys and value is not None:
                return value
    return None


def _mapping_value(source: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = source.get(key)
    return value if isinstance(value, Mapping) else {}


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_key(value: Any) -> str:
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value))
    normalized = re.sub(r"[_\-\s]+", " ", normalized).strip().lower()
    return normalized.replace(" ", "")


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value))
    normalized = re.sub(r"[_\-\s]+", " ", normalized).strip().lower()
    return normalized


def main() -> int:
    """Read a JSON event from stdin and print the requested title update."""

    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
