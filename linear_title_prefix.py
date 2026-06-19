"""Build Linear issue-title update actions for research status changes.

The module intentionally returns a small declarative action instead of calling
Linear directly. The surrounding automation can decide how to execute it.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_status", "workflowstatus"}
STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
ISSUE_UPDATE_TRIGGERS = {"update", "updated", "issue update", "issue updated", "updated issue"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update action for Linear "to research" changes.

    Supported inputs include Cursor's flat ``triggerContext`` payload and common
    Linear webhook shapes such as ``{"action": "update", "data": {"issue": ...}}``.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _first_text(_status_candidates(contexts))
    if _normalize_phrase(new_status) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(_issue_id_candidates(contexts))
    title = _first_text(_title_candidates(contexts))
    if not issue_id or not title:
        return None

    if title.lower().startswith(TITLE_PREFIX.lower()):
        new_title = title
    else:
        new_title = f"{TITLE_PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": new_title,
    }


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect relevant nested dictionaries, ordered from broad to specific."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event)

    for key in ("triggerContext", "webhook", "payload", "data"):
        value = event.get(key)
        add(value)
        if isinstance(value, Mapping):
            add(value.get("issue"))
            add(value.get("node"))
            add(value.get("object"))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("previousIssue"))

    issue = event.get("issue")
    add(issue)

    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    saw_issue_update = False
    saw_update_field_metadata = False

    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type", "eventType"):
            normalized = _normalize_phrase(_text_value(context.get(key)))
            if normalized in STATUS_CHANGE_TRIGGERS:
                return True
            if normalized in ISSUE_UPDATE_TRIGGERS:
                saw_issue_update = True

        if _updated_fields_include_status(context):
            return True
        if _has_update_field_metadata(context):
            saw_update_field_metadata = True

    if saw_update_field_metadata:
        return False

    return saw_issue_update and any(_has_status_change_details(context) for context in contexts)


def _has_update_field_metadata(context: Mapping[str, Any]) -> bool:
    return any(key in context for key in ("updatedFields", "changedFields", "changes"))


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "changedFields"):
        if _field_collection_mentions_status(context.get(key)):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_is_status_field(key) for key in changes)

    return _field_collection_mentions_status(changes)


def _field_collection_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        return any(_is_status_field(key) or _field_collection_mentions_status(item) for key, item in value.items())
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        return any(_field_collection_mentions_status(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    normalized = _normalize_key(_text_value(value))
    return normalized in STATUS_FIELDS


def _has_status_change_details(context: Mapping[str, Any]) -> bool:
    return any(
        _extract_status_from_value(context.get(key))
        for key in ("newStatus", "new_status", "status", "state", "workflowState")
    )


def _status_candidates(contexts: Iterable[Mapping[str, Any]]) -> Iterable[str | None]:
    for context in contexts:
        for key in ("newStatus", "new_status", "toStatus", "to_state", "newState", "newWorkflowState"):
            yield _extract_status_from_value(context.get(key))

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            for key, value in changes.items():
                if _is_status_field(key):
                    yield _extract_changed_value(value)

    for context in contexts:
        for key in ("status", "state", "workflowState"):
            yield _extract_status_from_value(context.get(key))


def _extract_changed_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "to", "after", "name"):
            extracted = _extract_status_from_value(value.get(key))
            if extracted:
                return extracted
    return _extract_status_from_value(value)


def _extract_status_from_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state"):
            extracted = _extract_status_from_value(value.get(key))
            if extracted:
                return extracted
        return None
    return _text_value(value)


def _issue_id_candidates(contexts: Iterable[Mapping[str, Any]]) -> Iterable[str | None]:
    preferred_keys = ("issueId", "issue_id", "identifier", "key")
    fallback_keys = ("id",)

    for keys in (preferred_keys, fallback_keys):
        for context in contexts:
            for key in keys:
                value = _text_value(context.get(key))
                if value:
                    yield value


def _title_candidates(contexts: Iterable[Mapping[str, Any]]) -> Iterable[str | None]:
    for context in contexts:
        for key in ("title", "name"):
            yield _text_value(context.get(key))


def _first_text(values: Iterable[str | None]) -> str | None:
    for value in values:
        text = _text_value(value)
        if text:
            return text
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _normalize_phrase(value: str | None) -> str:
    if not value:
        return ""

    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[\W_]+", " ", separated).strip().lower()


def _normalize_key(value: str | None) -> str:
    return re.sub(r"[\W_]+", "", _normalize_phrase(value))


def main() -> int:
    """Read a JSON event from stdin and print the computed action, if any."""

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(payload)
    if action is not None:
        print(json.dumps(action, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
