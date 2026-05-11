"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import re
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title-update command for issues entering To Research.

    The automation platform passes a compact ``triggerContext`` payload, while
    Linear webhooks commonly nest issue details under ``data.issue``. This
    function accepts both shapes and returns a side-effect-free command that the
    caller can translate into the actual Linear API mutation.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_new_status(event)
    if _normalize(status) != _normalize(TARGET_STATUS):
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if _has_research_prefix(clean_title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {clean_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    for mapping in _event_mappings(event):
        for key in ("trigger", "event", "eventType", "action", "type"):
            value = _string_value(mapping.get(key))
            if _normalize(value) in {
                "statuschanged",
                "statuschange",
                "statechanged",
                "workflowstatechanged",
            }:
                return True

        if _has_status_update_marker(mapping):
            return True

    return False


def _has_status_update_marker(mapping: Mapping[str, Any]) -> bool:
    for key in (
        "updatedFields",
        "updated_fields",
        "changedFields",
        "changed_fields",
        "fields",
    ):
        if _contains_status_field(mapping.get(key)):
            return True

    for key in ("updatedFrom", "updated_from", "changes"):
        value = mapping.get(key)
        if isinstance(value, Mapping) and any(_is_status_field(field) for field in value):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        return any(_is_status_field(field) for field in value)

    if isinstance(value, Iterable):
        return any(_is_status_field(item) for item in value)

    return False


def _is_status_field(value: Any) -> bool:
    normalized = _normalize(_string_value(value))
    return normalized in {
        "status",
        "state",
        "stateid",
        "workflowstate",
        "workflowstateid",
    }


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for mapping in _event_mappings(event):
        for key in (
            "newStatus",
            "new_status",
            "newStatusName",
            "status",
            "state",
            "workflowState",
        ):
            value = mapping.get(key)
            if isinstance(value, Mapping):
                value = value.get("name") or value.get("title")
            text = _string_value(value)
            if text:
                return text

    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for mapping in _issue_mappings(event):
        for key in ("id", "issueId", "issue_id", "identifier"):
            value = _string_value(mapping.get(key))
            if value:
                return value.strip()

    return None


def _extract_title(event: Mapping[str, Any]) -> str | None:
    for mapping in _issue_mappings(event):
        value = _string_value(mapping.get("title"))
        if value:
            return value

    return None


def _event_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _dedupe_mappings(
        [
            event,
            _mapping_at(event, "triggerContext"),
            _mapping_at(event, "data"),
            _mapping_at(event, "payload"),
            _mapping_at(event, "issue"),
            _mapping_at(event, "triggerContext", "data"),
            _mapping_at(event, "triggerContext", "issue"),
            _mapping_at(event, "data", "issue"),
            _mapping_at(event, "payload", "issue"),
        ]
    )


def _issue_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _dedupe_mappings(
        [
            _mapping_at(event, "issue"),
            _mapping_at(event, "data", "issue"),
            _mapping_at(event, "payload", "issue"),
            _mapping_at(event, "triggerContext", "issue"),
            _mapping_at(event, "triggerContext", "data", "issue"),
            _mapping_at(event, "triggerContext"),
            _mapping_at(event, "data"),
            _mapping_at(event, "payload"),
            event,
        ]
    )


def _mapping_at(mapping: Mapping[str, Any], *path: str) -> Mapping[str, Any] | None:
    current: Any = mapping
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)

    return current if isinstance(current, Mapping) else None


def _dedupe_mappings(values: Iterable[Mapping[str, Any] | None]) -> list[Mapping[str, Any]]:
    mappings: list[Mapping[str, Any]] = []
    seen: set[int] = set()
    for value in values:
        if value is None:
            continue
        identity = id(value)
        if identity not in seen:
            mappings.append(value)
            seen.add(identity)

    return mappings


def _normalize(value: str | None) -> str:
    if not value:
        return ""

    spaced = _CAMEL_BOUNDARY_RE.sub(" ", value.strip())
    return _NON_ALNUM_RE.sub("", spaced.lower())


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None

    return None


def _has_research_prefix(title: str) -> bool:
    return title.lstrip().lower().startswith(PREFIX.lower())
