"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_KEYS = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}
_NEW_STATUS_KEYS = {
    "newstatus",
    "newstate",
    "newworkflowstate",
    "tostatus",
    "tostate",
    "toworkflowstate",
    "statusname",
    "statename",
    "workflowstatename",
    "newstatusname",
    "newstatename",
    "newworkflowstatename",
}
_NEW_VALUE_KEYS = ("to", "after", "new", "newvalue", "newstatus", "newstate", "name")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update when a Linear issue enters "to research".

    The Cursor automation trigger can provide a flat ``triggerContext`` object,
    while Linear webhooks commonly nest issue data under ``data`` or ``issue``.
    This function accepts those shapes and returns a side-effect-free action for
    the caller to apply to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_research_status_change(event):
        return None

    issue_id = _first_text(_field_candidates(event, ("id", "issueId", "issue_id", "identifier", "key")))
    title = _first_text(_field_candidates(event, ("title", "name")))

    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _is_research_status_change(event: Mapping[str, Any]) -> bool:
    return _is_status_change_event(event) and _has_target_status(event)


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    for item in _walk_mappings(event):
        for key in ("trigger", "action", "type", "webhookType", "webhook_type", "event"):
            value = item.get(key)
            if isinstance(value, str) and _is_direct_status_change(value):
                return True

    return _changed_fields_include_status(event)


def _is_direct_status_change(value: str) -> bool:
    normalized = _normalize_identifier(value)
    return normalized in {
        "statuschanged",
        "statuschange",
        "issuestatuschanged",
        "issuestatuschange",
        "statechanged",
        "statechange",
        "workflowstatechanged",
        "workflowstatechange",
    }


def _changed_fields_include_status(event: Mapping[str, Any]) -> bool:
    for item in _walk_mappings(event):
        for key, value in item.items():
            normalized_key = _normalize_identifier(key)
            if normalized_key in {"updatedfields", "changedfields"} and _iterable_mentions_status(value):
                return True
            if normalized_key in {"changes", "updatedfrom"} and _mapping_mentions_status(value):
                return True
    return False


def _iterable_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        return _mapping_mentions_status(value)
    if isinstance(value, Iterable):
        return any(_iterable_mentions_status(item) for item in value)
    return False


def _mapping_mentions_status(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    return any(_is_status_field_name(key) for key in value)


def _is_status_field_name(value: Any) -> bool:
    return _normalize_identifier(value) in _STATUS_FIELD_KEYS


def _has_target_status(event: Mapping[str, Any]) -> bool:
    for item in _walk_mappings(event):
        for key, value in item.items():
            normalized_key = _normalize_identifier(key)
            if normalized_key in _NEW_STATUS_KEYS and _value_is_target_status(value):
                return True

    for item in _walk_mappings(event):
        for key, value in item.items():
            if _is_status_field_name(key) and _value_is_target_status(value):
                return True

    return False


def _value_is_target_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_phrase(value) == TARGET_STATUS

    if isinstance(value, Mapping):
        for key in _NEW_VALUE_KEYS:
            if key in {_normalize_identifier(candidate) for candidate in value}:
                selected = _value_for_normalized_key(value, key)
                if _value_is_target_status(selected):
                    return True

    return False


def _value_for_normalized_key(mapping: Mapping[str, Any], normalized_key: str) -> Any:
    for key, value in mapping.items():
        if _normalize_identifier(key) == normalized_key:
            return value
    return None


def _field_candidates(event: Mapping[str, Any], keys: tuple[str, ...]) -> list[Any]:
    candidates: list[Any] = []
    for item in _preferred_issue_mappings(event):
        for key in keys:
            if key in item:
                candidates.append(item[key])
    return candidates


def _preferred_issue_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    mappings: list[Mapping[str, Any]] = [event]

    for path in (
        ("triggerContext",),
        ("issue",),
        ("data", "issue"),
        ("triggerContext", "issue"),
        ("triggerContext", "data", "issue"),
        ("data",),
        ("triggerContext", "data"),
    ):
        value = _get_path(event, path)
        if isinstance(value, Mapping):
            mappings.append(value)

    return mappings


def _get_path(mapping: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = mapping
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _first_text(values: Iterable[Any]) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _has_research_prefix(title: str) -> bool:
    return title.strip().lower().startswith(PREFIX.lower())


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_mappings(child)


def _normalize_identifier(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def _normalize_phrase(value: str) -> str:
    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value.strip())
    spaced = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return re.sub(r"\s+", " ", spaced).strip().lower()


def main() -> int:
    payload = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(payload), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
