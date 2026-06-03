"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newStatusName",
    "new_status_name",
    "status",
    "statusName",
    "status_name",
)
_NESTED_STATUS_KEYS = ("state", "workflowState", "workflow_state")
_ID_KEYS = ("id", "issueId", "issue_id", "identifier")
_TITLE_KEYS = ("title", "name")
_STATUS_FIELD_NAMES = {
    "status",
    "status id",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title update action when a status changes to research."""

    if not isinstance(event, Mapping):
        return None

    contexts = list(_iter_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    status = _extract_status(contexts)
    if _normalize_label(status) != TARGET_STATUS:
        return None

    issue_id = _extract_string(contexts, _ID_KEYS)
    title = _extract_string(contexts, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    if _normalize_label(title).startswith(_normalize_label(PREFIX)):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _iter_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely payload containers from outermost metadata to issue details."""

    yield event
    for key in ("triggerContext", "payload", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            yield from _iter_contexts(value)


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "event", "eventType", "webhookType", "type"):
            if _normalize_label(context.get(key)) in {"status changed", "status change"}:
                return True

    if not _is_issue_update(contexts):
        return False

    return any(_updated_fields_include_status(context) for context in contexts)


def _is_issue_update(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("action", "trigger", "event", "eventType", "type"):
            value = _normalize_label(context.get(key))
            if value in {"update", "updated", "issue update", "issue updated", "updated issue"}:
                return True
    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    for key in (
        "updatedFields",
        "updated_fields",
        "changedFields",
        "changed_fields",
        "updatedFrom",
        "updated_from",
        "changes",
    ):
        value = context.get(key)
        if _field_names(value) & _STATUS_FIELD_NAMES:
            return True
    return False


def _field_names(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        return {_normalize_label(key) for key in value.keys()}
    if isinstance(value, str):
        return {_normalize_label(value)}
    if isinstance(value, Iterable):
        return {_normalize_label(item) for item in value}
    return set()


def _extract_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for key in _DIRECT_STATUS_KEYS:
        value = _extract_string(contexts, (key,))
        if value:
            return value

    for context in contexts:
        for key in _NESTED_STATUS_KEYS:
            value = context.get(key)
            if isinstance(value, Mapping):
                status = _extract_string([value], ("name", "title"))
                if status:
                    return status
            elif isinstance(value, str):
                return value.strip()

    return None


def _extract_string(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str):
                value = value.strip()
                if value:
                    return value
    return None


def _normalize_label(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    with_word_boundaries = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    words_only = re.sub(r"[^A-Za-z0-9]+", " ", with_word_boundaries)
    return re.sub(r"\s+", " ", words_only).strip().casefold()


def main() -> int:
    """Read a JSON event from stdin and print the resulting action as JSON."""

    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is None:
        return 0

    print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
