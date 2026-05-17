"""Build title update actions for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue moves to research.

    The automation platform can pass either a flat trigger context or a nested
    Linear webhook payload. This function keeps the output side-effect free so
    the caller can decide how to apply the returned action.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _find_new_status(event)
    if _normalize_status(new_status) != TARGET_STATUS:
        return None

    issue = _find_issue_details(event)
    if issue is None:
        return None

    issue_id, title = issue
    stripped_title = title.strip()
    if _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_words = {_normalize_event_value(value) for value in _event_values(event)}
    event_words.discard("")

    if event_words & {"statuschanged", "statuschange", "statechanged", "workflowstatechanged"}:
        return True

    updated_fields = {_normalize_field_name(value) for value in _updated_field_values(event)}
    if updated_fields & {"status", "state", "workflowstate"}:
        return True

    return False


def _find_new_status(event: Mapping[str, Any]) -> Any:
    explicit_status_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "toStatus",
        "to_status",
    )
    for context in _candidate_contexts(event):
        value = _first_present(context, explicit_status_keys)
        if value is not None:
            return _status_name(value)

    for context in _candidate_contexts(event):
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = context.get(key)
            if value is not None:
                return _status_name(value)

    return None


def _find_issue_details(event: Mapping[str, Any]) -> tuple[str, str] | None:
    for context in _candidate_contexts(event):
        title = context.get("title")
        if not isinstance(title, str) or not title.strip():
            continue

        issue_id = _first_present(context, ("issueId", "issue_id", "identifier", "id"))
        if isinstance(issue_id, str) and issue_id.strip():
            return issue_id, title

    return None


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    trigger_context = event.get("triggerContext")
    add(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data)

    add(event.get("issue"))
    add(event)

    for context in list(contexts):
        add(context.get("issue"))

    return contexts


def _event_values(event: Mapping[str, Any]) -> Iterable[Any]:
    event_keys = {
        "trigger",
        "webhookType",
        "webhook_type",
        "action",
        "type",
        "eventType",
        "event_type",
    }
    for context in _all_mappings(event):
        for key in event_keys:
            if key in context:
                yield context[key]


def _updated_field_values(event: Mapping[str, Any]) -> Iterable[Any]:
    for context in _all_mappings(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if key not in context:
                continue

            value = context[key]
            if isinstance(value, str):
                yield value
            elif isinstance(value, Mapping):
                yield from value.keys()
            elif isinstance(value, Iterable):
                for item in value:
                    yield item


def _all_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _all_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _all_mappings(child)


def _first_present(context: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = context.get(key)
        if value is not None:
            return value
    return None


def _status_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if nested is not None:
                return nested
    return value


def _normalize_status(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _split_camel_case(value).replace("_", " ").replace("-", " ").strip().lower()


def _normalize_event_value(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", _split_camel_case(value).lower())


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", _split_camel_case(value).lower())


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
