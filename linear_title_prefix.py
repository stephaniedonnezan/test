"""Build title update actions for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_EVENT_FIELD_KEYS = {"action", "event", "eventtype", "trigger", "type", "webhooktype"}
_DIRECT_STATUS_CHANGE_EVENTS = {"state changed", "status changed", "workflow state changed"}
_GENERIC_UPDATE_EVENTS = {"issue update", "issue updated", "update", "updated", "updated issue"}
_STATUS_FIELD_KEYS = {
    "state",
    "status",
    "workflowstate",
}
_EXPLICIT_NEW_STATUS_KEYS = (
    "newstate",
    "newstatus",
    "newworkflowstate",
    "statusname",
    "targetstate",
    "targetstatus",
)
_CURRENT_STATUS_KEYS = (
    "state",
    "status",
    "workflowstate",
)
_HISTORICAL_KEYS = {
    "before",
    "old",
    "oldstatus",
    "previous",
    "previousstatus",
    "previousvalues",
    "updatedfrom",
}
_ISSUE_ID_KEYS = ("issueid", "identifier", "key", "id")
_TITLE_KEYS = ("title", "issuetitle")


def handle_issue_status_changed(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action for qualifying Linear status changes.

    The function is intentionally side-effect free so callers can wire the
    returned action into whatever Linear client is available in their runtime.
    """

    return build_issue_title_update(event)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Build a title update when an issue status changes to ``to research``."""

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize_words(_status_value(event)) != TARGET_STATUS:
        return None

    issue_id = _first_text_for_keys(event, _ISSUE_ID_KEYS)
    title = _first_text_for_keys(event, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{RESEARCH_TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_values = {
        _normalize_words(value)
        for mapping in _walk_mappings(event)
        for key, value in mapping.items()
        if _normalize_key(key) in _EVENT_FIELD_KEYS
    }

    if event_values & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    if event_values & _GENERIC_UPDATE_EVENTS:
        return _has_status_field_change(event)

    return _has_status_field_change(event)


def _has_status_field_change(event: Mapping[str, Any]) -> bool:
    for mapping in _walk_mappings(event):
        for key, value in mapping.items():
            normalized_key = _normalize_key(key)
            if normalized_key in {"updatedfields", "changedfields"}:
                if _iterable_mentions_status_field(value):
                    return True

            if normalized_key in {"changes", "updatedfrom", "previousvalues"}:
                if isinstance(value, Mapping) and any(
                    _is_status_field_key(changed_key) for changed_key in value
                ):
                    return True

            if normalized_key in {"oldstatus", "previousstatus"}:
                return True

    return False


def _status_value(event: Mapping[str, Any]) -> Any:
    searchable_mappings = list(_walk_mappings(event, skip_keys=_HISTORICAL_KEYS))

    for mapping in searchable_mappings:
        value = _value_for_keys(mapping, _EXPLICIT_NEW_STATUS_KEYS)
        if value is not None:
            return value

    changed_value = _status_value_from_changes(event)
    if changed_value is not None:
        return changed_value

    for mapping in searchable_mappings:
        value = _value_for_keys(mapping, _CURRENT_STATUS_KEYS)
        if value is not None:
            return value

    return None


def _status_value_from_changes(event: Mapping[str, Any]) -> Any:
    for mapping in _walk_mappings(event):
        for key, value in mapping.items():
            if _normalize_key(key) != "changes" or not isinstance(value, Mapping):
                continue

            for changed_key, changed_value in value.items():
                if not _is_status_field_key(changed_key):
                    continue

                if isinstance(changed_value, Mapping):
                    for candidate_key in ("to", "new", "after", "value", "name"):
                        candidate = changed_value.get(candidate_key)
                        if candidate is not None:
                            return candidate
                return changed_value

    return None


def _first_text_for_keys(event: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for mapping in _preferred_mappings(event):
        value = _value_for_keys(mapping, keys)
        text = _value_to_text(value)
        if text:
            return text
    return None


def _preferred_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    paths = (
        ("automation_trigger_info", "triggerContext"),
        ("automationTriggerInfo", "triggerContext"),
        ("triggerContext",),
        ("data", "issue"),
        ("data", "node"),
        ("issue",),
        ("data",),
        ("payload",),
        (),
    )
    mappings: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    for path in paths:
        value: Any = event
        for part in path:
            if not isinstance(value, Mapping):
                value = None
                break
            value = value.get(part)

        if isinstance(value, Mapping) and id(value) not in seen:
            mappings.append(value)
            seen.add(id(value))

    for mapping in _walk_mappings(event, skip_keys=_HISTORICAL_KEYS):
        if id(mapping) not in seen:
            mappings.append(mapping)
            seen.add(id(mapping))

    return mappings


def _value_for_keys(mapping: Mapping[str, Any], keys: Iterable[str]) -> Any:
    values_by_key = {_normalize_key(key): value for key, value in mapping.items()}
    for key in keys:
        if key in values_by_key:
            return values_by_key[key]
    return None


def _iterable_mentions_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_key(value)

    if isinstance(value, Iterable):
        return any(_is_status_field_key(item) for item in value)

    return False


def _is_status_field_key(value: Any) -> bool:
    return _normalize_key(value) in _STATUS_FIELD_KEYS


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(RESEARCH_TITLE_PREFIX.casefold())


def _walk_mappings(
    value: Any,
    *,
    skip_keys: set[str] | None = None,
) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for key, child in value.items():
            if skip_keys and _normalize_key(key) in skip_keys:
                continue
            yield from _walk_mappings(child, skip_keys=skip_keys)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_mappings(child, skip_keys=skip_keys)


def _value_to_text(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "id"):
            text = _value_to_text(value.get(key))
            if text:
                return text
        return None

    text = str(value).strip()
    return text or None


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def _normalize_words(value: Any) -> str:
    text = _value_to_text(value)
    if not text:
        return ""

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    words = re.findall(r"[A-Za-z0-9]+", text.casefold())
    return " ".join(words)


def _main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print(f"invalid JSON input: {error}", file=sys.stderr)
        return 2

    result = build_issue_title_update(event)
    print(json.dumps(result, sort_keys=True) if result is not None else "null")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
