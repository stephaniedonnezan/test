"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


ACTION = "update_issue_title"
PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "status",
    "state",
    "workflowState",
    "workflow_state",
)
_STATUS_FIELD_NAMES = {"status", "state", "workflow state"}
_UPDATE_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
    "changes",
    "updatedFrom",
    "updated_from",
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue enters research.

    The function accepts Cursor automation payloads and common Linear webhook
    shapes. It intentionally returns data describing the update instead of
    performing the API call, so callers can decide how to apply the action.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_iter_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    status = _extract_new_status(contexts)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(contexts)
    title = _extract_title(contexts)
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _iter_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely event and issue containers from outermost to innermost."""

    yield event

    for key in ("triggerContext", "trigger_context", "payload"):
        value = event.get(key)
        if isinstance(value, Mapping):
            yield value

    data = event.get("data")
    if isinstance(data, Mapping):
        yield data
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            yield issue

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "event", "eventType", "webhookEvent", "action", "type"):
            value = context.get(key)
            normalized = _normalize_text(value)
            if "status" in normalized and ("change" in normalized or "changed" in normalized):
                return True

    is_update_event = any(
        _normalize_text(context.get(key)) in {"update", "updated", "issue updated", "updated issue"}
        for context in contexts
        for key in ("trigger", "event", "eventType", "webhookEvent", "action", "type")
    )
    return is_update_event and _status_field_was_updated(contexts)


def _status_field_was_updated(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _UPDATE_FIELD_KEYS:
            if key not in context:
                continue
            if _contains_status_field(context[key]):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_text(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(
            _normalize_text(key) in _STATUS_FIELD_NAMES or _contains_status_field(item)
            for key, item in value.items()
        )

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _extract_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in _NEW_STATUS_KEYS:
            status = _status_value(context.get(key))
            if status:
                return status

    for context in contexts:
        for key in _UPDATE_FIELD_KEYS:
            status = _status_from_updated_fields(context.get(key))
            if status:
                return status

    return None


def _status_from_updated_fields(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for field_name, field_value in value.items():
        if _normalize_text(field_name) not in _STATUS_FIELD_NAMES:
            continue

        status = _status_value(field_value)
        if status:
            return status

        if isinstance(field_value, Mapping):
            for key in ("to", "new", "after", "current", "name"):
                status = _status_value(field_value.get(key))
                if status:
                    return status

    return None


def _status_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state", "workflowState"):
            status = _status_value(value.get(key))
            if status:
                return status

    return None


def _extract_issue_id(contexts: list[Mapping[str, Any]]) -> str | None:
    for key in ("issueId", "issue_id", "identifier", "key"):
        issue_id = _first_text_value(contexts, key)
        if issue_id:
            return issue_id

    for context in contexts:
        issue_id = _text_value(context.get("id"))
        if issue_id and "title" in context:
            return issue_id

    return _first_text_value(contexts, "id")


def _extract_title(contexts: list[Mapping[str, Any]]) -> str | None:
    return _first_text_value(contexts, "title")


def _first_text_value(contexts: list[Mapping[str, Any]], key: str) -> str | None:
    for context in contexts:
        value = _text_value(context.get(key))
        if value:
            return value
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            return stripped
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lstrip().lower().startswith(PREFIX.lower())


def _normalize_text(value: Any) -> str:
    if isinstance(value, Mapping):
        value = _status_value(value)
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
