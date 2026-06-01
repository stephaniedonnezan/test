"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research.

    The automation trigger can arrive as a flat Cursor trigger context or as a
    nested Linear webhook payload. This function keeps the output side-effect
    free so callers can decide how to apply the returned update.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize_text(_extract_new_status(event)) != TARGET_STATUS:
        return None

    issue_id = _first_clean_string(
        _get(mapping, "id", "issueId", "issue_id", "identifier")
        for mapping in _issue_mappings(event)
    )
    title = _first_clean_string(
        _get(mapping, "title") for mapping in _issue_mappings(event)
    )

    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = {
        _normalize_text(value)
        for value in _collect_key_values(
            event, "trigger", "webhookType", "eventType", "action", "type"
        )
    }

    if trigger_values & {
        "status changed",
        "status change",
        "state changed",
        "state change",
        "workflow state changed",
        "workflow state change",
        "issue status changed",
    }:
        return True

    if trigger_values & {"update", "updated", "issue update", "issue updated", "updated issue"}:
        return any(_is_status_field(field) for field in _updated_fields(event))

    return False


def _extract_new_status(event: Mapping[str, Any]) -> Any:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )

    for mapping in _status_mappings(event):
        value = _get(mapping, *explicit_keys)
        if value is not None:
            return _status_value(value)

    for mapping in _status_mappings(event):
        value = _get(mapping, "status", "state", "workflowState", "workflow_state")
        if value is not None:
            return _status_value(value)

    return None


def _status_mappings(event: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    mappings: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in mappings:
            mappings.append(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")

    add(trigger_context)
    add(event)
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))
    add(issue)

    for mapping in _walk_mappings(event):
        add(mapping)

    return tuple(mappings)


def _issue_mappings(event: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    mappings: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in mappings:
            mappings.append(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")

    add(trigger_context)
    add(issue)
    if isinstance(data, Mapping):
        add(data.get("issue"))
    add(data)
    add(event)

    return tuple(mappings)


def _status_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _get(value, "name", "title", "label")
    return value


def _collect_key_values(event: Any, *keys: str) -> Iterable[Any]:
    for mapping in _walk_mappings(event):
        for key in keys:
            value = mapping.get(key)
            if isinstance(value, str):
                yield value


def _updated_fields(event: Any) -> Iterable[Any]:
    for mapping in _walk_mappings(event):
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
        ):
            fields = mapping.get(key)
            if isinstance(fields, Mapping):
                yield from fields.keys()
            elif isinstance(fields, Iterable) and not isinstance(fields, (str, bytes)):
                yield from fields

        for key in ("updatedFrom", "updated_from", "previousValues", "previous_values"):
            fields = mapping.get(key)
            if isinstance(fields, Mapping):
                yield from fields.keys()


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested in value.values():
            yield from _walk_mappings(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_mappings(item)


def _is_status_field(field: Any) -> bool:
    normalized = _normalize_text(field)
    return (
        normalized in {"status", "state", "workflow state"}
        or normalized.startswith("status ")
        or normalized.startswith("state ")
        or "workflow state" in normalized
    )


def _get(mapping: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _first_clean_string(values: Iterable[Any]) -> str | None:
    for value in values:
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned:
                return cleaned
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lstrip().casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
