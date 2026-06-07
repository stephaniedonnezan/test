"""Build Linear issue title updates for Cursor research automation.

The automation platform calls into this module with a Linear issue webhook
payload. When an issue moves to "to research", the handler returns the title
update that should be sent back to Linear.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_SPACE_RE = re.compile(r"\s+")
_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}
_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_ISSUE_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action for research status changes.

    The return value is intentionally side-effect free so callers can decide how
    to apply the update:

    {"action": "update_issue_title", "issueId": "POI-123", "title": "..."}
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_context_candidates(event))
    if not _is_status_change_event(contexts):
        return None

    status = _extract_new_status(contexts)
    if _normalize(status) != RESEARCH_STATUS:
        return None

    issue_id = _extract_issue_id(contexts)
    title = _extract_title(contexts)
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _context_candidates(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely metadata and issue objects from flat or nested webhooks."""

    yielded: list[int] = []

    def add(value: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(value, Mapping):
            marker = id(value)
            if marker not in yielded:
                yielded.append(marker)
                yield value

    yield from add(event.get("triggerContext"))
    data = event.get("data")
    if isinstance(data, Mapping):
        yield from add(data.get("issue"))
    yield from add(event.get("issue"))
    yield from add(data)
    yield from add(event)


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    contexts = list(contexts)
    event_names = {
        normalized
        for context in contexts
        for key in ("trigger", "eventType", "type", "action", "webhookType")
        if (normalized := _normalize(context.get(key)))
    }

    if event_names & _STATUS_CHANGE_EVENTS:
        return True

    if event_names & _ISSUE_UPDATE_EVENTS:
        return _changed_status_fields(contexts)

    return _changed_status_fields(contexts)


def _changed_status_fields(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
            "changedProperties",
            "changed_properties",
        ):
            if _contains_status_field(context.get(key)):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            if any(_normalize(field) in _STATUS_FIELD_NAMES for field in changes):
                return True
        elif isinstance(changes, list):
            for change in changes:
                if isinstance(change, Mapping):
                    if _contains_status_field(
                        change.get("field")
                        or change.get("fieldName")
                        or change.get("name")
                        or change.get("key")
                    ):
                        return True
                elif _contains_status_field(change):
                    return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(_contains_status_field(item) for item in value.values())

    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)

    return False


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    contexts = list(contexts)
    explicit_status_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "toStatus",
        "to_status",
        "toState",
        "to_state",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
    )
    fallback_status_keys = ("status", "state", "workflowState", "workflow_state")

    for key in explicit_status_keys:
        if status := _first_string_value(contexts, key):
            return status

    for key in fallback_status_keys:
        if status := _first_string_value(contexts, key):
            return status

    return None


def _extract_issue_id(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    return _first_string_value(
        contexts,
        "issueId",
        "issue_id",
        "identifier",
        "key",
        "id",
    )


def _extract_title(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    return _first_string_value(contexts, "title", "name")


def _first_string_value(
    contexts: Iterable[Mapping[str, Any]],
    *keys: str,
) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            extracted = _string_from_value(value)
            if extracted:
                return extracted
    return None


def _string_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "id", "identifier"):
            extracted = _string_from_value(value.get(key))
            if extracted:
                return extracted

    return None


def _has_research_prefix(title: str) -> bool:
    return title.lstrip().lower().startswith(TITLE_PREFIX.lower())


def _normalize(value: Any) -> str:
    text = _string_from_value(value)
    if not text:
        return ""

    text = _CAMEL_BOUNDARY.sub(" ", text)
    text = re.sub(r"[_\-.]+", " ", text)
    return _SPACE_RE.sub(" ", text).strip().lower()


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
