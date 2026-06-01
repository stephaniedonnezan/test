"""Build Linear issue-title updates for Cursor research automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_EXPLICIT_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "targetStatus",
    "target_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_CURRENT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_TITLE_KEYS = ("title", "name", "summary")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TRIGGER_KEYS = ("trigger", "webhookType", "webhook_type", "action", "type", "event", "eventType")
_UPDATED_FIELD_KEYS = ("updatedFields", "updated_fields", "changedFields", "changed_fields")
_OLD_VALUE_KEYS = {"before", "changes", "history", "old", "previous", "updatedFrom", "updated_from"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return the issue-title update for a status change into research."""

    if not isinstance(event, Mapping):
        return None

    mappings = list(_walk_mappings(event))
    if not _is_status_change_event(mappings):
        return None

    new_status = _find_new_status(mappings)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id, title = _find_issue_fields(event)
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if not clean_title or _has_research_prefix(clean_title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _walk_mappings(root: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield useful payload mappings without scanning old status values."""

    seen: set[int] = set()
    queue: list[Mapping[str, Any]] = []

    def enqueue(value: Any) -> None:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            queue.append(value)

    enqueue(root)
    index = 0
    while index < len(queue):
        mapping = queue[index]
        index += 1
        yield mapping

        for key, value in mapping.items():
            if key in _OLD_VALUE_KEYS:
                continue
            if isinstance(value, Mapping):
                enqueue(value)
            elif isinstance(value, list | tuple):
                for item in value:
                    enqueue(item)


def _is_status_change_event(mappings: Iterable[Mapping[str, Any]]) -> bool:
    has_generic_update = False
    has_status_field_change = False

    for mapping in mappings:
        for key in _TRIGGER_KEYS:
            value = mapping.get(key)
            if _is_status_change_trigger(value):
                return True
            if _is_generic_update_trigger(value):
                has_generic_update = True

        if _updated_fields_include_status(mapping):
            has_status_field_change = True

    return has_generic_update and has_status_field_change


def _is_status_change_trigger(value: Any) -> bool:
    normalized = _normalize_words(_string_value(value))
    return normalized in {
        "status change",
        "status changed",
        "state change",
        "state changed",
        "workflow state change",
        "workflow state changed",
    }


def _is_generic_update_trigger(value: Any) -> bool:
    normalized = _normalize_words(_string_value(value))
    return normalized in {"update", "updated", "issue update", "issue updated", "updated issue"}


def _updated_fields_include_status(mapping: Mapping[str, Any]) -> bool:
    for key in _UPDATED_FIELD_KEYS:
        if _field_collection_includes_status(mapping.get(key)):
            return True

    for key in ("updatedFrom", "updated_from"):
        value = mapping.get(key)
        if isinstance(value, Mapping) and any(_is_status_field_name(field) for field in value):
            return True

    return False


def _field_collection_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        return any(_is_status_field_name(field) for field in value)
    if isinstance(value, list | tuple | set):
        return any(_field_collection_includes_status(item) for item in value)
    return False


def _is_status_field_name(value: Any) -> bool:
    words = set(_normalize_words(_string_value(value)).split())
    return bool(words & {"status", "state", "workflow"})


def _find_new_status(mappings: Iterable[Mapping[str, Any]]) -> str | None:
    for key_set in (_EXPLICIT_NEW_STATUS_KEYS, _CURRENT_STATUS_KEYS):
        for mapping in mappings:
            for key in key_set:
                status = _status_name(mapping.get(key))
                if status:
                    return status
    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            status = _string_value(value.get(key))
            if status:
                return status
        return None
    return _string_value(value)


def _find_issue_fields(root: Mapping[str, Any]) -> tuple[str | None, str | None]:
    containers = list(_issue_containers(root))
    fallback_issue_id = _find_first_text(containers, _ISSUE_ID_KEYS)

    for container in containers:
        title = _first_text(container, _TITLE_KEYS)
        if not title:
            continue
        issue_id = _first_text(container, _ISSUE_ID_KEYS) or fallback_issue_id
        if issue_id:
            return issue_id, title

    return fallback_issue_id, None


def _issue_containers(root: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    seen: set[int] = set()

    def yield_once(value: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            yield value

    trigger_context = root.get("triggerContext")
    yield from yield_once(trigger_context)
    if isinstance(trigger_context, Mapping):
        yield from _nested_issue_containers(trigger_context, seen)

    yield from _nested_issue_containers(root, seen)
    yield from yield_once(root)


def _nested_issue_containers(container: Mapping[str, Any], seen: set[int]) -> Iterable[Mapping[str, Any]]:
    for key in ("issue", "data", "payload", "webhook"):
        value = container.get(key)
        if not isinstance(value, Mapping) or id(value) in seen:
            continue

        nested_issue = value.get("issue")
        if isinstance(nested_issue, Mapping) and id(nested_issue) not in seen:
            seen.add(id(nested_issue))
            yield nested_issue

        seen.add(id(value))
        yield value


def _find_first_text(containers: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for container in containers:
        value = _first_text(container, keys)
        if value:
            return value
    return None


def _first_text(container: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = _string_value(container.get(key))
        if value:
            return value
    return None


def _has_research_prefix(title: str) -> bool:
    return re.match(r"^\s*cursor researching\b", title, flags=re.IGNORECASE) is not None


def _normalize_words(value: str | None) -> str:
    if value is None:
        return ""
    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", separated)
    return " ".join(words.casefold().split())


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError as error:
        print(f"Invalid JSON payload: {error}", file=sys.stderr)
        print("null")
        return 1

    update = build_issue_title_update(event)
    print(json.dumps(update) if update else "null")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
