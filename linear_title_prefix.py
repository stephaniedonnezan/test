"""Build Linear issue-title updates for Cursor research automation.

The automation is intentionally side-effect free: callers pass in a Linear or
Cursor webhook payload and receive the issue-title update they should perform.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_EXPLICIT_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "targetStatus",
    "target_status",
)
_CURRENT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_ID_KEYS = ("issueId", "issue_id", "id", "identifier")
_SKIP_NESTED_KEYS = {
    "before",
    "changes",
    "history",
    "old",
    "previous",
    "updatedFrom",
    "updated_from",
}
_TRIGGER_KEYS = ("trigger", "webhookType", "webhook_type", "action", "type", "event")
_UPDATE_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return the issue title update for a matching status-change event.

    The returned dictionary is deliberately simple so a caller can translate it
    to whichever Linear client or workflow action performs the mutation.
    """

    if not isinstance(event, Mapping):
        return None

    maps = list(_walk_mappings(event))
    if not _is_status_change_event(maps):
        return None

    new_status = _find_new_status(maps)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id, title = _find_issue_fields(maps)
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {title.strip()}",
    }


def _walk_mappings(root: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely issue/trigger mappings in priority order."""

    seen: set[int] = set()
    queue: list[Mapping[str, Any]] = []

    def enqueue(value: Any) -> None:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            queue.append(value)

    # Cursor automation payloads commonly keep the useful issue fields here.
    enqueue(root.get("triggerContext"))
    data = root.get("data")
    if isinstance(data, Mapping):
        enqueue(data.get("issue"))
        enqueue(data)
    enqueue(root.get("issue"))
    enqueue(root.get("payload"))
    enqueue(root)

    index = 0
    while index < len(queue):
        mapping = queue[index]
        index += 1
        yield mapping

        for key, value in mapping.items():
            if key in _SKIP_NESTED_KEYS:
                continue
            if isinstance(value, Mapping):
                enqueue(value)
            elif isinstance(value, list):
                for item in value:
                    enqueue(item)


def _is_status_change_event(maps: Iterable[Mapping[str, Any]]) -> bool:
    status_field_changed = False
    has_generic_update = False

    for mapping in maps:
        for key in _TRIGGER_KEYS:
            if _is_status_changed_trigger(mapping.get(key)):
                return True

        if _is_generic_update(mapping):
            has_generic_update = True

        if _updated_fields_include_status(mapping):
            status_field_changed = True

    return has_generic_update and status_field_changed


def _is_status_changed_trigger(value: Any) -> bool:
    normalized = _normalize_words(_string_value(value))
    if not normalized:
        return False

    words = set(normalized.split())
    return "status" in words and ("change" in words or "changed" in words)


def _is_generic_update(mapping: Mapping[str, Any]) -> bool:
    for key in _TRIGGER_KEYS:
        normalized = _normalize_words(_string_value(mapping.get(key)))
        if normalized in {"update", "updated", "issue update", "issue updated", "updated issue"}:
            return True
    return False


def _updated_fields_include_status(mapping: Mapping[str, Any]) -> bool:
    for key in _UPDATE_FIELD_KEYS:
        if _field_collection_includes_status(mapping.get(key)):
            return True

    for key in ("updatedFrom", "updated_from"):
        updated_from = mapping.get(key)
        if isinstance(updated_from, Mapping):
            for field_name in updated_from:
                if _is_status_field_name(field_name):
                    return True

    return False


def _field_collection_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) for key in value)
    if isinstance(value, list):
        return any(_field_collection_includes_status(item) for item in value)
    return False


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_words(_string_value(value))
    words = set(normalized.split())
    return bool(words & {"status", "state", "workflow"})


def _find_new_status(maps: Iterable[Mapping[str, Any]]) -> str | None:
    for key_set in (_EXPLICIT_NEW_STATUS_KEYS, _CURRENT_STATUS_KEYS):
        for mapping in maps:
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


def _find_issue_fields(maps: Iterable[Mapping[str, Any]]) -> tuple[str | None, str | None]:
    fallback_issue_id: str | None = None

    for mapping in maps:
        if fallback_issue_id is None:
            fallback_issue_id = _find_issue_id(mapping)

        title = _string_value(mapping.get("title"))
        if title:
            issue_id = _find_issue_id(mapping) or fallback_issue_id
            if issue_id:
                return issue_id.strip(), title.strip()

    return fallback_issue_id.strip() if fallback_issue_id else None, None


def _find_issue_id(mapping: Mapping[str, Any]) -> str | None:
    for key in _ID_KEYS:
        issue_id = _string_value(mapping.get(key))
        if issue_id:
            return issue_id
    return None


def _has_research_prefix(title: str) -> bool:
    return re.match(r"^\s*cursor researching\b", title, flags=re.IGNORECASE) is not None


def _normalize_words(value: str | None) -> str | None:
    if value is None:
        return None
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return " ".join(value.lower().split())


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        print("null")
        return 1

    update = build_issue_title_update(event)
    print(json.dumps(update) if update else "null")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
