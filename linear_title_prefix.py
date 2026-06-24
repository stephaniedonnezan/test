"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


CURSOR_RESEARCHING_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
TITLE_SEPARATOR = ": "

STATUS_FIELD_NAMES = frozenset(
    {
        "status",
        "state",
        "workflow state",
        "workflowstate",
        "workflow_state",
        "workflow status",
        "workflow status id",
        "status id",
    }
)

TRIGGER_FIELD_NAMES = ("trigger", "webhookType", "webhook_type", "action", "type")
GENERIC_UPDATE_TRIGGERS = frozenset({"update", "updated", "issue update", "issue updated", "updated issue"})
DIRECT_STATUS_TRIGGERS = frozenset(
    {
        "status change",
        "status changed",
        "state change",
        "state changed",
        "workflow state change",
        "workflow state changed",
    }
)


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return the Linear issue title update action for matching events.

    The automation input has varied between a flat Cursor ``triggerContext`` and
    nested Linear webhook payloads. This function intentionally reads from both
    shapes while keeping the behavior narrow: only status changes to
    ``to research`` produce an update.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _first_status_name(contexts)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_string(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_string(contexts, ("title", "name"))
    if issue_id is None or title is None:
        return None

    title = title.strip()
    issue_id = issue_id.strip()
    if not title or not issue_id or _has_cursor_researching_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{CURSOR_RESEARCHING_PREFIX}{TITLE_SEPARATOR}{title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility wrapper for callers that name the event directly."""

    return build_issue_title_update(event)


def _contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield relevant payload dictionaries from outermost to innermost."""

    yield event

    automation_info = event.get("automation_trigger_info") or event.get("automationTriggerInfo")
    if isinstance(automation_info, Mapping):
        yield automation_info
        trigger_context = automation_info.get("triggerContext") or automation_info.get("trigger_context")
        if isinstance(trigger_context, Mapping):
            yield trigger_context

    trigger_context = event.get("triggerContext") or event.get("trigger_context")
    if isinstance(trigger_context, Mapping):
        yield trigger_context

    data = event.get("data")
    if isinstance(data, Mapping):
        yield data
        for key in ("issue", "node"):
            value = data.get(key)
            if isinstance(value, Mapping):
                yield value

    for key in ("issue", "node"):
        value = event.get(key)
        if isinstance(value, Mapping):
            yield value


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    if _has_direct_status_trigger(contexts):
        return True

    if not _has_generic_update_trigger(contexts):
        return False

    return any(_updated_fields_include_status(context) or _changes_include_status(context) for context in contexts)


def _has_direct_status_trigger(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for field_name in TRIGGER_FIELD_NAMES:
            normalized = _normalize(context.get(field_name))
            if normalized in DIRECT_STATUS_TRIGGERS:
                return True
    return False


def _has_generic_update_trigger(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for field_name in TRIGGER_FIELD_NAMES:
            normalized = _normalize(context.get(field_name))
            if normalized in GENERIC_UPDATE_TRIGGERS:
                return True
    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields") or context.get("updated_fields")
    if isinstance(updated_fields, str):
        updated_fields = [updated_fields]
    if not isinstance(updated_fields, Iterable):
        return False

    for field_name in updated_fields:
        if _normalize_field_name(field_name) in STATUS_FIELD_NAMES:
            return True
    return False


def _changes_include_status(context: Mapping[str, Any]) -> bool:
    changes = context.get("changes") or context.get("changed")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(field_name) in STATUS_FIELD_NAMES for field_name in changes)

    if isinstance(changes, Iterable) and not isinstance(changes, (str, bytes)):
        for change in changes:
            if isinstance(change, Mapping):
                field_name = change.get("field") or change.get("fieldName") or change.get("name") or change.get("key")
                if _normalize_field_name(field_name) in STATUS_FIELD_NAMES:
                    return True
            elif _normalize_field_name(change) in STATUS_FIELD_NAMES:
                return True

    return False


def _first_status_name(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
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
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    for context in contexts:
        status = _first_string_from_context(context, explicit_keys)
        if status is not None:
            return status

    for context in contexts:
        status = _first_string_from_context(context, fallback_keys)
        if status is not None:
            return status

    for context in contexts:
        status = _status_from_changes(context)
        if status is not None:
            return status

    return None


def _status_from_changes(context: Mapping[str, Any]) -> str | None:
    changes = context.get("changes") or context.get("changed")
    if not isinstance(changes, Mapping):
        return None

    for field_name, change in changes.items():
        if _normalize_field_name(field_name) not in STATUS_FIELD_NAMES:
            continue

        if isinstance(change, Mapping):
            return _coerce_string(
                change.get("new")
                or change.get("to")
                or change.get("after")
                or change.get("newValue")
                or change.get("new_value")
            )
        return _coerce_string(change)

    return None


def _first_string(contexts: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        value = _first_string_from_context(context, keys)
        if value is not None:
            return value
    return None


def _first_string_from_context(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _coerce_string(context.get(key))
        if value is not None:
            return value
    return None


def _coerce_string(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "key", "id"):
            nested = value.get(key)
            if isinstance(nested, str):
                return nested

    return None


def _has_cursor_researching_prefix(title: str) -> bool:
    return title.casefold().startswith(CURSOR_RESEARCHING_PREFIX.casefold())


def _normalize(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip().casefold()
    return text or None


def _normalize_field_name(value: Any) -> str | None:
    return _normalize(value)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print(f"Invalid JSON input: {error}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
