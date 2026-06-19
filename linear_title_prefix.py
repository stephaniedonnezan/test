"""Build Linear issue-title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "statuschange",
    "statuschanged",
    "statechange",
    "statechanged",
    "workflowstatechange",
    "workflowstatechanged",
}
_UPDATE_EVENTS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}
_STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    Cursor automation payloads place issue details under ``triggerContext``.
    Linear webhooks are often nested under ``data.issue``. Accept both shapes so
    the title prefixing rule is tied to the status transition, not the transport.
    """

    if not isinstance(event, Mapping):
        return None

    mappings = list(_iter_mappings(event))
    if not _is_status_change_event(mappings):
        return None

    new_status = _extract_new_status(mappings)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(mappings, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(mappings, ("title",))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if not stripped_title or _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Compatibility alias for JavaScript-style automation naming."""

    return build_issue_title_update(event)


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for key in (
            "triggerContext",
            "payload",
            "data",
            "issue",
            "node",
            "object",
            "resource",
            "webhook",
            "status",
            "state",
            "workflowState",
        ):
            if key in value:
                yield from _iter_mappings(value[key])
        return

    if isinstance(value, list):
        for item in value:
            yield from _iter_mappings(item)


def _is_status_change_event(mappings: list[Mapping[str, Any]]) -> bool:
    event_keys = (
        "trigger",
        "event",
        "eventType",
        "webhookType",
        "action",
        "type",
    )

    event_names = {
        _normalize_compact(_text_from_value(mapping.get(key)))
        for mapping in mappings
        for key in event_keys
        if key in mapping
    }
    event_names.discard("")

    if event_names & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    if event_names & _UPDATE_EVENTS:
        return _updated_fields_include_status(mappings)

    # Test and fixture payloads sometimes include only the changed status.
    return not event_names and any(
        _first_text([mapping], ("newStatus", "new_status", "toStatus", "to_status"))
        for mapping in mappings
    )


def _updated_fields_include_status(mappings: list[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        for key in ("updatedFields", "changedFields", "changes", "changed", "field"):
            if key in mapping and _contains_status_field(mapping[key]):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_compact(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        if any(_normalize_compact(key) in _STATUS_FIELD_NAMES for key in value):
            return True
        for key in ("field", "fieldName", "name", "key", "id"):
            if key in value and _contains_status_field(value[key]):
                return True
        return any(_contains_status_field(item) for item in value.values())

    if isinstance(value, list):
        return any(_contains_status_field(item) for item in value)

    return False


def _extract_new_status(mappings: list[Mapping[str, Any]]) -> str:
    direct_status = _first_text(
        mappings,
        (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "statusName",
            "stateName",
            "workflowStateName",
        ),
    )
    if direct_status:
        return direct_status

    for mapping in mappings:
        for key in ("status", "state", "workflowState"):
            if key in mapping:
                status = _text_from_value(mapping[key])
                if status:
                    return status

    return ""


def _first_text(mappings: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str:
    for mapping in mappings:
        for key in keys:
            if key in mapping:
                text = _text_from_value(mapping[key])
                if text:
                    return text
    return ""


def _text_from_value(value: Any) -> str:
    if isinstance(value, str):
        return value

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, Mapping):
        for key in ("name", "title", "displayName", "identifier", "key", "id"):
            if key in value:
                text = _text_from_value(value[key])
                if text:
                    return text

    return ""


def _normalize_words(value: str) -> str:
    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    separated = re.sub(r"[^A-Za-z0-9]+", " ", separated)
    return " ".join(separated.casefold().split())


def _normalize_compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _normalize_words(value))


def _has_research_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(TITLE_PREFIX)}\b", title, re.IGNORECASE) is not None


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
