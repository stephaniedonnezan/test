"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"

_DIRECT_STATUS_CHANGE_SIGNALS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
    "issue status changed",
    "issue status change",
}
_GENERIC_UPDATE_SIGNALS = {
    "update",
    "updated",
    "issue update",
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
    "workflowstate",
    "workflowstate id",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action for "to research" status changes."""
    if not isinstance(event, Mapping):
        return None

    sources = list(_current_sources(event))
    if not _is_status_change_event(sources):
        return None

    new_status = _find_new_status(sources)
    if _normalize_text(new_status) != RESEARCH_STATUS:
        return None

    issue_id = _find_text(sources, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _find_text(sources, ("title", "name"))
    if issue_id is None or title is None:
        return None

    trimmed_title = title.strip()
    if not trimmed_title or _has_research_prefix(trimmed_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {trimmed_title}",
    }


def _current_sources(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely current issue/status containers, excluding old-value metadata."""
    seen: set[int] = set()

    def add(source: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(source, Mapping) and id(source) not in seen:
            seen.add(id(source))
            yield source

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")

    yield from add(trigger_context)
    if isinstance(trigger_context, Mapping):
        yield from add(trigger_context.get("data"))
        trigger_issue = trigger_context.get("issue")
        yield from add(trigger_issue)
        if isinstance(trigger_context.get("data"), Mapping):
            yield from add(trigger_context["data"].get("issue"))

    yield from add(data)
    if isinstance(data, Mapping):
        yield from add(data.get("issue"))

    yield from add(issue)
    yield from add(event)


def _is_status_change_event(sources: list[Mapping[str, Any]]) -> bool:
    signals = {
        _normalize_text(value)
        for source in sources
        for key in ("trigger", "webhookType", "action", "type", "event")
        if (value := source.get(key)) is not None
    }

    if any(signal in _DIRECT_STATUS_CHANGE_SIGNALS for signal in signals):
        return True

    if not any(signal in _GENERIC_UPDATE_SIGNALS for signal in signals):
        return False

    return any(_has_status_field_change(source) for source in sources)


def _has_status_field_change(source: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "changedFields", "fields"):
        if _contains_status_field(source.get(key)):
            return True

    for key in ("changes", "changed", "updatedFrom", "previous", "previousValues"):
        changed_value = source.get(key)
        if isinstance(changed_value, Mapping) and any(
            _is_status_field(field_name) for field_name in changed_value
        ):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value)
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    return _normalize_text(value) in _STATUS_FIELD_NAMES


def _find_new_status(sources: list[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "statusName",
        "status_name",
        "newState",
        "new_state",
        "stateName",
        "state_name",
        "newWorkflowState",
        "workflowStateName",
    )
    status_keys = ("status", "state", "workflowState", "workflow_state")

    for source in sources:
        value = _find_text_in_source(source, explicit_keys)
        if value is not None:
            return value

    for source in sources:
        value = _find_text_in_source(source, status_keys)
        if value is not None:
            return value

    return None


def _find_text(sources: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for source in sources:
        value = _find_text_in_source(source, keys)
        if value is not None:
            return value
    return None


def _find_text_in_source(source: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = source.get(key)
        text = _to_text(value)
        if text is not None and text.strip():
            return text
    return None


def _to_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return _find_text_in_source(value, ("name", "title", "identifier", "key", "id"))
    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_text(value: Any) -> str:
    text = _to_text(value)
    if text is None:
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text.strip())
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
