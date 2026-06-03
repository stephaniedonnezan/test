"""Build title updates for Linear issues moved into research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


RESEARCH_TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_CHANGE_TRIGGERS = {"status changed", "status change"}
_UPDATE_TRIGGERS = {"update", "updated", "issue updated", "updated issue"}
_STATUS_FIELD_NAMES = {
    "status",
    "status id",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
    "workflow status",
    "workflow status id",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action for issues newly moved to research.

    The automation payloads used by Cursor and Linear can be either flat
    trigger contexts or nested webhook payloads. This function keeps the
    integration point small: callers pass the decoded JSON event and receive
    either the update action to perform or ``None`` when no update is needed.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _new_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    title = _text_from_contexts(contexts, ("title", "name"))
    issue_id = _text_from_contexts(
        contexts,
        ("id", "issueId", "issue_id", "identifier"),
    )
    if not title or not issue_id:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{RESEARCH_TITLE_PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload dictionaries ordered from most to least authoritative."""

    contexts: list[Mapping[str, Any]] = []

    def append(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")
    data_issue = data.get("issue") if isinstance(data, Mapping) else None

    append(trigger_context)
    append(event)
    append(data)
    append(issue)
    append(data_issue)

    return contexts


def _is_status_change_event(contexts: Sequence[Mapping[str, Any]]) -> bool:
    trigger_values = []
    for context in contexts:
        trigger_values.extend(
            _string_values(
                context,
                (
                    "trigger",
                    "triggerType",
                    "webhookType",
                    "webhook_type",
                    "action",
                    "type",
                ),
            )
        )

    normalized = {_normalize(value) for value in trigger_values}
    if normalized & _STATUS_CHANGE_TRIGGERS:
        return True

    if normalized & _UPDATE_TRIGGERS:
        return _updated_status_fields(contexts)

    return False


def _updated_status_fields(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
        ):
            value = context.get(key)
            if _contains_status_field(value):
                return True

        updated_from = context.get("updatedFrom") or context.get("updated_from")
        if isinstance(updated_from, Mapping) and _contains_status_field(
            list(updated_from.keys())
        ):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        normalized = _normalize(value)
        return normalized in _STATUS_FIELD_NAMES or normalized.endswith(" state")

    if isinstance(value, Mapping):
        candidates = list(value.keys()) + [
            item
            for item in value.values()
            if isinstance(item, str)
        ]
        return _contains_status_field(candidates)

    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        for item in value:
            if isinstance(item, Mapping):
                if _contains_status_field(item):
                    return True
            elif _contains_status_field(item):
                return True

    return False


def _new_status(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
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
    for context in contexts:
        value = _text_value(context, explicit_keys)
        if value:
            return value
    return None


def _text_from_contexts(
    contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]
) -> str | None:
    for context in contexts:
        value = _text_value(context, keys)
        if value:
            return value
    return None


def _text_value(context: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        if key not in context:
            continue

        value = context[key]
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped

        if isinstance(value, Mapping):
            nested = _text_value(value, ("name", "title", "id", "identifier"))
            if nested:
                return nested

    return None


def _string_values(context: Mapping[str, Any], keys: Sequence[str]) -> list[str]:
    values: list[str] = []
    for key in keys:
        value = context.get(key)
        if isinstance(value, str):
            values.append(value)
    return values


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    separated = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return " ".join(separated.casefold().split())


def _has_research_prefix(title: str) -> bool:
    return re.match(r"^\s*cursor researching\b", title, flags=re.IGNORECASE) is not None


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
