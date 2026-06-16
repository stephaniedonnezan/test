"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "statusName",
    "status_name",
    "newState",
    "new_state",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type", "event", "eventType")
_UPDATE_FIELD_KEYS = ("updatedFields", "updatedFrom", "changes")
_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    contexts = list(_ordered_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("id", "issueId", "issue_id", "identifier", "key"))
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title or _already_prefixed(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _ordered_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield payload fragments from most automation-specific to most generic."""
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield trigger_context

    yield event

    data = event.get("data")
    if isinstance(data, Mapping):
        yield data
        data_issue = data.get("issue")
        if isinstance(data_issue, Mapping):
            yield data_issue

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    context_list = list(contexts)
    generic_update_seen = False

    for context in context_list:
        for key in _TRIGGER_KEYS:
            normalized = _normalize_text(context.get(key))
            if not normalized:
                continue
            if "status" in normalized and "change" in normalized:
                return True
            if "state" in normalized and "change" in normalized:
                return True
            if normalized in {"update", "updated", "issue updated", "updated issue"}:
                generic_update_seen = True

    return generic_update_seen and _has_status_update_marker(context_list)


def _has_status_update_marker(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _UPDATE_FIELD_KEYS:
            value = context.get(key)
            if _contains_status_field(value):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value)
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    normalized = _normalize_text(value).replace(" ", "")
    return normalized in _STATUS_FIELD_NAMES or normalized == "workflowstate"


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    context_list = list(contexts)

    explicit_status = _first_text(context_list, _EXPLICIT_STATUS_KEYS)
    if explicit_status:
        return explicit_status

    for context in context_list:
        direct_status = _text_value(context.get("status"))
        if direct_status:
            return direct_status

        state_status = _named_value(context.get("state"))
        if state_status:
            return state_status

        workflow_status = _named_value(context.get("workflowState"))
        if workflow_status:
            return workflow_status

    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            text = _text_value(context.get(key))
            if text:
                return text
    return None


def _named_value(value: Any) -> str | None:
    text = _text_value(value)
    if text:
        return text
    if isinstance(value, Mapping):
        return _text_value(value.get("name"))
    return None


def _text_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _already_prefixed(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    with_spaces = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    alphanumeric = re.sub(r"[^A-Za-z0-9]+", " ", with_spaces)
    return " ".join(alphanumeric.casefold().split())


def main() -> int:
    update = build_issue_title_update(json.load(sys.stdin))
    if update:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
