"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_TRIGGER_KEYS = (
    "trigger",
    "webhookType",
    "webhook_type",
    "action",
    "type",
    "eventType",
    "event_type",
)
_DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue updated",
    "updated issue",
}
_STATUS_FIELD_NAMES = {
    "status",
    "status id",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
    "workflow status",
    "workflow status id",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title update action for relevant status changes.

    The automation should only update titles when an issue is moved to
    "to research". Payloads can be either the flat Cursor automation shape or a
    nested Linear webhook shape.
    """

    if not isinstance(event, Mapping):
        return None

    payloads = list(_ordered_payloads(event))
    if not _is_status_change_event(payloads):
        return None

    new_status = _extract_new_status(payloads)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(
        payloads,
        ("issueId", "issue_id", "identifier", "key", "id"),
    )
    title = _first_text(payloads, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if title.lower().startswith(PREFIX.lower()):
        updated_title = title
    else:
        updated_title = f"{PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": updated_title,
    }


def _ordered_payloads(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely payload objects in a useful precedence order."""

    candidates: list[Any] = []
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        candidates.append(trigger_context)
        candidates.extend(_nested_payloads(trigger_context))

    candidates.extend(_nested_payloads(event))
    candidates.append(event)

    seen: set[int] = set()
    for candidate in candidates:
        if isinstance(candidate, Mapping) and id(candidate) not in seen:
            seen.add(id(candidate))
            yield candidate


def _nested_payloads(payload: Mapping[str, Any]) -> list[Any]:
    nested: list[Any] = []
    data = payload.get("data")
    issue = payload.get("issue")
    node = payload.get("node")

    for value in (issue, data, node):
        if isinstance(value, Mapping):
            nested.append(value)

    if isinstance(data, Mapping):
        for key in ("issue", "node"):
            value = data.get(key)
            if isinstance(value, Mapping):
                nested.append(value)

    return nested


def _is_status_change_event(payloads: list[Mapping[str, Any]]) -> bool:
    triggers = {
        _normalize(payload.get(key))
        for payload in payloads
        for key in _TRIGGER_KEYS
        if payload.get(key) is not None
    }

    if triggers & _DIRECT_STATUS_TRIGGERS:
        return True

    if triggers & _UPDATE_TRIGGERS:
        return _has_status_change_marker(payloads)

    return _has_status_change_marker(payloads) and not triggers


def _has_status_change_marker(payloads: list[Mapping[str, Any]]) -> bool:
    for payload in payloads:
        if _updated_fields_include_status(payload.get("updatedFields")):
            return True
        if _updated_fields_include_status(payload.get("updated_fields")):
            return True
        if _mapping_has_status_key(payload.get("changes")):
            return True
        if _mapping_has_status_key(payload.get("updatedFrom")):
            return True
        if _mapping_has_status_key(payload.get("updated_from")):
            return True

    return False


def _updated_fields_include_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if not isinstance(value, Iterable) or isinstance(value, (bytes, Mapping)):
        return False

    for field in value:
        if isinstance(field, Mapping):
            names = (field.get("name"), field.get("field"), field.get("key"))
            if any(_is_status_field_name(name) for name in names):
                return True
        elif _is_status_field_name(field):
            return True

    return False


def _mapping_has_status_key(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    return any(_is_status_field_name(key) for key in value.keys())


def _extract_new_status(payloads: list[Mapping[str, Any]]) -> str | None:
    for payload in payloads:
        value = _first_present(
            payload,
            (
                "newStatus",
                "new_status",
                "newState",
                "new_state",
                "newWorkflowState",
                "new_workflow_state",
                "statusName",
                "status_name",
            ),
        )
        if value is not None:
            return _status_name(value)

    for payload in payloads:
        status = _status_from_changes(payload.get("changes"))
        if status is not None:
            return status

    for payload in payloads:
        value = _first_present(payload, ("status", "state", "workflowState"))
        if value is not None:
            return _status_name(value)

    return None


def _status_from_changes(changes: Any) -> str | None:
    if not isinstance(changes, Mapping):
        return None

    for field, change in changes.items():
        if not _is_status_field_name(field):
            continue

        if isinstance(change, Mapping):
            for key in ("to", "new", "newValue", "after", "toName", "name"):
                value = change.get(key)
                if value is not None:
                    return _status_name(value)
        elif change is not None:
            return _status_name(change)

    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "id"):
            nested_value = value.get(key)
            if nested_value is not None:
                return str(nested_value)
        return None
    if value is None:
        return None
    return str(value)


def _first_text(payloads: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        for payload in payloads:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _first_present(payload: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


def _is_status_field_name(value: Any) -> bool:
    return _normalize(value) in _STATUS_FIELD_NAMES


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
