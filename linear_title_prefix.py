"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflowstatus",
}
_EXPLICIT_NEW_STATUS_KEYS = {
    "newstatus",
    "newstate",
    "newworkflowstate",
    "targetstatus",
    "targetstate",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action when the event enters research."""

    if not isinstance(event, Mapping):
        return None

    contexts = list(_mapping_contexts(event))
    if not _is_status_change_event(event, contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(contexts)
    title = _extract_title(contexts)
    if issue_id is None or title is None:
        return None

    title = title.strip()
    if not title or title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _mapping_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely metadata and issue objects from Cursor and Linear payloads."""

    seen: set[int] = set()

    def walk(value: Any) -> Iterable[Mapping[str, Any]]:
        if not isinstance(value, Mapping):
            return

        object_id = id(value)
        if object_id in seen:
            return
        seen.add(object_id)
        yield value

        for key in ("triggerContext", "data", "issue", "node", "object"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                yield from walk(nested)

    yield from walk(event)


def _is_status_change_event(
    event: Mapping[str, Any], contexts: Iterable[Mapping[str, Any]]
) -> bool:
    event_names = []
    for context in contexts:
        for key in ("trigger", "action", "type", "webhookType", "event", "eventType", "kind"):
            value = context.get(key)
            if isinstance(value, str):
                event_names.append(value)

    if any(_is_direct_status_change_name(name) for name in event_names):
        return True

    has_generic_update_name = any(
        _normalize_words(name) in {"update", "updated", "issue update", "issue updated", "updated issue"}
        for name in event_names
    )
    has_status_marker = _has_status_change_marker(event)

    if has_generic_update_name:
        return has_status_marker

    return has_status_marker and not event_names


def _is_direct_status_change_name(value: str) -> bool:
    words = _normalize_words(value)
    tokens = set(words.split())
    return bool(
        words in {
            "status changed",
            "status change",
            "state changed",
            "state change",
            "workflow state changed",
            "workflow status changed",
        }
        or ("status" in tokens and {"change", "changed"} & tokens)
        or ("state" in tokens and {"change", "changed"} & tokens)
    )


def _has_status_change_marker(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            key_name = _normalize_key(key)
            if key_name in _EXPLICIT_NEW_STATUS_KEYS:
                return True
            if key_name in {"updatedfields", "changedfields"} and _contains_status_field(nested_value):
                return True
            if key_name in {"changes", "updatedfrom", "previousvalues", "changed"}:
                if _mapping_has_status_key(nested_value):
                    return True
            if _has_status_change_marker(nested_value):
                return True
    elif isinstance(value, list):
        return any(_has_status_change_marker(item) for item in value)

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_key(value) in _STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        return _mapping_has_status_key(value) or any(
            _contains_status_field(item) for item in value.values()
        )
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _mapping_has_status_key(value: Any) -> bool:
    return isinstance(value, Mapping) and any(
        _normalize_key(key) in _STATUS_FIELD_NAMES for key in value
    )


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    context_list = list(contexts)

    for context in context_list:
        value = _first_key_value(context, _EXPLICIT_NEW_STATUS_KEYS)
        if value is not None:
            return _string_value(value)

    for context in context_list:
        status = _status_from_change_mapping(context.get("changes"))
        if status is not None:
            return status
        status = _status_from_change_mapping(context.get("changed"))
        if status is not None:
            return status

    for context in context_list:
        value = _first_key_value(context, _STATUS_FIELD_NAMES)
        if value is not None:
            return _string_value(value)

    return None


def _status_from_change_mapping(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for key, nested_value in value.items():
        if _normalize_key(key) not in _STATUS_FIELD_NAMES:
            continue
        if isinstance(nested_value, Mapping):
            for target_key in ("to", "new", "after", "value", "name"):
                status = _string_value(nested_value.get(target_key))
                if status is not None:
                    return status
        status = _string_value(nested_value)
        if status is not None:
            return status

    return None


def _extract_issue_id(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    preferred_keys = ("issueId", "issue_id", "identifier", "key", "id")
    for key in preferred_keys:
        normalized = _normalize_key(key)
        for context in contexts:
            value = _first_key_value(context, {normalized})
            text = _string_value(value)
            if text:
                return text.strip()
    return None


def _extract_title(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        value = _first_key_value(context, {"title"})
        text = _string_value(value)
        if text is not None:
            return text
    return None


def _first_key_value(context: Mapping[str, Any], normalized_keys: set[str]) -> Any:
    for key, value in context.items():
        if _normalize_key(key) in normalized_keys:
            return value
    return None


def _string_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value"):
            nested = value.get(key)
            if isinstance(nested, str):
                return nested
    return str(value)


def _normalize_key(value: Any) -> str:
    return _normalize_words(value).replace(" ", "")


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""
    text = _CAMEL_CASE_BOUNDARY.sub(" ", str(value)).lower()
    return _NON_ALNUM.sub(" ", text).strip()


def main() -> int:
    payload = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(payload), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
