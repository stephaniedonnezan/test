"""Build Linear issue title updates for Cursor research automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TITLE_PREFIX = f"{PREFIX}: "

_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
    "status",
)
_NAMED_STATUS_KEYS = ("state", "workflowState", "workflow_state", "status")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "id")
_TITLE_KEYS = ("title",)
_TRIGGER_KEYS = ("trigger", "webhookType", "webhook_type", "action", "type")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters To Research.

    The function is intentionally side-effect free so callers can decide how to
    apply the returned action to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_contexts(event)
    if not _is_status_change_event(event, contexts):
        return None

    new_status = _extract_status(contexts)
    if _normalize(new_status) != "to research":
        return None

    issue_id = _first_text(contexts, _ISSUE_ID_KEYS)
    title = _first_text(contexts, _TITLE_KEYS)
    if issue_id is None or title is None:
        return None

    clean_title = title.strip()
    if not clean_title or clean_title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}{clean_title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely payload locations, preferring issue-shaped objects."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    trigger_context = event.get("triggerContext") or event.get("trigger_context")
    data = event.get("data")
    issue = event.get("issue")

    add(trigger_context)
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("issue"))
        add(trigger_context.get("data"))
    if isinstance(data, Mapping):
        add(data.get("issue"))
    add(data)
    add(issue)
    add(event)

    return contexts


def _is_status_change_event(
    event: Mapping[str, Any],
    contexts: Iterable[Mapping[str, Any]],
) -> bool:
    trigger_values = {_normalize(value) for value in _trigger_values(contexts)}
    trigger_values.discard("")

    if any(value in {"status changed", "status change", "status"} for value in trigger_values):
        return True

    is_issue_update = any(
        value in {"update", "updated", "issue update", "issue updated", "updated issue"}
        for value in trigger_values
    )
    return is_issue_update and _has_status_updated_field(event)


def _trigger_values(contexts: Iterable[Mapping[str, Any]]) -> Iterable[Any]:
    for context in contexts:
        for key in _TRIGGER_KEYS:
            if key in context:
                yield context[key]


def _has_status_updated_field(event: Mapping[str, Any]) -> bool:
    for context in _walk_mappings(event):
        for key in _UPDATED_FIELD_KEYS:
            fields = context.get(key)
            if _contains_status_field(fields):
                return True

        updated_from = context.get("updatedFrom") or context.get("updated_from")
        if isinstance(updated_from, Mapping) and any(
            _is_status_field(field_name) for field_name in updated_from
        ):
            return True

    return False


def _contains_status_field(fields: Any) -> bool:
    if isinstance(fields, str):
        return _is_status_field(fields)
    if isinstance(fields, Mapping):
        return any(_is_status_field(field_name) for field_name in fields)
    if isinstance(fields, Iterable):
        return any(_is_status_field(field) for field in fields)
    return False


def _is_status_field(field: Any) -> bool:
    normalized = _normalize(field)
    return normalized in {
        "status",
        "status id",
        "state",
        "state id",
        "workflow state",
        "workflow state id",
    }


def _extract_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    context_list = list(contexts)

    for key in _EXPLICIT_STATUS_KEYS:
        value = _first_text(context_list, (key,))
        if value is not None:
            return value

    for context in context_list:
        for key in _NAMED_STATUS_KEYS:
            value = context.get(key)
            if isinstance(value, Mapping):
                name = _first_text((value,), ("name", "title"))
                if name is not None:
                    return name

    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested in value.values():
            yield from _walk_mappings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_mappings(nested)


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    with_camel_spacing = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    with_word_separators = re.sub(r"[^A-Za-z0-9]+", " ", with_camel_spacing)
    return " ".join(with_word_separators.lower().split())


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    json.dump(result, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
