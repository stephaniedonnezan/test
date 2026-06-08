"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status change",
    "status changed",
    "status update",
    "status updated",
    "state change",
    "state changed",
    "state update",
    "state updated",
    "workflow state change",
    "workflow state changed",
    "workflow state update",
    "workflow state updated",
}
_ISSUE_UPDATE_EVENTS = {
    "issue update",
    "issue updated",
    "update",
    "updated",
    "updated issue",
}
_STATUS_FIELD_NAMES = {
    "status",
    "status id",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
    "workflowstate",
    "workflowstate id",
}
_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_PREFIX_PATTERN = re.compile(
    rf"^\s*{re.escape(TITLE_PREFIX)}(?:(?:\s*[-:]\s*)|\s+|$)",
    flags=re.IGNORECASE,
)


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title-update action for issues moved to to research.

    The function intentionally has no side effects. Automation runners can pass
    the returned action to their Linear client, while unrelated or malformed
    payloads return ``None``.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _context_maps(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _issue_status(contexts)
    if _normalize(new_status) != _normalize(TARGET_STATUS):
        return None

    issue_title = _first_text(contexts, ("title", "name"))
    issue_id = _first_text(contexts, ("issueId", "issue_id", "id", "identifier"))
    if not issue_title or not issue_id:
        return None

    updated_title = with_researching_prefix(issue_title)
    if updated_title == issue_title:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": updated_title,
    }


def update_issue_title_for_status(title: str, new_status: str) -> str:
    """Return ``title`` prefixed when ``new_status`` is to research."""

    if _normalize(new_status) != _normalize(TARGET_STATUS):
        return title
    return with_researching_prefix(title)


def derive_updated_title(payload: Mapping[str, Any]) -> str | None:
    """Return the prefixed title from an automation payload, if needed."""

    if not isinstance(payload, Mapping):
        return None

    contexts = _context_maps(payload)
    title = _first_text(contexts, ("title", "name"))
    new_status = _issue_status(contexts)
    if not title or _normalize(new_status) != _normalize(TARGET_STATUS):
        return None

    updated_title = with_researching_prefix(title)
    if updated_title == title:
        return None
    return updated_title


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility wrapper for status-change automation handlers."""

    return build_issue_title_update(event)


def with_researching_prefix(title: str) -> str:
    """Add the research prefix to ``title`` without duplicating it."""

    if has_research_prefix(title):
        return title

    clean_title = title.strip()
    if not clean_title:
        return TITLE_PREFIX
    return f"{TITLE_PREFIX}: {clean_title}"


def prefix_issue_title(title: str) -> str:
    """Compatibility wrapper for prefixing a Linear issue title."""

    return with_researching_prefix(title)


def has_research_prefix(title: str) -> bool:
    """Return whether ``title`` already starts with the research prefix."""

    return bool(_PREFIX_PATTERN.match(title))


def _context_maps(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload contexts ordered from issue-specific to global."""

    trigger_context = _as_mapping(event.get("triggerContext"))
    data = _as_mapping(event.get("data"))
    issue = _as_mapping(event.get("issue"))

    for container in (trigger_context, data):
        nested_issue = _as_mapping(container.get("issue")) if container else None
        if nested_issue:
            issue = nested_issue
            break

    contexts: list[Mapping[str, Any]] = []
    for candidate in (issue, data, trigger_context, event):
        if candidate and candidate not in contexts:
            contexts.append(candidate)
    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    if _first_text(contexts, _STATUS_KEYS):
        return True

    event_values = []
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type", "event"):
            value = context.get(key)
            if isinstance(value, str):
                event_values.append(_normalize(value))

    if any(value in _DIRECT_STATUS_CHANGE_EVENTS for value in event_values):
        return True

    if any(value in _ISSUE_UPDATE_EVENTS for value in event_values):
        return _updated_fields_include_status(contexts)

    return False


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        raw_fields = (
            context.get("updatedFields")
            or context.get("updated_fields")
            or context.get("changedFields")
            or context.get("changed_fields")
        )
        if isinstance(raw_fields, str):
            fields = [raw_fields]
        elif isinstance(raw_fields, (list, tuple, set)):
            fields = raw_fields
        else:
            continue

        for field in fields:
            if isinstance(field, Mapping):
                field_name = _first_text([field], ("field", "name", "key", "id"))
            else:
                field_name = str(field)
            if _normalize(field_name) in _STATUS_FIELD_NAMES:
                return True

    return False


def _issue_status(contexts: list[Mapping[str, Any]]) -> str | None:
    direct_status = _first_text(contexts, _STATUS_KEYS)
    if direct_status:
        return direct_status

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = context.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, Mapping):
                name = _first_text([value], ("name", "title"))
                if name:
                    return name

    return None


def _first_text(
    contexts: list[Mapping[str, Any]],
    keys: tuple[str, ...],
) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    """Read a JSON payload from stdin and print the title-update action."""

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
