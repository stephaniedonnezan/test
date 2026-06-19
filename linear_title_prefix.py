"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"

_STATUS_FIELDS = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    The automation payloads seen by this repository can be flat Cursor trigger
    contexts or nested Linear webhook events. This function accepts both and
    returns a declarative update action for callers to apply to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _event_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _extract_status(contexts)
    if _normalize_words(status) != RESEARCH_STATUS:
        return None

    issue_id = _extract_issue_id(contexts)
    title = _extract_title(contexts)
    if issue_id is None or title is None:
        return None

    clean_title = title.strip()
    if not clean_title or clean_title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _event_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return relevant payload fragments from most to least specific."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    def child(source: Mapping[str, Any], *keys: str) -> Any:
        value: Any = source
        for key in keys:
            if not isinstance(value, Mapping):
                return None
            value = value.get(key)
        return value

    add(child(event, "automation_trigger_info", "triggerContext"))
    add(child(event, "automationTriggerInfo", "triggerContext"))
    add(child(event, "triggerContext"))
    add(event)

    # Linear webhooks often keep issue data below data/issue while update
    # metadata remains at the top level.
    for source in list(contexts):
        add(child(source, "data", "issue"))
        add(child(source, "issue"))
        add(child(source, "data"))

    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    values = [
        _string_value(context.get(key))
        for context in contexts
        for key in ("trigger", "webhookType", "action", "type", "eventType")
    ]
    normalized = {_normalize_words(value) for value in values if value}

    if any(
        phrase in normalized_value
        for normalized_value in normalized
        for phrase in ("status changed", "state changed", "workflow state changed")
    ):
        return True

    if any(value in {"update", "updated", "issue update", "issue updated", "updated issue"} for value in normalized):
        return _changed_status_field(contexts)

    return False


def _changed_status_field(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "changedFields"):
            if _contains_status_field(context.get(key)):
                return True

        for key in ("changes", "updatedFrom"):
            changes = context.get(key)
            if isinstance(changes, Mapping) and any(_is_status_field(field) for field in changes):
                return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value)

    if isinstance(value, Iterable):
        return any(_is_status_field(field) for field in value)

    return False


def _is_status_field(value: Any) -> bool:
    return _normalize_field(_string_value(value)) in _STATUS_FIELDS


def _extract_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    priority_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "statusName",
        "stateName",
        "workflowStateName",
        "status",
        "state",
        "workflowState",
    )
    return _extract_first_string(contexts, priority_keys)


def _extract_issue_id(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    return _extract_first_string(contexts, ("issueId", "issue_id", "identifier", "key", "id"))


def _extract_title(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    return _extract_first_string(contexts, ("title", "name"))


def _extract_first_string(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _string_value(context.get(key))
            if value and value.strip():
                return value.strip()
    return None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str):
                return nested

    return None


def _normalize_words(value: str | None) -> str:
    if value is None:
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()


def _normalize_field(value: str | None) -> str:
    if value is None:
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
