"""Build title updates for Linear issues entering research.

The automation receives slightly different payload shapes depending on whether
the event comes from Cursor's trigger context or directly from Linear.  This
module keeps the behavior small and testable: return an update action when an
issue status changes to "to research", otherwise return ``None``.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate"}
DIRECT_STATUS_CHANGE_EVENTS = {"statuschanged", "statuschange", "status_changed"}
GENERIC_UPDATE_EVENTS = {"update", "updated", "issueupdated", "updatedissue"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters research.

    The returned dictionary is intentionally transport-agnostic so the caller can
    apply the update through whatever Linear client the automation uses.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _first_status(contexts)
    if _normalize_for_compare(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_issue_id(contexts)
    title = _first_title(contexts)
    if issue_id is None or title is None:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload fragments from most-specific to broadest."""

    contexts: list[Mapping[str, Any]] = []

    trigger_context = _mapping(event.get("triggerContext"))
    data = _mapping(event.get("data"))
    issue = _mapping(event.get("issue"))
    data_issue = _mapping(data.get("issue"))
    webhook_issue = _mapping(event.get("webhook", {})).get("issue")
    webhook_issue_mapping = _mapping(webhook_issue)

    for candidate in (
        trigger_context,
        data_issue,
        issue,
        data,
        webhook_issue_mapping,
        event,
    ):
        if candidate and not any(candidate is existing for existing in contexts):
            contexts.append(candidate)

    return contexts


def _is_status_change_event(contexts: Sequence[Mapping[str, Any]]) -> bool:
    event_names = {
        _normalize_token(value)
        for context in contexts
        for key in ("trigger", "webhookType", "action", "type")
        for value in (context.get(key),)
        if isinstance(value, str)
    }

    if event_names & DIRECT_STATUS_CHANGE_EVENTS:
        return True

    if event_names & GENERIC_UPDATE_EVENTS:
        return _has_status_update_marker(contexts)

    return False


def _has_status_update_marker(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        updated_fields = context.get("updatedFields")
        if _sequence_mentions_status(updated_fields):
            return True

        for key in ("changes", "changed", "updatedFrom", "updated"):
            if _mapping_mentions_status(context.get(key)):
                return True

    return False


def _sequence_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _field_name_is_status(value)

    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        return False

    return any(_field_name_is_status(item) for item in value if isinstance(item, str))


def _mapping_mentions_status(value: Any) -> bool:
    mapping = _mapping(value)
    if not mapping:
        return False

    return any(_field_name_is_status(str(key)) for key in mapping.keys())


def _field_name_is_status(value: str) -> bool:
    return _normalize_token(value) in STATUS_FIELD_NAMES


def _first_status(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    for key in ("newStatus", "new_status", "toStatus", "to_status", "statusName", "stateName"):
        value = _first_string(contexts, key)
        if value is not None:
            return value

    for key in ("status", "state", "workflowState"):
        value = _first_string_or_name(contexts, key)
        if value is not None:
            return value

    return None


def _first_issue_id(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    for key in ("identifier", "key", "issueId", "issue_id", "id"):
        value = _first_string(contexts, key)
        if value is not None:
            return value
    return None


def _first_title(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    return _first_string(contexts, "title")


def _first_string(contexts: Sequence[Mapping[str, Any]], key: str) -> str | None:
    for context in contexts:
        value = context.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _first_string_or_name(contexts: Sequence[Mapping[str, Any]], key: str) -> str | None:
    for context in contexts:
        value = context.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped

        named_value = _mapping(value).get("name")
        if isinstance(named_value, str):
            stripped = named_value.strip()
            if stripped:
                return stripped

    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _normalize_for_compare(value: str | None) -> str:
    if value is None:
        return ""

    with_spaces = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", with_spaces).strip().casefold()
    return re.sub(r"\s+", " ", normalized)


def _normalize_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", value).casefold()


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
