"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate"}
UPDATE_ACTIONS = {"update", "updated", "issueupdate", "issueupdated", "updatedissue"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update when an issue moves to "to research"."""

    if not isinstance(event, Mapping):
        return None

    contexts = list(_context_sources(event))
    if not _is_status_change_event(contexts):
        return None

    if not _contains_target_status(contexts):
        return None

    issue_id = _first_text(_issue_sources(event), ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(_issue_sources(event), ("title", "name"))

    if not issue_id or not title:
        return None

    if _starts_with_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _context_sources(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely trigger/status containers from broad to nested contexts."""

    seen: set[int] = set()

    def visit(value: Any) -> Iterable[Mapping[str, Any]]:
        if not isinstance(value, Mapping) or id(value) in seen:
            return
        seen.add(id(value))
        yield value

        for key in ("automation_trigger_info", "automationTriggerInfo"):
            yield from visit(value.get(key))

        for key in ("triggerContext", "trigger_context"):
            yield from visit(value.get(key))

        data = value.get("data")
        if isinstance(data, Mapping):
            yield from visit(data)
            yield from visit(data.get("issue"))

        yield from visit(value.get("issue"))

    yield from visit(event)


def _issue_sources(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield issue-like containers, preferring Linear/Cursor issue payloads."""

    for key in ("automation_trigger_info", "automationTriggerInfo"):
        wrapper = event.get(key)
        if isinstance(wrapper, Mapping):
            yield from _issue_sources(wrapper)

    for key in ("triggerContext", "trigger_context"):
        context = event.get(key)
        if isinstance(context, Mapping):
            yield context

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            yield issue
        yield data

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue

    yield event


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    contexts = list(contexts)
    if any(_is_direct_status_change(context) for context in contexts):
        return True

    return _is_generic_update(contexts) and _has_status_change_marker(contexts)


def _is_direct_status_change(context: Mapping[str, Any]) -> bool:
    for key in ("trigger", "webhookType", "webhook_type", "action", "type"):
        token = _compact_words(context.get(key))
        if not token:
            continue
        if "statuschanged" in token or "statechanged" in token or "workflowstatechanged" in token:
            return True
    return False


def _is_generic_update(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "webhookType", "webhook_type", "action", "type"):
            if _compact_words(context.get(key)) in UPDATE_ACTIONS:
                return True
    return False


def _has_status_change_marker(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _field_list_contains_status(context.get(key)):
                return True

        for key in ("changes", "updatedFrom", "updated_from"):
            value = context.get(key)
            if isinstance(value, Mapping) and any(_is_status_field(field) for field in value):
                return True

    return False


def _field_list_contains_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if not isinstance(value, Iterable) or isinstance(value, (bytes, bytearray, Mapping)):
        return False

    for item in value:
        if isinstance(item, Mapping):
            names = (
                item.get("field"),
                item.get("name"),
                item.get("key"),
                item.get("property"),
            )
            if any(_is_status_field(name) for name in names):
                return True
        elif _is_status_field(item):
            return True

    return False


def _is_status_field(value: Any) -> bool:
    token = _compact_words(value)
    return any(field in token for field in STATUS_FIELDS)


def _contains_target_status(contexts: Iterable[Mapping[str, Any]]) -> bool:
    return any(_normalize_words(status) == TARGET_STATUS for status in _status_values(contexts))


def _status_values(contexts: Iterable[Mapping[str, Any]]) -> Iterable[Any]:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    contexts = list(contexts)
    for context in contexts:
        for key in explicit_keys:
            yield from _value_names(context.get(key))

    for context in contexts:
        for key in fallback_keys:
            yield from _value_names(context.get(key))

    for context in contexts:
        changes = context.get("changes")
        if isinstance(changes, Mapping):
            for field, change in changes.items():
                if _is_status_field(field):
                    yield from _new_change_values(change)


def _new_change_values(value: Any) -> Iterable[Any]:
    if not isinstance(value, Mapping):
        yield from _value_names(value)
        return

    for key in ("to", "after", "new", "newValue", "new_value", "value"):
        yield from _value_names(value.get(key))


def _value_names(value: Any) -> Iterable[Any]:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value"):
            if key in value:
                yield value[key]
        return

    if value is not None:
        yield value


def _first_text(sources: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for source in sources:
        for key in keys:
            value = source.get(key)
            if isinstance(value, str):
                text = value.strip()
                if text:
                    return text
    return None


def _starts_with_prefix(title: str) -> bool:
    return _normalize_words(title).startswith(_normalize_words(PREFIX))


def _compact_words(value: Any) -> str:
    return _normalize_words(value).replace(" ", "")


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value))
    words = re.sub(r"[^A-Za-z0-9]+", " ", words)
    return " ".join(words.lower().split())


def main() -> int:
    event = json.loads(sys.stdin.read())
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
