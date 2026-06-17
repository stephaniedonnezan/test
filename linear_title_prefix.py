"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TARGET_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"

DIRECT_STATUS_TRIGGERS = {
    "statuschanged",
    "statechanged",
    "workflowstatechanged",
    "workflowstatuschanged",
}

GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}

STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
    "workflowstatus",
    "workflowstatusid",
}

TRIGGER_KEYS = ("trigger", "action", "type", "webhookType", "webhook_type")
NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "status",
    "state",
    "stateName",
    "state_name",
    "workflowState",
    "workflow_state",
    "workflowStateName",
    "workflow_state_name",
    "workflowStatus",
    "workflow_status",
)
ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    The automation payloads used by Cursor and Linear vary: some expose a flat
    trigger context, while others nest issue data under ``triggerContext`` or
    ``data``. This function accepts those common shapes and returns ``None`` for
    unrelated events.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue = _issue_context(contexts)
    issue_id = _first_text(issue, ISSUE_ID_KEYS)
    title = _first_text(issue, ("title",))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": clean_title if _has_research_prefix(clean_title) else f"{TITLE_PREFIX}: {clean_title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = [event]

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        contexts.append(data)
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            contexts.append(issue)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        contexts.append(issue)

    # Preserve order while removing repeated mapping objects.
    unique_contexts: list[Mapping[str, Any]] = []
    seen_ids: set[int] = set()
    for context in contexts:
        context_id = id(context)
        if context_id not in seen_ids:
            unique_contexts.append(context)
            seen_ids.add(context_id)
    return unique_contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    contexts = list(contexts)
    for context in contexts:
        for key in TRIGGER_KEYS:
            trigger = context.get(key)
            if _normalize_compact(trigger) in DIRECT_STATUS_TRIGGERS:
                return True

    if any(
        _normalize_compact(context.get(key)) in GENERIC_UPDATE_TRIGGERS
        for context in contexts
        for key in TRIGGER_KEYS
    ):
        return any(_changed_fields_include_status(context) for context in contexts)

    return False


def _changed_fields_include_status(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        value = context.get(key)
        if isinstance(value, str) and _is_status_field(value):
            return True
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
            if any(_is_status_field(field) for field in value):
                return True

    changes = context.get("changes") or context.get("changed") or context.get("updatedFrom")
    if isinstance(changes, Mapping):
        return any(_is_status_field(field) for field in changes)
    if isinstance(changes, Iterable) and not isinstance(changes, (str, bytes, Mapping)):
        return any(_change_mentions_status(change) for change in changes)

    return False


def _change_mentions_status(change: Any) -> bool:
    if isinstance(change, str):
        return _is_status_field(change)
    if isinstance(change, Mapping):
        field = (
            change.get("field")
            or change.get("fieldName")
            or change.get("name")
            or change.get("property")
            or change.get("key")
        )
        return _is_status_field(field) or any(_is_status_field(key) for key in change)
    return False


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    contexts = list(contexts)
    for context in contexts:
        status = _first_text(context, NEW_STATUS_KEYS)
        if status:
            return status

    for context in contexts:
        changes = context.get("changes") or context.get("changed")
        status = _new_status_from_changes(changes)
        if status:
            return status

    return None


def _new_status_from_changes(changes: Any) -> str | None:
    if isinstance(changes, Mapping):
        for field, value in changes.items():
            if not _is_status_field(field):
                continue
            status = _status_name(value)
            if status:
                return status
    elif isinstance(changes, Iterable) and not isinstance(changes, (str, bytes, Mapping)):
        for change in changes:
            if not isinstance(change, Mapping):
                continue
            field = (
                change.get("field")
                or change.get("fieldName")
                or change.get("name")
                or change.get("property")
                or change.get("key")
            )
            if not _is_status_field(field):
                continue
            status = _status_name(
                change.get("to")
                or change.get("toValue")
                or change.get("newValue")
                or change.get("new")
                or change.get("value")
            )
            if status:
                return status
    return None


def _issue_context(contexts: Iterable[Mapping[str, Any]]) -> Mapping[str, Any]:
    merged: dict[str, Any] = {}
    for context in contexts:
        merged.update(context)
    return merged


def _first_text(context: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = _status_name(context.get(key))
        if value:
            return value
    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "displayName"):
            text = _status_name(value.get(key))
            if text:
                return text
    return None


def _is_status_field(value: Any) -> bool:
    return _normalize_compact(value) in STATUS_FIELD_NAMES


def _normalize_words(value: Any) -> str | None:
    text = _status_name(value)
    if not text:
        return None
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()


def _normalize_compact(value: Any) -> str | None:
    words = _normalize_words(value)
    if not words:
        return None
    return words.replace(" ", "")


def _has_research_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(TITLE_PREFIX)}\b", title, flags=re.IGNORECASE) is not None


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is None:
        return 0
    print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
