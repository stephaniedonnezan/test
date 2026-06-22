"""Build Linear issue title updates for Cursor research automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {
    "status",
    "state",
    "state id",
    "state name",
    "workflow state",
    "workflow state id",
    "workflow state name",
}
DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "state changed",
    "workflow state changed",
}
GENERIC_UPDATE_TRIGGERS = {
    "issue updated",
    "updated issue",
    "issue update",
    "update issue",
    "updated",
    "update",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to "to research".

    The automation payload can arrive as a flat Cursor trigger context, a nested
    ``triggerContext`` object, or a Linear-style ``data.issue`` webhook. This
    function accepts those common shapes and returns a small action object that a
    caller can use to update the issue title.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _status_value(contexts)
    if _normalize_label(status) != TARGET_STATUS:
        return None

    title = _string_value(_first_value(contexts, ("title", "name")))
    issue_id = _string_value(
        _first_value(
            contexts,
            (
                "issueId",
                "issue_id",
                "identifier",
                "key",
                "id",
            ),
        )
    )
    if not title or not issue_id:
        return None

    title = title.strip()
    issue_id = issue_id.strip()
    if not title or not issue_id or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    trigger_context = _mapping_value(event.get("triggerContext"))
    data = _mapping_value(event.get("data"))
    event_issue = _mapping_value(event.get("issue"))
    data_issue = _mapping_value(data.get("issue")) if data else None
    trigger_issue = (
        _mapping_value(trigger_context.get("issue")) if trigger_context else None
    )

    for candidate in (
        trigger_issue,
        data_issue,
        event_issue,
        trigger_context,
        data,
        event,
    ):
        if candidate:
            contexts.append(candidate)

    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = []
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            value = _string_value(context.get(key))
            if value:
                trigger_values.append(_normalize_label(value))

    if any(value in DIRECT_STATUS_TRIGGERS for value in trigger_values):
        return True

    if any(value in GENERIC_UPDATE_TRIGGERS for value in trigger_values):
        return _changed_fields_include_status(contexts)

    return _first_value(
        contexts,
        (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "newWorkflowState",
            "new_workflow_state",
        ),
    ) is not None


def _changed_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
            "changed",
        ):
            if _field_collection_mentions_status(context.get(key)):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            if any(_normalize_label(str(field)) in STATUS_FIELD_NAMES for field in changes):
                return True
        elif _field_collection_mentions_status(changes):
            return True

        previous_values = context.get("previousValues") or context.get("previous_values")
        if isinstance(previous_values, Mapping) and any(
            _normalize_label(str(field)) in STATUS_FIELD_NAMES
            for field in previous_values
        ):
            return True

    return False


def _field_collection_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_label(value) in STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        return any(
            _normalize_label(str(key)) in STATUS_FIELD_NAMES for key in value.keys()
        )
    if isinstance(value, list | tuple | set):
        return any(_field_collection_mentions_status(item) for item in value)
    return False


def _status_value(contexts: list[Mapping[str, Any]]) -> Any:
    explicit = _first_value(
        contexts,
        (
            "newStatus",
            "new_status",
            "newStatusName",
            "new_status_name",
            "newState",
            "new_state",
            "newStateName",
            "new_state_name",
            "newWorkflowState",
            "new_workflow_state",
            "newWorkflowStateName",
            "new_workflow_state_name",
        ),
    )
    if explicit is not None:
        return _named_value(explicit)

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _first_value(contexts, (key,))
        if value is not None:
            return _named_value(value)

    return None


def _first_value(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> Any:
    normalized_keys = {_normalize_key(key) for key in keys}
    for context in contexts:
        for key, value in context.items():
            if _normalize_key(str(key)) in normalized_keys and value is not None:
                return value
    return None


def _named_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if value.get(key) is not None:
                return value[key]
    return value


def _mapping_value(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_key(value: str) -> str:
    return _normalize_label(value).replace(" ", "")


def _normalize_label(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    words = re.sub(r"[^A-Za-z0-9]+", " ", words)
    return re.sub(r"\s+", " ", words).strip().casefold()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
