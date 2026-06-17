"""Build Linear issue-title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
TITLE_UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue enters the To Research state.

    The automation receives slightly different payloads depending on whether it
    was triggered by Cursor's flat trigger context or Linear's nested webhook
    shape. This function keeps the output narrow and side-effect free so callers
    can decide how to apply the returned update.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    if not _is_status_change_event(payload):
        return None

    status = _new_status(payload)
    if _normalize_phrase(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, "issueId", "issue_id", "identifier", "key", "id")
    title = _first_text(payload, "title", "name")
    if not issue_id or not title:
        return None

    if _has_title_prefix(title):
        return None

    return {
        "action": TITLE_UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common nested payload sections with precedence for trigger fields."""

    trigger_context = _mapping(event.get("triggerContext"))
    data = _mapping(event.get("data"))
    issue = _mapping(data.get("issue")) or _mapping(event.get("issue"))

    flattened: dict[str, Any] = {}
    flattened.update(issue)
    flattened.update(data)
    flattened.update(trigger_context)
    flattened.update(event)

    # Prefer Linear's human-readable issue identifier over opaque webhook ids.
    for source in (trigger_context, issue, data, event):
        identifier = _first_text(source, "issueId", "issue_id", "identifier", "key")
        if identifier:
            flattened["issueId"] = identifier
            break

    # Keep useful nested issue fields available when outer metadata has its own
    # id/type/action keys.
    title = _first_text(trigger_context, "title") or _first_text(issue, "title", "name")
    if title:
        flattened["title"] = title

    status = _extract_status_from(issue.get("state")) or _extract_status_from(
        issue.get("workflowState")
    )
    if status and not _first_text(flattened, "status", "newStatus", "new_status"):
        flattened["status"] = status

    return flattened


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    direct_status_triggers = {
        "status changed",
        "statuschange",
        "state changed",
        "statechange",
        "workflow state changed",
        "workflowstatechanged",
    }
    update_triggers = {
        "update",
        "updated",
        "issue update",
        "issue updated",
        "updated issue",
    }

    trigger_values = [
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    ]
    normalized_triggers = {_normalize_phrase(value) for value in trigger_values if value}

    if normalized_triggers & direct_status_triggers:
        return True

    has_update_trigger = bool(normalized_triggers & update_triggers)
    return has_update_trigger and _changed_fields_include_status(payload)


def _changed_fields_include_status(payload: Mapping[str, Any]) -> bool:
    status_fields = {"status", "state", "workflowstate", "workflow state"}
    field_values: list[Any] = [
        payload.get("updatedFields"),
        payload.get("updated_fields"),
        payload.get("changedFields"),
        payload.get("changed_fields"),
        payload.get("changes"),
    ]

    for field in _walk_values(field_values):
        if isinstance(field, Mapping):
            keys = {_normalize_field_name(key) for key in field.keys()}
            if keys & status_fields:
                return True
            field_name = _first_text(field, "field", "name", "key")
            if _normalize_field_name(field_name) in status_fields:
                return True
            continue

        if _normalize_field_name(field) in status_fields:
            return True

    return False


def _new_status(payload: Mapping[str, Any]) -> str | None:
    explicit_status = _first_text(
        payload,
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "statusName",
        "status_name",
    )
    if explicit_status:
        return explicit_status

    for changes_key in ("changes", "updatedFields", "updated_fields"):
        status = _status_from_change(payload.get(changes_key))
        if status:
            return status

    return (
        _extract_status_from(payload.get("status"))
        or _extract_status_from(payload.get("state"))
        or _extract_status_from(payload.get("workflowState"))
        or _extract_status_from(payload.get("workflow_state"))
    )


def _status_from_change(change_data: Any) -> str | None:
    if isinstance(change_data, Mapping):
        for key in (
            "status",
            "state",
            "workflowState",
            "workflow_state",
            "newStatus",
            "newState",
        ):
            status = _extract_status_from(change_data.get(key))
            if status:
                return status
        return _first_text(change_data, "to", "newValue", "new_value", "after")

    if isinstance(change_data, Iterable) and not isinstance(change_data, (str, bytes)):
        for item in change_data:
            if not isinstance(item, Mapping):
                continue
            field_name = _normalize_field_name(_first_text(item, "field", "name", "key"))
            if field_name in {"status", "state", "workflowstate", "workflow state"}:
                status = _first_text(item, "to", "newValue", "new_value", "after")
                if status:
                    return status

    return None


def _extract_status_from(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _first_text(value, "name", "title", "label")
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _first_text(mapping: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = mapping.get(key)
        text = _extract_text(value)
        if text:
            return text
    return None


def _extract_text(value: Any) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, (int, float)):
        return str(value)
    return None


def _has_title_prefix(title: str) -> bool:
    return title.strip().lower().startswith(TITLE_PREFIX.lower())


def _normalize_phrase(value: Any) -> str:
    text = _extract_status_from(value) or _extract_text(value) or ""
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _normalize_field_name(value: Any) -> str:
    return _normalize_phrase(value).replace(" ", "")


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _walk_values(values: Iterable[Any]) -> Iterable[Any]:
    for value in values:
        if isinstance(value, Mapping):
            yield value
            continue
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            yield from value
            continue
        yield value


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
