"""Build Linear issue-title updates for the research status automation.

The automation runner can pass either a compact trigger context or a fuller
Linear webhook payload. This module keeps the decision pure and testable: it
returns the update the runner should apply, or ``None`` when no update is
needed.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_KEYS = ("trigger", "event", "eventType", "webhookType")
_UPDATE_EVENT_KEYS = ("action", "type")
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
)
_CURRENT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "id")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when an issue moves to "to research".

    The returned shape intentionally contains only data needed by a caller that
    performs side effects:

    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``
    """

    if not isinstance(event, Mapping):
        return None

    mappings = list(_iter_mappings(event))
    if not _is_status_change_event(mappings):
        return None

    if not _status_is_target(mappings):
        return None

    issue_id, title = _extract_issue_identity(mappings)
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if _already_prefixed(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _iter_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_mappings(child)


def _is_status_change_event(mappings: list[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        for key in _DIRECT_STATUS_CHANGE_KEYS:
            if _mentions_status_change(mapping.get(key)):
                return True

    return _is_update_event(mappings) and _updated_fields_include_status(mappings)


def _is_update_event(mappings: list[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        for key in _UPDATE_EVENT_KEYS:
            normalized = _normalize(mapping.get(key))
            if normalized in {"update", "updated", "issue update", "issue updated", "updated issue"}:
                return True
    return False


def _updated_fields_include_status(mappings: list[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        for key, value in mapping.items():
            normalized_key = _normalize(key)
            if normalized_key in {
                "updated fields",
                "changed fields",
                "fields",
                "changes",
                "updated from",
                "previous values",
            }:
                if _value_mentions_status_field(value):
                    return True
    return False


def _value_mentions_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_is_status_field(key) or _value_mentions_status_field(child) for key, child in value.items())
    if isinstance(value, list):
        return any(_value_mentions_status_field(child) for child in value)
    return _is_status_field(value)


def _is_status_field(value: Any) -> bool:
    normalized = _normalize(value)
    return normalized in {
        "status",
        "status id",
        "state",
        "state id",
        "workflow state",
        "workflow state id",
    }


def _status_is_target(mappings: list[Mapping[str, Any]]) -> bool:
    for key_group in (_EXPLICIT_STATUS_KEYS, _CURRENT_STATUS_KEYS):
        for status in _values_for_keys(mappings, key_group):
            if _normalize(_status_name(status)) == TARGET_STATUS:
                return True
    return False


def _values_for_keys(mappings: list[Mapping[str, Any]], keys: tuple[str, ...]) -> Iterable[Any]:
    wanted = {_normalize(key) for key in keys}
    for mapping in mappings:
        for key, value in mapping.items():
            if _normalize(key) in wanted:
                yield value


def _status_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if key in value:
                return value[key]
    return value


def _extract_issue_identity(mappings: list[Mapping[str, Any]]) -> tuple[str | None, str | None]:
    issue_like_mappings = sorted(
        mappings,
        key=lambda mapping: 0 if any(_normalize(key) == "title" for key in mapping) else 1,
    )

    title = _first_string_value(issue_like_mappings, ("title",))
    issue_id = _first_string_value(issue_like_mappings, _ISSUE_ID_KEYS)
    return issue_id, title


def _first_string_value(mappings: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    normalized_keys = [(key, _normalize(key)) for key in keys]
    for mapping in mappings:
        normalized_mapping = {_normalize(key): value for key, value in mapping.items()}
        for _, normalized_key in normalized_keys:
            value = normalized_mapping.get(normalized_key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _mentions_status_change(value: Any) -> bool:
    normalized = _normalize(value)
    words = set(normalized.split())
    return "status" in words and ("changed" in words or "change" in words)


def _already_prefixed(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    """Read a JSON event from stdin and print the update action, if any."""

    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
