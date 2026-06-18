"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "stateid", "statusid"}
DIRECT_STATUS_TRIGGERS = {"statuschanged", "statuschange", "statechanged", "statechange"}
UPDATE_TRIGGERS = {"update", "updated", "issueupdate", "issueupdated", "updatedissue"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to "to research".

    The function accepts the flat Cursor automation payload shape and common
    nested Linear webhook variants. It is intentionally side-effect free so the
    caller can decide how to apply the returned update action.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize_words(_new_status(event)) != TARGET_STATUS:
        return None

    issue_id = _first_text(_issue_id_candidates(event))
    title = _first_text(_title_candidates(event))
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    triggers = {_normalize_token(value) for value in _trigger_candidates(event)}
    triggers.discard("")

    if triggers & DIRECT_STATUS_TRIGGERS:
        return True

    if triggers & UPDATE_TRIGGERS:
        return _changed_status_fields(event)

    # Cursor's status-change automation payload can be represented only through
    # explicit old/new status fields.
    return any(
        _lookup_path(mapping, path) is not None
        for mapping in _mappings(event)
        for path in _explicit_status_value_paths()
    )


def _changed_status_fields(event: Mapping[str, Any]) -> bool:
    for mapping in _mappings(event):
        for key in ("updatedFields", "changedFields", "changed_fields", "updated_fields"):
            fields = mapping.get(key)
            if _sequence_contains_status_field(fields):
                return True

        changes = mapping.get("changes")
        if isinstance(changes, Mapping):
            if any(_normalize_token(key) in STATUS_FIELD_NAMES for key in changes):
                return True
        elif _sequence_contains_status_field(changes):
            return True

    return False


def _new_status(event: Mapping[str, Any]) -> Any:
    for mapping in _mappings(event):
        for path in _explicit_status_value_paths():
            value = _lookup_path(mapping, path)
            if value is not None:
                return value

    for value in _change_values(event):
        status = _extract_status_name(value)
        if status is not None:
            return status

    for mapping in _mappings(event):
        for path in _current_status_value_paths():
            value = _lookup_path(mapping, path)
            if value is not None:
                return value

    return None


def _explicit_status_value_paths() -> tuple[tuple[str, ...], ...]:
    return (
        ("newStatus",),
        ("new_status",),
        ("newState",),
        ("new_state",),
        ("newWorkflowState",),
        ("new_workflow_state",),
    )


def _current_status_value_paths() -> tuple[tuple[str, ...], ...]:
    return (
        ("status",),
        ("status", "name"),
        ("state",),
        ("state", "name"),
        ("workflowState",),
        ("workflowState", "name"),
        ("workflow_state",),
        ("workflow_state", "name"),
    )


def _change_values(event: Mapping[str, Any]) -> list[Any]:
    values: list[Any] = []
    for mapping in _mappings(event):
        changes = mapping.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for key, change in changes.items():
            if _normalize_token(key) not in STATUS_FIELD_NAMES:
                continue

            if isinstance(change, Mapping):
                for candidate_key in (
                    "to",
                    "toValue",
                    "new",
                    "newValue",
                    "after",
                    "current",
                    "value",
                    "name",
                ):
                    if candidate_key in change:
                        values.append(change[candidate_key])
            else:
                values.append(change)

    return values


def _trigger_candidates(event: Mapping[str, Any]) -> list[Any]:
    values: list[Any] = []
    for mapping in _mappings(event):
        for key in ("trigger", "webhookType", "action", "type", "eventType", "event_type"):
            if key in mapping:
                values.append(mapping[key])
    return values


def _issue_id_candidates(event: Mapping[str, Any]) -> list[Any]:
    values: list[Any] = []
    for mapping in _mappings(event):
        for key in ("issueId", "issue_id", "identifier", "key", "id"):
            if key in mapping:
                values.append(mapping[key])
    return values


def _title_candidates(event: Mapping[str, Any]) -> list[Any]:
    values: list[Any] = []
    for mapping in _mappings(event):
        if "title" in mapping:
            values.append(mapping["title"])
        if "issue" in mapping and isinstance(mapping["issue"], Mapping):
            values.append(mapping["issue"].get("title"))
    return values


def _mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    mappings: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def add(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        marker = id(value)
        if marker in seen:
            return
        seen.add(marker)
        mappings.append(value)

    add(event)
    trigger_context = event.get("triggerContext")
    add(trigger_context)
    data = event.get("data")
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("data"))
    if isinstance(trigger_context, Mapping):
        nested_data = trigger_context.get("data")
        add(nested_data)
        if isinstance(nested_data, Mapping):
            add(nested_data.get("issue"))
    add(event.get("issue"))

    return mappings


def _lookup_path(mapping: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = mapping
    for key in path:
        if not isinstance(value, Mapping) or key not in value:
            return None
        value = value[key]
    return _extract_status_name(value)


def _extract_status_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if key in value:
                return value[key]
        return None
    return value


def _sequence_contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_token(value) in STATUS_FIELD_NAMES

    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        return False

    for item in value:
        if isinstance(item, Mapping):
            field = item.get("field") or item.get("name") or item.get("key")
            if _normalize_token(field) in STATUS_FIELD_NAMES:
                return True
        elif _normalize_token(item) in STATUS_FIELD_NAMES:
            return True

    return False


def _first_text(values: Sequence[Any]) -> str | None:
    for value in values:
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text
    return None


def _has_research_prefix(title: str) -> bool:
    return re.match(r"^\s*cursor researching\b", title, flags=re.IGNORECASE) is not None


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^a-z0-9]+", " ", spaced.lower())
    return " ".join(normalized.split())


def _normalize_token(value: Any) -> str:
    return _normalize_words(value).replace(" ", "")


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    print(json.dumps(update, sort_keys=True) if update is not None else "null")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
