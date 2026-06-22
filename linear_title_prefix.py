"""Build Linear issue-title updates for research status changes.

The Cursor automation event can arrive as a flat ``triggerContext`` payload,
while Linear webhooks usually nest issue data under ``data`` or ``issue``. This
module keeps the handler pure: callers can apply the returned update action
with their Linear client.
"""

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
    """Return a Linear title update when an issue moves to "to research".

    The returned shape is intentionally small and serializable:
    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``.
    ``None`` means the event does not require a title update.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if not _is_target_status(_first_value(event, _status_candidates)):
        return None

    issue_id = _clean_string(_first_value(event, _issue_id_candidates))
    title = _clean_string(_first_value(event, _title_candidates))
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    for value in _trigger_candidates(event):
        normalized = _normalize_words(value)
        if normalized in {
            "status changed",
            "state changed",
            "workflow state changed",
            "workflowstate changed",
        }:
            return True

    if _is_update_event(event) and _mentions_status_field(event):
        return True

    return False


def _is_update_event(event: Mapping[str, Any]) -> bool:
    for value in _trigger_candidates(event):
        if _normalize_words(value) in {"update", "updated", "issue update", "issue updated", "updated issue"}:
            return True
    return False


def _mentions_status_field(event: Mapping[str, Any]) -> bool:
    for context in _contexts(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _field_collection_mentions_status(context.get(key)):
                return True

        for key in ("changes", "changed", "updatedFrom", "updated_from"):
            value = context.get(key)
            if isinstance(value, Mapping) and _field_collection_mentions_status(value.keys()):
                return True
            if _field_collection_mentions_status(value):
                return True

    return False


def _field_collection_mentions_status(fields: Any) -> bool:
    if fields is None or isinstance(fields, (str, bytes)):
        return _normalize_field_name(fields) in STATUS_FIELDS if fields else False

    if isinstance(fields, Mapping):
        iterable: Iterable[Any] = fields.keys()
    elif isinstance(fields, Iterable):
        iterable = fields
    else:
        return False

    return any(_normalize_field_name(field) in STATUS_FIELDS for field in iterable)


def _trigger_candidates(event: Mapping[str, Any]) -> Iterable[Any]:
    keys = ("trigger", "webhookType", "webhook_type", "action", "type", "eventType", "event_type")
    for context in _contexts(event):
        for key in keys:
            yield context.get(key)


def _status_candidates(context: Mapping[str, Any]) -> Iterable[Any]:
    for key in (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
    ):
        yield context.get(key)

    yield _nested_value(context, ("status", "name"))
    yield _nested_value(context, ("state", "name"))
    yield _nested_value(context, ("workflowState", "name"))
    yield _nested_value(context, ("workflow_state", "name"))

    for key in ("status", "state", "workflowState", "workflow_state"):
        yield context.get(key)

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            yield _change_to_value(changes.get(key))


def _issue_id_candidates(context: Mapping[str, Any]) -> Iterable[Any]:
    for key in ("issueId", "issue_id", "identifier", "key", "id"):
        yield context.get(key)


def _title_candidates(context: Mapping[str, Any]) -> Iterable[Any]:
    yield context.get("title")


def _first_value(event: Mapping[str, Any], extractor: Any) -> Any:
    for context in _contexts(event):
        for value in extractor(context):
            cleaned = _string_or_name(value)
            if cleaned:
                return cleaned
    return None


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event.get("triggerContext"))
    add(event)
    add(event.get("data"))
    add(event.get("issue"))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("data"))
        add(trigger_context.get("issue"))

    return contexts


def _nested_value(context: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = context
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _change_to_value(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value
    for key in ("to", "new", "newValue", "new_value", "after", "name"):
        if key in value:
            return value[key]
    return value


def _is_target_status(value: Any) -> bool:
    return _normalize_words(value) == TARGET_STATUS


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_field_name(value: Any) -> str:
    return _normalize_words(value).replace(" ", "")


def _normalize_words(value: Any) -> str:
    text = _string_or_name(value)
    if not text:
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _string_or_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            cleaned = _clean_string(value.get(key))
            if cleaned:
                return cleaned
        return None
    return _clean_string(value)


def _clean_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2

    result = build_issue_title_update(event)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
