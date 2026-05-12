"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections import deque
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_KEYS = {"status", "state", "workflowState", "workflow_state"}
_NEW_STATUS_KEYS = {
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
}
_TITLE_KEYS = ("title", "name")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "id")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
)
_TRIGGER_KEYS = ("trigger", "webhookType", "webhook_type", "action", "type")
_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflowstatus"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves into To Research."""

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _find_new_status(event)
    if _normalize_text(status) != _normalize_text(TARGET_STATUS):
        return None

    issue_id, title = _extract_issue_identity(event)
    if not issue_id or not title:
        return None

    trimmed_title = title.strip()
    if not trimmed_title or _has_research_prefix(trimmed_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {trimmed_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    markers = {
        _compact_text(value)
        for mapping in _iter_mappings(event)
        for key, value in mapping.items()
        if key in _TRIGGER_KEYS and isinstance(value, str)
    }

    if markers.intersection({"statuschanged", "statuschange", "statusupdated"}):
        return True

    update_markers = {"update", "updated", "issueupdated", "updatedissue"}
    if markers.intersection(update_markers) and _has_updated_status_field(event):
        return True

    return not markers and _has_updated_status_field(event)


def _has_updated_status_field(event: Mapping[str, Any]) -> bool:
    for mapping in _iter_mappings(event):
        for key in _UPDATED_FIELD_KEYS:
            if key not in mapping:
                continue
            for field_name in _coerce_iterable(mapping[key]):
                if _compact_text(field_name) in _STATUS_FIELD_NAMES:
                    return True
    return False


def _find_new_status(event: Mapping[str, Any]) -> str | None:
    for mapping in _iter_mappings(event):
        for key in _NEW_STATUS_KEYS:
            value = mapping.get(key)
            if isinstance(value, str) and value.strip():
                return value
            if isinstance(value, Mapping):
                name = value.get("name")
                if isinstance(name, str) and name.strip():
                    return name

    for mapping in _iter_mappings(event):
        for key in _STATUS_KEYS:
            value = mapping.get(key)
            if isinstance(value, str) and value.strip():
                return value
            if isinstance(value, Mapping):
                name = value.get("name")
                if isinstance(name, str) and name.strip():
                    return name

    return None


def _extract_issue_identity(event: Mapping[str, Any]) -> tuple[str | None, str | None]:
    for mapping in _candidate_issue_mappings(event):
        title = _first_string(mapping, _TITLE_KEYS)
        if title is None:
            continue

        issue_id = _first_string(mapping, _ISSUE_ID_KEYS)
        if issue_id is None:
            issue_id = _first_string(event, ("issueId", "issue_id"))
        return issue_id, title

    return None, None


def _candidate_issue_mappings(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    preferred_paths = (
        ("triggerContext",),
        ("data", "issue"),
        ("payload", "issue"),
        ("issue",),
        ("data",),
        ("payload", "data"),
        (),
    )

    seen: set[int] = set()
    for path in preferred_paths:
        mapping = _get_mapping_at_path(event, path)
        if mapping is not None and id(mapping) not in seen:
            seen.add(id(mapping))
            yield mapping

    for mapping in _iter_mappings(event):
        if id(mapping) not in seen and _first_string(mapping, _TITLE_KEYS) is not None:
            seen.add(id(mapping))
            yield mapping


def _get_mapping_at_path(
    event: Mapping[str, Any], path: tuple[str, ...]
) -> Mapping[str, Any] | None:
    current: Any = event
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, Mapping) else None


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    queue: deque[Any] = deque([value])
    seen: set[int] = set()

    while queue:
        current = queue.popleft()
        if isinstance(current, Mapping):
            if id(current) in seen:
                continue
            seen.add(id(current))
            yield current
            queue.extend(current.values())
        elif isinstance(current, list):
            queue.extend(current)


def _first_string(mapping: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)
    return None


def _coerce_iterable(value: Any) -> Iterable[Any]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Mapping):
        return value.keys()
    if isinstance(value, Iterable):
        return value
    return ()


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_text(value: str | None) -> str:
    if not isinstance(value, str):
        return ""
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value)
    return " ".join(value.casefold().split())


def _compact_text(value: Any) -> str:
    normalized = _normalize_text(value if isinstance(value, str) else str(value))
    return normalized.replace(" ", "")


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
