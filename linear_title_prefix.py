"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"

_STATUS_CHANGE_MARKERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_UPDATE_MARKERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_STATUS_FIELD_NAMES = {"status", "state", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue enters To Research.

    The automation platform supplies a flat ``triggerContext`` payload, while
    Linear webhooks often nest issue data under ``data`` or ``issue``. This
    function accepts both shapes and returns ``None`` when no title update is
    required.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize_text(_status_name(event)) != "to research":
        return None

    title = _first_text_value(event, ("title",))
    issue_id = _first_text_value(event, ("id", "issueId", "issue_id", "identifier"))
    if not title or not issue_id:
        return None

    stripped_title = title.strip()
    if _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {stripped_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    for context in _candidate_contexts(event):
        for key in ("trigger", "webhookType", "action", "type"):
            marker = _normalize_text(context.get(key))
            if marker in _STATUS_CHANGE_MARKERS:
                return True

    if _has_update_marker(event):
        return _updated_fields_include_status(event)

    return False


def _has_update_marker(event: Mapping[str, Any]) -> bool:
    for context in _candidate_contexts(event):
        for key in ("trigger", "webhookType", "action", "type"):
            marker = _normalize_text(context.get(key))
            if marker in _UPDATE_MARKERS:
                return True
    return False


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for value in _walk_values_for_keys(
        event,
        (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
            "updatedFrom",
            "previousValues",
        ),
    ):
        for field in _field_names(value):
            if _normalize_text(field) in _STATUS_FIELD_NAMES:
                return True
    return False


def _status_name(event: Mapping[str, Any]) -> str | None:
    explicit_status_keys = (
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
    status = _first_text_value(event, explicit_status_keys)
    if status:
        return status

    status = _first_text_value(event, ("status",))
    if status:
        return status

    for context in _candidate_contexts(event):
        for key in ("state", "workflowState", "workflow_state", "status"):
            nested_status = _text_from_named_value(context.get(key))
            if nested_status:
                return nested_status

    return None


def _first_text_value(event: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for context in _candidate_contexts(event):
        for key in keys:
            text = _text_from_named_value(context.get(key))
            if text and text.strip():
                return text
    return None


def _text_from_named_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "id", "identifier"):
            nested = value.get(key)
            if isinstance(nested, str):
                return nested
    return None


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
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
        add(data.get("triggerContext"))

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("data"))
        add(trigger_context.get("issue"))

    return contexts


def _walk_values_for_keys(value: Any, keys: Iterable[str]) -> Iterable[Any]:
    key_set = set(keys)
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if key in key_set:
                yield nested_value
            yield from _walk_values_for_keys(nested_value, key_set)
    elif isinstance(value, list):
        for nested_value in value:
            yield from _walk_values_for_keys(nested_value, key_set)


def _field_names(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        yield from (str(key) for key in value.keys())
    elif isinstance(value, Iterable):
        for item in value:
            if isinstance(item, str):
                yield item
            elif isinstance(item, Mapping):
                name = item.get("name") or item.get("field") or item.get("key")
                if isinstance(name, str):
                    yield name


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^a-zA-Z0-9]+", " ", spaced)
    return re.sub(r"\s+", " ", words).strip().lower()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
