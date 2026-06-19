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

_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_WORD_RE = re.compile(r"[^A-Za-z0-9]+")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue enters To Research.

    The automation trigger payload has appeared in both flat Cursor
    `triggerContext` form and nested Linear webhook form. This function accepts
    both shapes and keeps side effects outside this module.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _new_status(event)
    if _normalise_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text_value(_issue_sources(event), ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text_value(_issue_sources(event), ("title", "issueTitle", "issue_title"))
    if not issue_id or not title:
        return None

    trimmed_title = title.strip()
    if _has_research_prefix(trimmed_title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {trimmed_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = {
        _normalise_words(value)
        for source in _walk_mappings(event)
        for key, value in source.items()
        if _normalise_key(key) in {"trigger", "webhooktype", "action", "type", "eventtype"}
    }

    direct_status_change = any(
        value in {"status changed", "state changed", "workflow state changed"}
        or _compact(value) in {"statuschanged", "statechanged", "workflowstatechanged"}
        for value in trigger_values
    )
    if direct_status_change:
        return True

    generic_issue_update = any(
        value in {"update", "updated", "issue updated", "updated issue"}
        for value in trigger_values
    )
    return generic_issue_update and _updated_fields_include_status(event)


def _new_status(event: Mapping[str, Any]) -> Any:
    explicit_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "statusName",
        "status_name",
        "newState",
        "new_state",
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    for key_group in (explicit_keys, fallback_keys):
        for source in _status_sources(event):
            value = _first_value(source, key_group)
            if value is not None:
                return _status_name(value)

    return None


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    field_keys = {
        "updatedfields",
        "updatedfieldids",
        "changedfields",
        "changedfieldids",
    }
    change_keys = {"changes", "updatedfrom", "updatedfromvalues"}

    for source in _walk_mappings(event):
        for key, value in source.items():
            normalised_key = _normalise_key(key)
            if normalised_key in field_keys and any(_is_status_field(field) for field in _field_names(value)):
                return True
            if normalised_key in change_keys and isinstance(value, Mapping):
                if any(_is_status_field(field) for field in value):
                    return True

    return False


def _issue_sources(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    for key in ("triggerContext", "trigger_context"):
        value = event.get(key)
        if isinstance(value, Mapping):
            yield value

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            yield issue

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue

    if isinstance(data, Mapping):
        yield data

    yield event


def _status_sources(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    for key in ("triggerContext", "trigger_context"):
        value = event.get(key)
        if isinstance(value, Mapping):
            yield value

    yield event

    data = event.get("data")
    if isinstance(data, Mapping):
        yield data
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            yield issue

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue


def _walk_mappings(value: Any, max_depth: int = 4) -> Iterable[Mapping[str, Any]]:
    if not isinstance(value, Mapping) or max_depth < 0:
        return

    yield value
    for child in value.values():
        if isinstance(child, Mapping):
            yield from _walk_mappings(child, max_depth - 1)
        elif isinstance(child, list):
            for item in child:
                if isinstance(item, Mapping):
                    yield from _walk_mappings(item, max_depth - 1)


def _first_text_value(sources: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for source in sources:
        value = _first_value(source, keys)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _first_value(source: Mapping[str, Any], keys: Iterable[str]) -> Any:
    wanted = {_normalise_key(key) for key in keys}
    for key, value in source.items():
        if _normalise_key(key) in wanted:
            return value
    return None


def _status_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _first_value(value, ("name", "title", "label", "status", "state"))
    return value


def _field_names(value: Any) -> Iterable[Any]:
    if isinstance(value, str):
        yield from (part.strip() for part in re.split(r"[,;|]", value) if part.strip())
        return

    if isinstance(value, Mapping):
        yield from value.keys()
        return

    if isinstance(value, Iterable):
        for item in value:
            if isinstance(item, Mapping):
                field_name = _first_value(item, ("field", "name", "key", "id"))
                if field_name is not None:
                    yield field_name
            else:
                yield item


def _is_status_field(value: Any) -> bool:
    return _compact(_normalise_words(value)) in {"status", "state", "workflowstate"}


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalise_words(value: Any) -> str:
    if value is None:
        return ""
    text = _CAMEL_BOUNDARY_RE.sub(" ", str(value).strip())
    text = _NON_WORD_RE.sub(" ", text)
    return " ".join(text.lower().split())


def _normalise_key(value: Any) -> str:
    return _compact(_normalise_words(value))


def _compact(value: str) -> str:
    return value.replace(" ", "")


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is None:
        return 0
    print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
