"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflowstatus"}
STATUS_CHANGE_EVENTS = {"status changed", "status change", "statuschanged"}
ISSUE_UPDATE_EVENTS = {"issue updated", "updated issue", "update", "updated"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    context = _merge_context(event)
    if not _is_status_change(context):
        return None

    new_status = _first_text(
        _deep_get(context, "newStatus"),
        _deep_get(context, "new_status"),
        _deep_get(context, "toStatus"),
        _deep_get(context, "to_status"),
        _deep_get(context, "issue.status.name"),
        _deep_get(context, "issue.state.name"),
        _deep_get(context, "issue.workflowState.name"),
        _deep_get(context, "issue.workflow_state.name"),
        _deep_get(context, "status.name"),
        _deep_get(context, "state.name"),
        _deep_get(context, "workflowState.name"),
        _deep_get(context, "workflow_state.name"),
        _deep_get(context, "status"),
        _deep_get(context, "state"),
        _deep_get(context, "workflowState"),
    )
    if _normalize_text(new_status) != _normalize_text(RESEARCH_STATUS):
        return None

    issue_id = _first_text(
        _deep_get(context, "issue.id"),
        _deep_get(context, "id"),
        _deep_get(context, "issueId"),
        _deep_get(context, "issue_id"),
        _deep_get(context, "identifier"),
    )
    title = _first_text(_deep_get(context, "issue.title"), _deep_get(context, "title"))
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


def _merge_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common automation and Linear webhook wrappers into one context."""

    sources = list(_context_sources(event))
    context: dict[str, Any] = {}
    for source in sources:
        context.update(source)

    issue = _first_mapping(_deep_get(source, "issue") for source in sources)
    if issue is not None:
        context["issue"] = issue

    return context


def _context_sources(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    yield event

    for key in ("automation_trigger_info", "automationTriggerInfo", "triggerInfo"):
        wrapper = event.get(key)
        if isinstance(wrapper, Mapping):
            yield wrapper
            yield from _context_sources(wrapper)

    for key in ("data", "issue", "triggerContext", "webhook"):
        value = event.get(key)
        if isinstance(value, Mapping):
            yield value


def _first_mapping(values: Iterable[Any]) -> Mapping[str, Any] | None:
    for value in values:
        if isinstance(value, Mapping):
            return value
    return None


def _is_status_change(context: Mapping[str, Any]) -> bool:
    event_names = [
        value
        for key in ("trigger", "webhookType", "action", "type")
        if (value := _deep_get(context, key)) is not None
    ]
    normalized_events = {_normalize_text(value) for value in event_names}

    if any(name in STATUS_CHANGE_EVENTS for name in normalized_events):
        return True

    if any(name in ISSUE_UPDATE_EVENTS for name in normalized_events):
        fields = _updated_fields(context)
        return not fields or any(field in STATUS_FIELDS for field in fields)

    return False


def _updated_fields(context: Mapping[str, Any]) -> set[str]:
    raw_fields = (
        _deep_get(context, "updatedFields")
        or _deep_get(context, "updated_fields")
        or _deep_get(context, "updatedFrom")
        or _deep_get(context, "updated_from")
    )
    if raw_fields is None:
        return set()

    values: Iterable[Any]
    if isinstance(raw_fields, str):
        values = re.split(r"[,;\s]+", raw_fields)
    elif isinstance(raw_fields, Mapping):
        values = raw_fields.keys()
    elif isinstance(raw_fields, Iterable):
        values = raw_fields
    else:
        return set()

    return {_normalize_field_name(value) for value in values if _first_text(value)}


def _deep_get(mapping: Mapping[str, Any], path: str) -> Any:
    current: Any = mapping
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _first_text(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, Mapping):
            nested = _first_text(value.get("name"), value.get("title"), value.get("id"))
            if nested:
                return nested
    return None


def _normalize_text(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[_\-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _normalize_field_name(value: Any) -> str:
    return _normalize_text(value).replace(" ", "")


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
