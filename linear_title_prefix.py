"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
PREFIXED_TITLE_PREFIX = f"{PREFIX}: "
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research.

    The automation runner is expected to perform the returned update. Returning
    ``None`` means the event is not relevant or is missing the required issue
    details.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if not issue_id or not title:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": _prefix_title(title),
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_values = list(_event_type_values(event))
    if any(_is_direct_status_change(value) for value in event_values):
        return True

    return any(_is_generic_update(value) for value in event_values) and _has_status_field_marker(event)


def _event_type_values(event: Mapping[str, Any]) -> Iterable[Any]:
    for payload in _all_mappings(event):
        for key in ("trigger", "webhookType", "webhook_type", "action", "type"):
            if key in payload:
                yield payload[key]


def _is_direct_status_change(value: Any) -> bool:
    normalized = _normalize_text(value)
    return normalized in {"status changed", "status change", "state changed", "state change"}


def _is_generic_update(value: Any) -> bool:
    normalized = _normalize_text(value)
    return normalized in {"update", "updated", "issue update", "issue updated", "updated issue"}


def _has_status_field_marker(event: Mapping[str, Any]) -> bool:
    return any(_is_status_field_name(field_name) for field_name in _changed_field_names(event))


def _changed_field_names(event: Mapping[str, Any]) -> Iterable[Any]:
    for payload in _all_mappings(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            value = payload.get(key)
            if isinstance(value, Mapping):
                yield from value.keys()
            elif isinstance(value, list | tuple | set):
                yield from value
            elif value is not None:
                yield value

        for key in ("changes", "updatedFrom", "updated_from"):
            value = payload.get(key)
            if isinstance(value, Mapping):
                yield from value.keys()
            elif isinstance(value, list | tuple | set):
                for item in value:
                    if isinstance(item, Mapping):
                        yield from item.keys()
                        yield item.get("field")
                        yield item.get("fieldName")
                        yield item.get("name")
                    else:
                        yield item


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_text(value)
    return normalized in {
        "status",
        "status id",
        "state",
        "state id",
        "workflow state",
        "workflow state id",
        "workflowstate",
        "workflowstate id",
    }


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for payload in _candidate_payloads(event):
        status = _value_from_keys(
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
        if status:
            return status

    status_from_changes = _status_from_changes(event)
    if status_from_changes:
        return status_from_changes

    for payload in _candidate_payloads(event):
        status = _current_status(payload)
        if status:
            return status

    return None


def _status_from_changes(event: Mapping[str, Any]) -> str | None:
    for payload in _all_mappings(event):
        changes = payload.get("changes")
        if isinstance(changes, Mapping):
            for key, value in changes.items():
                if _is_status_field_name(key):
                    status = _new_value(value)
                    if status:
                        return status
        elif isinstance(changes, list | tuple):
            for change in changes:
                if not isinstance(change, Mapping):
                    continue
                field_name = change.get("field") or change.get("fieldName") or change.get("name")
                if _is_status_field_name(field_name):
                    status = _new_value(change)
                    if status:
                        return status

    return None


def _new_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in (
            "newValue",
            "new_value",
            "to",
            "after",
            "value",
            "name",
            "title",
        ):
            status = _string_value(value.get(key))
            if status:
                return status
    return _string_value(value)


def _current_status(payload: Mapping[str, Any]) -> str | None:
    for key in ("status", "state", "workflowState", "workflow_state"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            status = _value_from_keys(value, ("name", "title", "status", "state"))
            if status:
                return status
        else:
            status = _string_value(value)
            if status:
                return status
    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for payload in _candidate_payloads(event):
        issue_id = _value_from_keys(payload, ("issueId", "issue_id", "identifier", "key", "id"))
        if issue_id:
            return issue_id
    return None


def _extract_title(event: Mapping[str, Any]) -> str | None:
    for payload in _candidate_payloads(event):
        title = _value_from_keys(payload, ("title",))
        if title:
            return title
    return None


def _prefix_title(title: str) -> str:
    stripped = title.strip()
    if stripped.casefold().startswith(PREFIX.casefold()):
        return stripped
    return f"{PREFIXED_TITLE_PREFIX}{stripped}"


def _candidate_payloads(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    seen: set[int] = set()

    def add(value: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            yield value

    yield from add(_nested_value(event, ("triggerContext",)))
    yield from add(_nested_value(event, ("trigger_context",)))
    yield from add(_nested_value(event, ("automation_trigger_info", "triggerContext")))
    yield from add(_nested_value(event, ("automationTriggerInfo", "triggerContext")))
    yield from add(_nested_value(event, ("data", "issue")))
    yield from add(_nested_value(event, ("issue",)))
    yield from add(_nested_value(event, ("data",)))
    yield from add(event)


def _all_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested_value in value.values():
            yield from _all_mappings(nested_value)
    elif isinstance(value, list | tuple | set):
        for item in value:
            yield from _all_mappings(item)


def _nested_value(value: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = value
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _value_from_keys(payload: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = _string_value(payload.get(key))
        if value:
            return value
    return None


def _string_value(value: Any) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        stripped = value.strip()
    elif isinstance(value, int | float):
        stripped = str(value).strip()
    else:
        return None
    return stripped or None


def _normalize_text(value: Any) -> str:
    text = _string_value(value)
    if not text:
        return ""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON input: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
