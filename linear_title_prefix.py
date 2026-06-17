"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_TRIGGER_KEYS = {
    "action",
    "event",
    "eventtype",
    "trigger",
    "type",
    "webhooktype",
}
_NEW_STATUS_KEYS = {
    "newstate",
    "newstatename",
    "newstatus",
    "newstatusname",
    "newworkflowstate",
    "newworkflowstatename",
    "statename",
    "statusname",
    "workflowstatename",
}
_STATUS_CONTAINER_KEYS = {
    "state",
    "status",
    "workflowstate",
}
_OLD_VALUE_KEYS = {
    "before",
    "from",
    "old",
    "previous",
    "previousvalue",
    "updatedfrom",
}
_UPDATED_FIELD_KEYS = {
    "changedfields",
    "changes",
    "updatedfields",
    "updatedfrom",
}
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    The automation receives slightly different payload shapes depending on
    whether it is triggered by Cursor's wrapper or Linear directly, so this
    function accepts both flat and nested issue data.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id, title = _extract_issue_id_and_title(event)
    if not issue_id or not title:
        return None

    clean_title = str(title).strip()
    if not clean_title or _has_research_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": str(issue_id).strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_names = {
        _normalize_text(value)
        for value in _trigger_values(event)
        if isinstance(value, str)
    }
    trigger_names.discard("")

    if trigger_names & _STATUS_CHANGE_TRIGGERS:
        return True

    if trigger_names & _UPDATE_TRIGGERS:
        return _updated_fields_include_status(event)

    return not trigger_names and _updated_fields_include_status(event)


def _trigger_values(event: Mapping[str, Any]) -> Iterable[Any]:
    for context in _walk_mappings(event, skip_old_values=True):
        for key, value in context.items():
            if _normalize_key(key) in _TRIGGER_KEYS:
                yield value


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for context in _walk_mappings(event, skip_old_values=False):
        for key, value in context.items():
            normalized_key = _normalize_key(key)
            if normalized_key in _UPDATED_FIELD_KEYS:
                if any(_is_status_field(field) for field in _field_names(value)):
                    return True
    return False


def _field_names(value: Any) -> Iterable[Any]:
    if isinstance(value, Mapping):
        yield from value.keys()
        for nested_value in value.values():
            yield from _field_names(nested_value)
    elif isinstance(value, str):
        yield value
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        for item in value:
            if isinstance(item, Mapping):
                yield from item.keys()
                field = _lookup(item, ("field", "name"))
                if field is not None:
                    yield field
            else:
                yield item


def _extract_new_status(event: Mapping[str, Any]) -> Any:
    for context in _walk_mappings(event, skip_old_values=True):
        for key, value in context.items():
            if _normalize_key(key) in _NEW_STATUS_KEYS:
                return _name_or_value(value)

    for context in _status_contexts(event):
        for key, value in context.items():
            if _normalize_key(key) in _STATUS_CONTAINER_KEYS:
                status = _name_or_value(value)
                if status is not None:
                    return status

    return None


def _extract_issue_id_and_title(event: Mapping[str, Any]) -> tuple[Any | None, Any | None]:
    title_contexts = [context for context in _issue_contexts(event) if _lookup(context, ("title",))]
    for context in title_contexts:
        issue_id = _lookup(context, _ISSUE_ID_KEYS)
        if issue_id is not None:
            return issue_id, _lookup(context, ("title",))

    title = _lookup(title_contexts[0], ("title",)) if title_contexts else None
    issue_id = next(
        (
            _lookup(context, _ISSUE_ID_KEYS)
            for context in _issue_contexts(event)
            if _lookup(context, _ISSUE_ID_KEYS) is not None
        ),
        None,
    )
    return issue_id, title


def _issue_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    trigger_context = _as_mapping(event.get("triggerContext"))
    data = _as_mapping(event.get("data"))
    issue = _as_mapping(event.get("issue"))

    yield from _nested_issue_contexts(trigger_context)
    yield from _nested_issue_contexts(data)
    if issue is not None:
        yield issue
    if data is not None:
        yield data
    if trigger_context is not None:
        yield trigger_context
    yield event


def _nested_issue_contexts(context: Mapping[str, Any] | None) -> Iterable[Mapping[str, Any]]:
    if context is None:
        return
    issue = _as_mapping(context.get("issue"))
    data = _as_mapping(context.get("data"))
    if issue is not None:
        yield issue
    if data is not None:
        nested_issue = _as_mapping(data.get("issue"))
        if nested_issue is not None:
            yield nested_issue


def _status_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    trigger_context = _as_mapping(event.get("triggerContext"))
    data = _as_mapping(event.get("data"))

    if trigger_context is not None:
        yield trigger_context
    yield event
    if data is not None:
        yield data
    yield from _issue_contexts(event)


def _walk_mappings(value: Any, *, skip_old_values: bool) -> Iterable[Mapping[str, Any]]:
    if not isinstance(value, Mapping):
        return

    yield value
    for key, nested_value in value.items():
        if skip_old_values and _normalize_key(key) in _OLD_VALUE_KEYS:
            continue
        if isinstance(nested_value, Mapping):
            yield from _walk_mappings(nested_value, skip_old_values=skip_old_values)
        elif isinstance(nested_value, Sequence) and not isinstance(
            nested_value, (bytes, bytearray, str)
        ):
            for item in nested_value:
                yield from _walk_mappings(item, skip_old_values=skip_old_values)


def _lookup(context: Mapping[str, Any], keys: Iterable[str]) -> Any:
    wanted = {_normalize_key(key) for key in keys}
    for key, value in context.items():
        if _normalize_key(key) in wanted and value is not None:
            if isinstance(value, str):
                stripped_value = value.strip()
                if not stripped_value:
                    continue
                return stripped_value
            return value
    return None


def _name_or_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _lookup(value, ("name", "title", "status", "state"))
    return value


def _is_status_field(value: Any) -> bool:
    return _normalize_key(value) in _STATUS_CONTAINER_KEYS


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    words = _words(str(value))
    return " ".join(words).lower()


def _normalize_key(value: Any) -> str:
    return "".join(_words(str(value))).lower()


def _words(value: str) -> list[str]:
    camel_spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    return re.findall(r"[A-Za-z0-9]+", camel_spaced)


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
