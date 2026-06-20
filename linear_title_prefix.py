"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type", "eventType")
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "toStatus",
    "to_status",
    "toState",
    "to_state",
    "status",
)
_FALLBACK_STATUS_KEYS = ("state", "workflowState", "workflow_state", "status")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title", "issueTitle", "issue_title")
_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters To Research."""

    if not isinstance(event, Mapping) or not _is_status_change_event(event):
        return None

    contexts = list(_candidate_contexts(event))
    if _normalize_words(_extract_status(contexts)) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(contexts, _ISSUE_ID_KEYS)
    title = _extract_first_text(contexts, _TITLE_KEYS)
    if issue_id is None or title is None:
        return None

    if title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = (
        _normalize_words(value)
        for mapping in _walk_mappings(event)
        for value in _values_for_keys(mapping, _TRIGGER_KEYS)
    )

    saw_update_event = False
    for trigger in trigger_values:
        if _is_status_change_trigger(trigger):
            return True
        if trigger in {"update", "updated", "issue updated", "updated issue"}:
            saw_update_event = True

    return saw_update_event and _updated_fields_include_status(event)


def _is_status_change_trigger(trigger: str) -> bool:
    if trigger in {"status changed", "status change", "state changed", "workflow state changed"}:
        return True
    words = set(trigger.split())
    return "status" in words and bool({"changed", "change"} & words)


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for mapping in _walk_mappings(event):
        for key, value in mapping.items():
            if _normalize_words(key) in {
                "updated fields",
                "changed fields",
                "changes",
                "updated field names",
            } and _field_collection_includes_status(value):
                return True
    return False


def _field_collection_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_words(value) in _STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        return any(
            _normalize_words(key) in _STATUS_FIELD_NAMES
            or _field_collection_includes_status(nested_value)
            for key, nested_value in value.items()
        )
    if isinstance(value, Iterable):
        return any(_field_collection_includes_status(item) for item in value)
    return False


def _candidate_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely issue contexts before broader wrapper payloads."""

    for path in (
        ("automation_trigger_info", "triggerContext"),
        ("automationTriggerInfo", "triggerContext"),
        ("triggerContext",),
        ("data", "issue"),
        ("payload", "issue"),
        ("issue",),
        ("data",),
        ("payload",),
    ):
        nested = _nested_mapping(event, path)
        if nested is not None:
            yield nested
    yield event


def _extract_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for keys in (_NEW_STATUS_KEYS, _FALLBACK_STATUS_KEYS):
        status = _extract_first_text(contexts, keys)
        if status is not None:
            return status
    return None


def _extract_first_text(contexts: list[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for value in _values_for_keys(context, keys):
            text = _coerce_text(value)
            if text is not None:
                return text
    return None


def _values_for_keys(mapping: Mapping[str, Any], keys: Iterable[str]) -> Iterable[Any]:
    wanted = {_normalize_key(key) for key in keys}
    for key, value in mapping.items():
        if _normalize_key(key) in wanted:
            yield value


def _nested_mapping(mapping: Mapping[str, Any], path: tuple[str, ...]) -> Mapping[str, Any] | None:
    current: Any = mapping
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = next(_values_for_keys(current, (key,)), None)
    return current if isinstance(current, Mapping) else None


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested in value.values():
            yield from _walk_mappings(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_mappings(item)


def _coerce_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "key", "id"):
            text = _extract_first_text([value], (key,))
            if text is not None:
                return text
        return None
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def _normalize_words(value: Any) -> str:
    if isinstance(value, Mapping):
        value = _coerce_text(value)
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
