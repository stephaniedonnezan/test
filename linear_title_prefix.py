"""Build Linear issue title updates for the research status automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to "to research"."""

    if not isinstance(event, Mapping):
        return None

    sources = _collect_sources(event)
    if not _is_status_change_event(sources):
        return None

    status = _first_text_value(
        sources,
        (
            "newStatus",
            "new_status",
            "status",
            "state",
            "workflowState",
            "workflow_state",
        ),
    )
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue = _find_issue_mapping(event)
    issue_id = _first_text_value(
        (issue, *sources),
        ("id", "issueId", "issue_id", "identifier", "uuid"),
    )
    title = _first_text_value((issue, *sources), ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _collect_sources(event: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    sources: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping):
            sources.append(value)

    add(event)
    add(event.get("triggerContext"))
    add(event.get("data"))
    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("state"))
        add(data.get("workflowState"))
    add(event.get("issue"))
    return tuple(sources)


def _find_issue_mapping(event: Mapping[str, Any]) -> Mapping[str, Any]:
    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            return issue
    issue = event.get("issue")
    if isinstance(issue, Mapping):
        return issue
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context
    return event


def _is_status_change_event(sources: tuple[Mapping[str, Any], ...]) -> bool:
    for source in sources:
        for key in ("trigger", "webhookType"):
            if _normalize_text(source.get(key)) == "status changed":
                return True

    status_field_changed = any(_updated_status_field(source) for source in sources)
    for source in sources:
        for key in ("action", "type", "webhookType", "trigger"):
            value = _normalize_text(source.get(key))
            if value in {"issue updated", "updated issue", "update", "updated"}:
                return status_field_changed

    return False


def _updated_status_field(source: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "updatedFrom", "updated_from"):
        fields = source.get(key)
        if isinstance(fields, Mapping):
            if any(_is_status_field(field) for field in fields):
                return True
        elif isinstance(fields, str):
            if _is_status_field(fields):
                return True
        elif isinstance(fields, list | tuple | set):
            if any(_is_status_field(field) for field in fields):
                return True
    return False


def _is_status_field(field: Any) -> bool:
    if isinstance(field, Mapping):
        field = field.get("field") or field.get("name") or field.get("key")
    normalized = _normalize_key(field)
    return normalized in STATUS_FIELDS


def _first_text_value(
    sources: tuple[Mapping[str, Any], ...],
    keys: tuple[str, ...],
) -> str | None:
    for source in sources:
        for key in keys:
            value = _extract_value(source.get(key))
            if value:
                return value
    return None


def _extract_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "id", "identifier"):
            nested = value.get(key)
            if isinstance(nested, str):
                return nested
    return None


def _normalize_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()
    return re.sub(r"\s+", " ", normalized)


def _normalize_key(value: Any) -> str:
    normalized = _normalize_text(value)
    return "" if normalized is None else normalized.replace(" ", "")


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
