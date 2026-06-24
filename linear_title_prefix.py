"""Build title update actions for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
TITLE_SEPARATOR = ": "
STATUS_FIELDS = frozenset({"status", "state", "workflowstate", "workflow_status"})
DIRECT_STATUS_TRIGGERS = frozenset(
    {
        "statuschanged",
        "statuschange",
        "status_changed",
        "status-change",
        "workflowstatechanged",
        "workflow_state_changed",
        "statechanged",
        "state_changed",
    }
)
ISSUE_UPDATE_TRIGGERS = frozenset(
    {
        "update",
        "updated",
        "issueupdate",
        "issueupdated",
        "updatedissue",
    }
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action for Linear research status changes."""
    if not isinstance(event, Mapping):
        return None

    contexts = list(_candidate_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    status = _first_text(contexts, _status_candidates)
    if _normalize_status(status) != _normalize_status(TARGET_STATUS):
        return None

    issue_id = _first_text(contexts, _issue_id_candidates)
    title = _first_text(contexts, _title_candidates)
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if _has_title_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}{TITLE_SEPARATOR}{clean_title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = [event]
    for key in ("automation_trigger_info", "triggerInfo", "trigger_info"):
        _append_mapping(contexts, event.get(key))

    for context in list(contexts):
        for key in ("triggerContext", "trigger_context", "data", "payload", "issue"):
            _append_mapping(contexts, context.get(key))

    for context in list(contexts):
        data = context.get("data")
        if isinstance(data, Mapping):
            _append_mapping(contexts, data.get("issue"))

    return contexts


def _append_mapping(contexts: list[Mapping[str, Any]], value: object) -> None:
    if isinstance(value, Mapping) and value not in contexts:
        contexts.append(value)


def _is_status_change_event(contexts: Sequence[Mapping[str, Any]]) -> bool:
    trigger_values = _trigger_values(contexts)
    normalized_triggers = {_normalize_token(value) for value in trigger_values}

    if normalized_triggers & {_normalize_token(value) for value in DIRECT_STATUS_TRIGGERS}:
        return True

    if normalized_triggers & {_normalize_token(value) for value in ISSUE_UPDATE_TRIGGERS}:
        return _updated_fields_include_status(contexts)

    return False


def _trigger_values(contexts: Sequence[Mapping[str, Any]]) -> list[str]:
    values: list[str] = []
    for context in contexts:
        for key in ("trigger", "webhookType", "webhook_type", "action", "type", "event"):
            value = context.get(key)
            if isinstance(value, str):
                values.append(value)
    return values


def _updated_fields_include_status(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _field_names_include_status(context.get(key)):
                return True
        changes = context.get("changes")
        if isinstance(changes, Mapping):
            if any(_is_status_field(name) for name in changes):
                return True
        elif isinstance(changes, Sequence) and not isinstance(changes, (str, bytes)):
            if _field_names_include_status(changes):
                return True
    return False


def _field_names_include_status(value: object) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        return any(_is_status_field(name) for name in value)
    if isinstance(value, Sequence):
        return any(_field_names_include_status(item) for item in value)
    return False


def _is_status_field(value: object) -> bool:
    return isinstance(value, str) and _normalize_token(value) in {
        _normalize_token(field) for field in STATUS_FIELDS
    }


def _first_text(
    contexts: Sequence[Mapping[str, Any]],
    extractor: Any,
) -> str | None:
    for context in contexts:
        for value in extractor(context):
            text = _as_text(value)
            if text:
                return text
    return None


def _status_candidates(context: Mapping[str, Any]) -> Sequence[object]:
    candidates: list[object] = []
    for key in (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "status",
        "state",
        "workflowState",
        "workflow_state",
    ):
        value = context.get(key)
        candidates.append(value)
        if isinstance(value, Mapping):
            candidates.extend(value.get(name) for name in ("name", "title", "label"))

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _is_status_field(key):
                candidates.extend(_change_value_candidates(value))
    return candidates


def _change_value_candidates(value: object) -> Sequence[object]:
    if isinstance(value, Mapping):
        return [
            value.get("to"),
            value.get("new"),
            value.get("newValue"),
            value.get("after"),
            value.get("name"),
        ]
    return [value]


def _issue_id_candidates(context: Mapping[str, Any]) -> Sequence[object]:
    return [
        context.get("issueId"),
        context.get("issue_id"),
        context.get("identifier"),
        context.get("key"),
        context.get("id"),
    ]


def _title_candidates(context: Mapping[str, Any]) -> Sequence[object]:
    return [
        context.get("title"),
        context.get("name"),
        context.get("issueTitle"),
        context.get("issue_title"),
    ]


def _as_text(value: object) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    return " ".join(_split_words(value))


def _normalize_token(value: str) -> str:
    return "".join(_split_words(value))


def _split_words(value: str) -> list[str]:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.findall(r"[a-z0-9]+", spaced.lower())


def _has_title_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    """Read a JSON event from stdin and print the resulting action, if any."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
