"""Build Linear issue title updates for Cursor research-status automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
PREFIXED_TITLE = f"{PREFIX}: {{title}}"
RESEARCH_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "workflowstate",
}

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}

_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return the title update action for Linear issues entering research.

    The function is intentionally side-effect free so the automation runtime can
    decide how to apply the returned update.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if not any(_normalize_words(status) == RESEARCH_STATUS for status in _status_candidates(event)):
        return None

    issue_id = _first_text_value(_issue_contexts(event), ("issueId", "issue_id", "identifier", "key", "id", "uuid"))
    title = _first_text_value(_issue_contexts(event), ("title", "name"))

    if not issue_id or not title:
        return None

    if title.lstrip().lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": PREFIXED_TITLE.format(title=title),
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = [
        value
        for context in _event_contexts(event)
        for key, value in context.items()
        if key in {"trigger", "webhookType", "action", "type"}
    ]

    normalized_values = {_normalize_words(value) for value in trigger_values}
    if normalized_values & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    if normalized_values & _GENERIC_UPDATE_EVENTS:
        return _updated_fields_include_status(event)

    return False


def _updated_fields_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized_key = _normalize_words(key)

            if normalized_key in {"updated fields", "changed fields"}:
                if _field_collection_includes_status(item):
                    return True

            if normalized_key in {"changes", "changed", "change"}:
                if _changes_include_status(item):
                    return True

            if _updated_fields_include_status(item):
                return True

    if isinstance(value, list):
        return any(_updated_fields_include_status(item) for item in value)

    return False


def _field_collection_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        return any(_is_status_field(key) or _field_collection_includes_status(item) for key, item in value.items())

    if isinstance(value, Iterable):
        return any(_field_collection_includes_status(item) for item in value)

    return False


def _changes_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        if _is_status_field(value.get("field")) or _is_status_field(value.get("name")):
            return True

        return any(_is_status_field(key) or _changes_include_status(item) for key, item in value.items())

    if isinstance(value, list):
        return any(_changes_include_status(item) for item in value)

    return False


def _status_candidates(event: Mapping[str, Any]) -> list[str]:
    candidates: list[str] = []

    for context in _event_contexts(event):
        for key in ("newStatus", "new_status", "toStatus", "to_status", "newState", "new_state"):
            candidates.extend(_text_candidates(context.get(key)))

    for changes in _values_for_keys(event, {"changes", "changed", "change"}):
        candidates.extend(_status_candidates_from_changes(changes))

    for context in _issue_contexts(event):
        for key in ("status", "state", "workflowState", "workflow_state"):
            candidates.extend(_text_candidates(context.get(key)))

    return [candidate for candidate in candidates if candidate]


def _status_candidates_from_changes(value: Any) -> list[str]:
    candidates: list[str] = []

    if isinstance(value, Mapping):
        field_name = value.get("field") or value.get("name")
        if _is_status_field(field_name):
            for key in ("newValue", "new_value", "to", "after", "new", "value", "name"):
                candidates.extend(_text_candidates(value.get(key)))

        for key, item in value.items():
            if _is_status_field(key):
                candidates.extend(_new_value_candidates(item))
            else:
                candidates.extend(_status_candidates_from_changes(item))

    elif isinstance(value, list):
        for item in value:
            candidates.extend(_status_candidates_from_changes(item))

    return candidates


def _new_value_candidates(value: Any) -> list[str]:
    if isinstance(value, Mapping):
        candidates: list[str] = []
        for key in ("newValue", "new_value", "to", "after", "new", "value", "name"):
            candidates.extend(_text_candidates(value.get(key)))
        return candidates or _text_candidates(value)

    return _text_candidates(value)


def _text_candidates(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, Mapping):
        candidates: list[str] = []
        for key in ("name", "title", "displayName", "display_name", "value"):
            candidates.extend(_text_candidates(value.get(key)))
        return candidates

    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []

    return [str(value).strip()] if str(value).strip() else []


def _first_text_value(contexts: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            candidates = _text_candidates(context.get(key))
            if candidates:
                return candidates[0]
    return None


def _event_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    _append_mapping(contexts, event.get("automation_trigger_info"))
    _append_mapping(contexts, _nested_mapping(event.get("automation_trigger_info"), "triggerContext"))
    _append_mapping(contexts, event.get("triggerContext"))
    _append_mapping(contexts, event)
    _append_mapping(contexts, event.get("data"))
    _append_mapping(contexts, _nested_mapping(event.get("data"), "issue"))
    _append_mapping(contexts, event.get("issue"))
    return _dedupe_mappings(contexts)


def _issue_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    _append_mapping(contexts, _nested_mapping(event.get("automation_trigger_info"), "triggerContext"))
    _append_mapping(contexts, event.get("triggerContext"))
    _append_mapping(contexts, _nested_mapping(event.get("data"), "issue"))
    _append_mapping(contexts, event.get("issue"))
    _append_mapping(contexts, event.get("data"))
    _append_mapping(contexts, event)
    return _dedupe_mappings(contexts)


def _nested_mapping(value: Any, key: str) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping) and isinstance(value.get(key), Mapping):
        return value[key]
    return None


def _append_mapping(contexts: list[Mapping[str, Any]], value: Any) -> None:
    if isinstance(value, Mapping):
        contexts.append(value)


def _dedupe_mappings(contexts: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    deduped: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    for context in contexts:
        marker = id(context)
        if marker not in seen:
            deduped.append(context)
            seen.add(marker)

    return deduped


def _values_for_keys(value: Any, wanted_keys: set[str]) -> list[Any]:
    matches: list[Any] = []

    if isinstance(value, Mapping):
        for key, item in value.items():
            if _normalize_words(key) in wanted_keys:
                matches.append(item)
            matches.extend(_values_for_keys(item, wanted_keys))

    elif isinstance(value, list):
        for item in value:
            matches.extend(_values_for_keys(item, wanted_keys))

    return matches


def _is_status_field(value: Any) -> bool:
    return _normalize_words(value) in _STATUS_FIELD_NAMES


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""

    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", str(value).strip())
    words = re.sub(r"[_\-.]+", " ", words)
    words = re.sub(r"\s+", " ", words)
    return words.lower()


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print(f"Invalid JSON: {error}", file=sys.stderr)
        return 1

    result = build_issue_title_update(event)
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
