"""Build Linear issue title updates for Cursor research-status automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    contexts = list(_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _new_status(contexts)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely payload locations from most issue-specific to broadest."""

    yielded: list[int] = []

    def emit(value: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(value, Mapping) and id(value) not in yielded:
            yielded.append(id(value))
            yield value

    trigger_context = event.get("triggerContext") or event.get("trigger_context")
    automation_info = event.get("automation_trigger_info") or event.get("automationTriggerInfo")
    automation_context = (
        automation_info.get("triggerContext") if isinstance(automation_info, Mapping) else None
    )
    data = event.get("data")
    issue = event.get("issue")
    data_issue = data.get("issue") if isinstance(data, Mapping) else None

    yield from emit(automation_context)
    yield from emit(trigger_context)
    yield from emit(data_issue)
    yield from emit(issue)
    yield from emit(data)
    yield from emit(event)


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    context_list = list(contexts)
    event_names = [
        value
        for context in context_list
        for key in ("trigger", "triggerType", "webhookType", "action", "type", "eventType")
        for value in (context.get(key),)
        if value is not None
    ]

    if any(_is_direct_status_change(value) for value in event_names):
        return True

    is_issue_update = any(
        _normalize(value) in {"update", "updated", "issue updated", "updated issue"}
        for value in event_names
    )
    return is_issue_update and _updated_fields_include_status(context_list)


def _is_direct_status_change(value: Any) -> bool:
    normalized = _normalize(value)
    if normalized in {
        "status changed",
        "status change",
        "status updated",
        "state changed",
        "state updated",
        "workflow state changed",
        "workflow state updated",
    }:
        return True

    has_status_field = any(field in normalized.split() for field in ("status", "state"))
    if "workflow state" in normalized:
        has_status_field = True
    has_change_verb = any(
        verb in normalized.split() for verb in ("changed", "change", "updated", "update")
    )
    return has_status_field and has_change_verb


def _updated_fields_include_status(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _field_collection_includes_status(context.get(key)):
                return True

        changes = context.get("changes") or context.get("changed") or context.get("updatedFrom")
        if isinstance(changes, Mapping):
            if any(_is_status_field(key) for key in changes):
                return True
        elif _field_collection_includes_status(changes):
            return True

    return False


def _field_collection_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value)

    if isinstance(value, Iterable):
        return any(_is_status_field(item) for item in value)

    return False


def _is_status_field(value: Any) -> bool:
    return _normalize(value).replace(" ", "") in STATUS_FIELDS


def _new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    context_list = list(contexts)
    explicit_keys = (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
    )
    explicit = _first_text(context_list, explicit_keys)
    if explicit:
        return explicit

    for context in context_list:
        status = _first_text((context,), ("status",))
        if status:
            return status

        changed_status = _status_from_changes(context)
        if changed_status:
            return changed_status

        for key in ("state", "workflowState", "workflow_state"):
            value = context.get(key)
            if isinstance(value, Mapping):
                name = _first_text((value,), ("name", "title", "status"))
                if name:
                    return name
            elif isinstance(value, str):
                return value.strip()

    return None


def _status_from_changes(context: Mapping[str, Any]) -> str | None:
    changes = context.get("changes") or context.get("changed") or context.get("updatedFrom")
    if not isinstance(changes, Mapping):
        return None

    for field, value in changes.items():
        if not _is_status_field(field):
            continue

        if isinstance(value, Mapping):
            changed_to = _first_text((value,), ("to", "new", "after", "value", "name"))
            if changed_to:
                return changed_to
        elif isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped

    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str):
                stripped = value.strip()
                if stripped:
                    return stripped
            elif isinstance(value, int):
                return str(value)
    return None


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", separated)
    return " ".join(normalized.casefold().split())


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print(f"Invalid JSON: {error}", file=sys.stderr)
        return 1

    result = build_issue_title_update(payload)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
