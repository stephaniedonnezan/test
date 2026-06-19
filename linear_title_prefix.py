"""Build Linear issue title updates for research-status automations.

The automation runner supplies Linear issue webhooks in slightly different
shapes depending on the trigger source. This module keeps the behavior focused:
when an issue status changes to "to research", prefix its title with
"Cursor researching".
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow status"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when the event enters research.

    The returned action is intentionally transport-agnostic so the caller can
    decide how to apply it to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)

    if not _is_status_change_event(payload):
        return None

    status = _extract_new_status(payload)
    if _normalize_text(status) != _normalize_text(RESEARCH_STATUS):
        return None

    issue_id = _extract_first_text(payload, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _extract_first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        new_title = title
    else:
        new_title = f"{RESEARCH_PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": new_title,
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor and Linear payload containers into one lookup map."""

    payload: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if isinstance(value, Mapping):
            payload.update(value)

    data = event.get("data")
    issue = data.get("issue") if isinstance(data, Mapping) else None

    merge(issue)
    merge(data)
    merge(event.get("issue"))
    merge(event.get("triggerContext"))
    merge(event)

    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
        payload.get("eventType"),
    ]

    if any(_looks_like_status_change(value) for value in trigger_values):
        return True

    if any(_looks_like_issue_update(value) for value in trigger_values):
        return _changed_fields_include_status(payload)

    return _changed_fields_include_status(payload) and _extract_new_status(payload) is not None


def _looks_like_status_change(value: Any) -> bool:
    normalized = _normalize_text(value)
    return normalized in {
        "status changed",
        "status change",
        "statuschanged",
        "state changed",
        "workflow state changed",
    }


def _looks_like_issue_update(value: Any) -> bool:
    normalized = _normalize_text(value)
    return normalized in {
        "update",
        "updated",
        "issue update",
        "issue updated",
        "updated issue",
    }


def _changed_fields_include_status(payload: Mapping[str, Any]) -> bool:
    changed_sources = (
        payload.get("updatedFields"),
        payload.get("updated_fields"),
        payload.get("changedFields"),
        payload.get("changed_fields"),
        payload.get("changes"),
    )

    for source in changed_sources:
        if _source_mentions_status(source):
            return True

    return False


def _source_mentions_status(source: Any) -> bool:
    if source is None:
        return False

    if isinstance(source, str):
        return _normalize_field_name(source) in STATUS_FIELDS

    if isinstance(source, Mapping):
        return any(_normalize_field_name(key) in STATUS_FIELDS for key in source.keys())

    if isinstance(source, list | tuple | set):
        return any(_source_mentions_status(item) for item in source)

    return False


def _extract_new_status(payload: Mapping[str, Any]) -> str | None:
    direct_status = _extract_first_text(
        payload,
        (
            "newStatus",
            "new_status",
            "status",
            "state",
            "workflowState",
            "workflow_state",
        ),
    )
    if direct_status:
        return direct_status

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        for field_name, value in changes.items():
            if _normalize_field_name(field_name) in STATUS_FIELDS:
                changed_status = _extract_changed_value(value)
                if changed_status:
                    return changed_status

    return None


def _extract_changed_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _extract_first_text(
            value,
            ("newValue", "new_value", "to", "after", "name", "value"),
        )

    if isinstance(value, str):
        return value

    return None


def _extract_first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value

        if isinstance(value, Mapping):
            nested = _extract_first_text(value, ("name", "title", "id", "identifier", "key"))
            if nested:
                return nested

    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(RESEARCH_PREFIX.casefold())


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-/]+", " ", text)
    return re.sub(r"\s+", " ", text).casefold()


def _normalize_field_name(value: Any) -> str:
    return _normalize_text(value).replace(" ", "")


def main() -> int:
    """Read an event JSON object from stdin and print the resulting action."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
