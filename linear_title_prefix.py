"""Build Linear issue-title updates for issues moved to research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "status id",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue enters research."""

    if not isinstance(event, Mapping):
        return None

    mappings = list(_ordered_mappings(event))
    if not _is_status_change_event(mappings):
        return None

    if not _is_target_status(mappings):
        return None

    issue_id = _first_text(mappings, ("issueId", "issue_id", "id", "identifier"))
    title = _first_text(mappings, ("title", "issueTitle", "issue_title"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _ordered_mappings(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield common wrapper and issue objects before recursively nested mappings."""

    yielded: set[int] = set()

    def yield_once(value: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(value, Mapping) and id(value) not in yielded:
            yielded.add(id(value))
            yield value

    for mapping in yield_once(event):
        yield mapping

    for key in ("triggerContext", "data", "issue"):
        for mapping in yield_once(event.get(key)):
            yield mapping

    data = event.get("data")
    if isinstance(data, Mapping):
        for key in ("issue", "state", "status", "workflowState"):
            for mapping in yield_once(data.get(key)):
                yield mapping

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        for key in ("issue", "state", "status", "workflowState"):
            for mapping in yield_once(trigger_context.get(key)):
                yield mapping

    for mapping in _walk_mappings(event):
        if id(mapping) not in yielded:
            yielded.add(id(mapping))
            yield mapping


def _is_status_change_event(mappings: Iterable[Mapping[str, Any]]) -> bool:
    mappings = list(mappings)
    event_names = {
        _normalize_words(value)
        for mapping in mappings
        for key in ("trigger", "webhookType", "action", "type", "eventType")
        if (value := mapping.get(key)) is not None
    }

    if event_names & {"status changed", "status change", "statuschanged"}:
        return True

    issue_update_names = {"issue updated", "updated issue", "update", "updated"}
    if event_names & issue_update_names:
        return _has_status_field_change(mappings)

    return _has_status_field_change(mappings)


def _has_status_field_change(mappings: Iterable[Mapping[str, Any]]) -> bool:
    change_keys = (
        "updatedFields",
        "changedFields",
        "changed_fields",
        "changes",
        "updatedFrom",
        "previousValues",
        "previous",
    )

    return any(
        _contains_status_field(mapping.get(key))
        for mapping in mappings
        for key in change_keys
        if key in mapping
    )


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) for key in value)
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_words(value)
    return normalized in _STATUS_FIELD_NAMES


def _is_target_status(mappings: Iterable[Mapping[str, Any]]) -> bool:
    return any(
        _normalize_words(candidate) == TARGET_STATUS
        for candidate in _status_candidates(mappings)
    )


def _status_candidates(mappings: Iterable[Mapping[str, Any]]) -> Iterable[Any]:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "toStatus",
        "to_status",
        "targetStatus",
        "statusName",
        "stateName",
        "workflowStateName",
    )
    object_keys = ("status", "state", "workflowState")

    mappings = list(mappings)
    for mapping in mappings:
        for key in explicit_keys:
            if key in mapping:
                yield _name_or_value(mapping[key])

    for mapping in mappings:
        for key in object_keys:
            if key in mapping:
                yield _name_or_value(mapping[key])


def _name_or_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return value.get("name")
    return value


def _first_text(mappings: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for mapping in mappings:
        for key in keys:
            value = mapping.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _has_title_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(TITLE_PREFIX)}\b", title, re.IGNORECASE) is not None


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    words = re.sub(r"[^A-Za-z0-9]+", " ", words)
    return re.sub(r"\s+", " ", words).strip().lower()


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested in value.values():
            yield from _walk_mappings(nested)
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for nested in value:
            yield from _walk_mappings(nested)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update:
        print(json.dumps(update, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
