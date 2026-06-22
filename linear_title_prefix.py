"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")

_TRIGGER_KEYS = (
    "trigger",
    "webhookType",
    "webhook_type",
    "action",
    "type",
    "event",
    "eventType",
    "event_type",
)
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "targetStatus",
    "target_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_CURRENT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_TITLE_KEYS = ("title", "name")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_CHANGE_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
    "changes",
    "change",
    "updatedFrom",
    "updated_from",
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update when an issue moves to To Research.

    The function is intentionally side-effect free so it can be used by an
    automation runtime, a queue worker, or the included stdin JSON CLI.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_candidate_contexts(event))
    if not _is_status_change(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_token(new_status) != TARGET_STATUS:
        return None

    title = _first_text(contexts, _TITLE_KEYS)
    if not title or _has_research_prefix(title):
        return None

    issue_id = _first_text(contexts, _ISSUE_ID_KEYS)
    if not issue_id:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{RESEARCH_TITLE_PREFIX}: {title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely issue/trigger payloads in precedence order."""

    seen: set[int] = set()

    def emit(value: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            yield value

    for key in ("triggerContext", "trigger_context"):
        yield from emit(event.get(key))

    for key in ("automationTriggerInfo", "automation_trigger_info"):
        automation_info = event.get(key)
        if isinstance(automation_info, Mapping):
            for trigger_key in ("triggerContext", "trigger_context"):
                yield from emit(automation_info.get(trigger_key))

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        yield from emit(issue)
        yield from emit(data)

    yield from emit(event.get("issue"))
    yield from emit(event)


def _is_status_change(contexts: Iterable[Mapping[str, Any]]) -> bool:
    contexts = list(contexts)
    trigger_values = [
        _normalize_token(context[key])
        for context in contexts
        for key in _TRIGGER_KEYS
        if key in context
    ]

    if any(_is_direct_status_change_trigger(value) for value in trigger_values):
        return True

    if _changed_fields_include_status(contexts):
        return True

    return any(value in {"issue updated", "issue update", "updated issue"} for value in trigger_values) and (
        "update" in trigger_values or "updated" in trigger_values
    )


def _is_direct_status_change_trigger(value: str) -> bool:
    words = set(value.split())
    if not words.intersection({"status", "state"}):
        return False

    return bool(words.intersection({"change", "changed", "update", "updated"}))


def _changed_fields_include_status(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _CHANGE_KEYS:
            if key in context and _change_value_includes_status(context[key]):
                return True
    return False


def _change_value_includes_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) for key in value)

    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Iterable):
        for item in value:
            if isinstance(item, Mapping):
                field_name = _first_text((item,), ("field", "fieldName", "field_name", "name", "key"))
                if field_name and _is_status_field_name(field_name):
                    return True
            elif _is_status_field_name(item):
                return True

    return False


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_token(value)
    compact = normalized.replace(" ", "")
    return compact in {"status", "statusid", "state", "stateid", "workflowstate", "workflowstateid"}


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    contexts = list(contexts)

    status = _first_text(contexts, _NEW_STATUS_KEYS)
    if status:
        return status

    for context in contexts:
        for key in ("changes", "change", "updatedFields", "updated_fields", "changedFields", "changed_fields"):
            status = _extract_status_from_change_value(context.get(key))
            if status:
                return status

    return _first_text(contexts, _CURRENT_STATUS_KEYS)


def _extract_status_from_change_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, change in value.items():
            if _is_status_field_name(key):
                return _status_from_value(change)

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for item in value:
            if not isinstance(item, Mapping):
                continue
            field_name = _first_text((item,), ("field", "fieldName", "field_name", "name", "key"))
            if field_name and _is_status_field_name(field_name):
                status = _status_from_value(item)
                if status:
                    return status

    return None


def _status_from_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "to", "after", "new", "value", "name", "title"):
            status = _coerce_text(value.get(key))
            if status:
                return status
        return None

    return _coerce_text(value)


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, Mapping):
                value = _first_text((value,), ("name", "title", "identifier", "key", "id"))
            text = _coerce_text(value)
            if text:
                return text
    return None


def _coerce_text(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


def _normalize_token(value: Any) -> str:
    text = _coerce_text(value)
    if text is None:
        return ""

    text = _CAMEL_BOUNDARY.sub(" ", text)
    text = _NON_ALNUM.sub(" ", text.lower())
    return " ".join(text.split())


def _has_research_prefix(title: str) -> bool:
    return title.strip().lower().startswith(RESEARCH_TITLE_PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
