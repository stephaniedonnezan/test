"""Build Linear issue title updates for issues entering To Research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflow_state",
    "stateid",
    "state_id",
    "statusid",
    "status_id",
    "workflowstateid",
    "workflow_state_id",
}

_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}

_ISSUE_UPDATE_TRIGGERS = {
    "issue updated",
    "issue update",
    "updated issue",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to To Research.

    The Cursor automation trigger can provide either a flattened
    ``triggerContext`` payload or a nested Linear webhook-like payload. This
    function accepts both shapes and returns a small action object for the
    caller to apply to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _ordered_contexts(event)
    if not _is_status_change_event(event, contexts):
        return None

    status = _extract_new_status(contexts)
    if _normalize_label(status) != TARGET_STATUS:
        return None

    title = _extract_text(contexts, ("title", "name"))
    issue_id = _extract_text(contexts, ("id", "issueId", "issue_id", "identifier"))
    if not title or not issue_id:
        return None

    clean_title = title.strip()
    if not clean_title or clean_title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _ordered_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    for path in (
        ("triggerContext",),
        ("trigger_context",),
        ("data", "issue"),
        ("issue",),
        ("data",),
    ):
        value = _get_path(event, path)
        if isinstance(value, Mapping):
            contexts.append(value)

    contexts.append(event)
    return _dedupe_mappings(contexts)


def _get_path(mapping: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = mapping
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _dedupe_mappings(mappings: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    seen: set[int] = set()
    unique: list[Mapping[str, Any]] = []
    for mapping in mappings:
        marker = id(mapping)
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(mapping)
    return unique


def _is_status_change_event(
    event: Mapping[str, Any], contexts: Iterable[Mapping[str, Any]]
) -> bool:
    trigger_values = [
        _normalize_label(value)
        for context in contexts
        for key in (
            "trigger",
            "webhookType",
            "webhook_type",
            "action",
            "type",
            "eventType",
            "event_type",
        )
        for value in [_coerce_name(context.get(key))]
        if value
    ]

    if any(value in _STATUS_CHANGE_TRIGGERS for value in trigger_values):
        return True

    if any(value in _ISSUE_UPDATE_TRIGGERS for value in trigger_values):
        return _updated_fields_include_status(event)

    return _updated_fields_include_status(event) and bool(_extract_new_status(contexts))


def _updated_fields_include_status(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False

    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if _field_collection_mentions_status(value.get(key)):
            return True

    for key in ("updatedFrom", "updated_from", "changes", "changed"):
        changed_value = value.get(key)
        if _field_collection_mentions_status(changed_value):
            return True
        if isinstance(changed_value, Mapping) and any(
            _is_status_field_name(field_name) for field_name in changed_value
        ):
            return True

    return any(
        _updated_fields_include_status(child)
        for child in value.values()
        if isinstance(child, Mapping)
    )


def _field_collection_mentions_status(value: Any) -> bool:
    if value is None:
        return False

    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Mapping):
        name = value.get("name") or value.get("field") or value.get("key")
        if name and _is_status_field_name(str(name)):
            return True
        return any(_field_collection_mentions_status(item) for item in value.values())

    if isinstance(value, Iterable):
        return any(_field_collection_mentions_status(item) for item in value)

    return False


def _is_status_field_name(value: str) -> bool:
    return _normalize_key(value) in _STATUS_FIELD_NAMES


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
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
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    for keys in (explicit_keys, fallback_keys):
        value = _extract_text(contexts, keys)
        if value:
            return value
    return None


def _extract_text(contexts: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _coerce_name(context.get(key))
            if value and value.strip():
                return value.strip()
    return None


def _coerce_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "identifier", "id"):
            nested = value.get(key)
            if isinstance(nested, str):
                return nested

    return None


def _normalize_label(value: str | None) -> str:
    if not value:
        return ""

    with_spaces = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    with_spaces = re.sub(r"[_\-\s]+", " ", with_spaces)
    return with_spaces.strip().lower()


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def main() -> int:
    payload = json.load(sys.stdin)
    result = build_issue_title_update(payload)
    if result is not None:
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
