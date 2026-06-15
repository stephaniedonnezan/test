"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELD_NAMES = {
    "status",
    "status id",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
}
DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "state updated",
    "workflow state changed",
    "workflow state change",
    "workflow state updated",
}
GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research.

    The returned value is intentionally side-effect free so the automation
    runtime can decide how to apply the update to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_collect_mappings(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _find_new_status(contexts)
    if _normalize_words(new_status) != RESEARCH_STATUS:
        return None

    issue_title = _find_issue_title(contexts)
    issue_id = _find_issue_id(contexts)
    if not issue_title or not issue_id:
        return None

    title = issue_title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{RESEARCH_PREFIX}: {title}",
    }


def _collect_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _collect_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _collect_mappings(child)


def _normalize_words(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    words = value.strip()
    if not words:
        return None

    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", words)
    words = re.sub(r"[_\-/]+", " ", words)
    words = re.sub(r"\s+", " ", words)
    return words.strip().lower()


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    event_values = []
    for context in contexts:
        for key in ("trigger", "event", "eventType", "webhookType", "action", "type"):
            normalized = _normalize_words(context.get(key))
            if normalized:
                event_values.append(normalized)

    if any(value in DIRECT_STATUS_CHANGE_EVENTS for value in event_values):
        return True

    return (
        any(value in GENERIC_UPDATE_EVENTS for value in event_values)
        and _has_status_change_metadata(contexts)
    )


def _has_status_change_metadata(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        updated_fields = context.get("updatedFields") or context.get("updated_fields")
        if _contains_status_field(updated_fields):
            return True

        for key in ("changes", "changed", "updatedFrom", "updated_from"):
            changes = context.get(key)
            if isinstance(changes, Mapping) and _contains_status_field(changes.keys()):
                return True

    return False


def _contains_status_field(fields: Any) -> bool:
    if isinstance(fields, str):
        fields = [fields]

    if not isinstance(fields, Iterable):
        return False

    for field in fields:
        normalized = _normalize_words(field)
        if normalized in STATUS_FIELD_NAMES:
            return True

    return False


def _find_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in (
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
        ):
            value = _string_or_name(context.get(key))
            if value:
                return value

    for context in contexts:
        changes = context.get("changes") or context.get("changed")
        if isinstance(changes, Mapping):
            for key in ("status", "state", "workflowState", "workflow_state"):
                value = _new_value_from_change(changes.get(key))
                if value:
                    return value

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = _string_or_name(context.get(key))
            if value:
                return value

    return None


def _new_value_from_change(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("new", "to", "after", "current", "value", "name"):
            changed_value = _string_or_name(value.get(key))
            if changed_value:
                return changed_value

    return _string_or_name(value)


def _string_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "value"):
            nested = _string_or_name(value.get(key))
            if nested:
                return nested

    return None


def _find_issue_title(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        title = _string_or_name(context.get("title"))
        if title:
            return title

    return None


def _find_issue_id(contexts: list[Mapping[str, Any]]) -> str | None:
    title_contexts = [
        context for context in contexts if _string_or_name(context.get("title"))
    ]

    for context in [*title_contexts, *contexts]:
        for key in ("issueId", "issue_id", "identifier", "key", "id"):
            issue_id = _string_or_name(context.get(key))
            if issue_id:
                return issue_id

    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(RESEARCH_PREFIX.lower())


def main() -> int:
    payload = json.load(sys.stdin)
    result = build_issue_title_update(payload)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
