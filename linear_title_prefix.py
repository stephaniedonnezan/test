"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue enters research."""
    if not isinstance(event, Mapping):
        return None

    mappings = list(_candidate_mappings(event))
    if not _is_status_change_event(mappings):
        return None

    status = _new_status(mappings)
    if _normalize(status) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(mappings, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(mappings, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _candidate_mappings(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely payload layers from most specific automation data outward."""
    nested_paths = (
        ("triggerContext",),
        ("data",),
        ("issue",),
        ("triggerContext", "issue"),
        ("triggerContext", "data"),
        ("triggerContext", "data", "issue"),
        ("data", "issue"),
    )

    seen: set[int] = set()
    for candidate in (event, *(_get_path(event, path) for path in nested_paths)):
        if isinstance(candidate, Mapping) and id(candidate) not in seen:
            seen.add(id(candidate))
            yield candidate


def _get_path(mapping: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = mapping
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _is_status_change_event(mappings: list[Mapping[str, Any]]) -> bool:
    event_values = []
    for mapping in mappings:
        event_values.extend(
            _string_values(mapping, ("trigger", "event", "eventType", "webhookType", "action", "type"))
        )

    normalized_events = {_normalize(value) for value in event_values}
    if normalized_events & {
        "status change",
        "status changed",
        "status update",
        "status updated",
        "state change",
        "state changed",
        "workflow state changed",
    }:
        return True

    updated_fields = {_normalize(value) for value in _updated_fields(mappings)}
    if updated_fields & {"status", "state", "workflow state"}:
        return bool(normalized_events & {"update", "updated", "issue update", "issue updated"})

    return False


def _updated_fields(mappings: list[Mapping[str, Any]]) -> Iterable[str]:
    for mapping in mappings:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            value = mapping.get(key)
            if isinstance(value, str):
                yield value
            elif isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
                for item in value:
                    if isinstance(item, str):
                        yield item


def _new_status(mappings: list[Mapping[str, Any]]) -> str | None:
    direct_keys = (
        "newStatus",
        "new_status",
        "newStatusName",
        "new_status_name",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    status_keys = ("status", "state", "workflowState", "workflow_state")

    direct = _first_text(mappings, direct_keys)
    if direct:
        return direct

    for mapping in mappings:
        for key in status_keys:
            value = mapping.get(key)
            if isinstance(value, Mapping):
                text = _first_text([value], ("name", "title", "status"))
                if text:
                    return text
            elif isinstance(value, str):
                return value

    return None


def _first_text(mappings: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for mapping in mappings:
        for key in keys:
            value = mapping.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _string_values(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> Iterable[str]:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            yield value


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    with_word_boundaries = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", with_word_boundaries)
    return re.sub(r"\s+", " ", normalized).strip().lower()


def main() -> int:
    payload = json.load(sys.stdin)
    result = build_issue_title_update(payload)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
