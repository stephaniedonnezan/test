"""Build Linear issue title updates for Cursor research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "targetStatus",
    "target_status",
    "newState",
    "new_state",
    "toState",
    "to_state",
)
_ISSUE_ID_KEYS = ("id", "issueId", "issue_id", "identifier")
_ISSUE_TITLE_KEYS = ("title", "name")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action for status changes to "to research".

    The automation payloads used for Linear can arrive either as a flat trigger
    context or as a nested webhook payload. This function keeps the public
    output small and side-effect free so callers can apply the update with their
    Linear client of choice.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_new_status(event)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_issue_title(event)
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title.strip()}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    metadata_sources = _metadata_sources(event)

    for source in metadata_sources:
        for key in ("trigger", "webhookType", "event", "eventType", "action", "type"):
            marker = _normalize_text(source.get(key))
            if marker in {
                "status changed",
                "status change",
                "status updated",
                "issue status changed",
                "issue status change",
                "state changed",
                "workflow state changed",
            }:
                return True

            if marker in {"update", "updated", "issue updated", "updated issue"}:
                if _has_updated_status_field(event):
                    return True

    return _has_updated_status_field(event)


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for source in _status_sources(event):
        for key in _EXPLICIT_STATUS_KEYS:
            value = _extract_named_value(source.get(key))
            if value:
                return value

    for source in _issue_sources(event) + _status_sources(event):
        for key in ("state", "workflowState", "workflow_state", "status"):
            value = _extract_named_value(source.get(key))
            if value:
                return value

    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for source in _issue_sources(event):
        for key in _ISSUE_ID_KEYS:
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, int):
                return str(value)
    return None


def _extract_issue_title(event: Mapping[str, Any]) -> str | None:
    for source in _issue_sources(event):
        for key in _ISSUE_TITLE_KEYS:
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _metadata_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        source
        for source in (
            event,
            _mapping_at(event, "triggerContext"),
            _mapping_at(event, "payload"),
            _mapping_at(event, "webhook"),
            _mapping_at(event, "data"),
        )
        if source is not None
    ]


def _status_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    trigger_context = _mapping_at(event, "triggerContext")
    payload = _mapping_at(event, "payload")
    data = _mapping_at(event, "data")
    issue = _mapping_at(data, "issue") if data is not None else None
    payload_issue = _mapping_at(payload, "issue") if payload is not None else None

    return [
        source
        for source in (
            event,
            trigger_context,
            payload,
            data,
            issue,
            payload_issue,
        )
        if source is not None
    ]


def _issue_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    trigger_context = _mapping_at(event, "triggerContext")
    payload = _mapping_at(event, "payload")
    data = _mapping_at(event, "data")
    issue = _mapping_at(data, "issue") if data is not None else None
    payload_issue = _mapping_at(payload, "issue") if payload is not None else None

    return [
        source
        for source in (
            issue,
            payload_issue,
            data,
            trigger_context,
            payload,
            event,
        )
        if source is not None
    ]


def _mapping_at(source: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if source is None:
        return None
    value = source.get(key)
    return value if isinstance(value, Mapping) else None


def _extract_named_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state"):
            nested = _extract_named_value(value.get(key))
            if nested:
                return nested
    return None


def _has_updated_status_field(event: Mapping[str, Any]) -> bool:
    for source in _metadata_sources(event) + _status_sources(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = source.get(key)
            if _contains_status_field(fields):
                return True

        updated_from = source.get("updatedFrom")
        if isinstance(updated_from, Mapping):
            for key in updated_from:
                if _is_status_field_key(key):
                    return True

    return False


def _contains_status_field(fields: Any) -> bool:
    if isinstance(fields, str):
        return _is_status_field_key(fields)

    if isinstance(fields, Mapping):
        return any(_is_status_field_key(key) for key in fields)

    if isinstance(fields, list | tuple | set):
        return any(_contains_status_field(field) for field in fields)

    return False


def _is_status_field_key(key: Any) -> bool:
    if not isinstance(key, str):
        return False
    normalized = re.sub(r"[^a-z0-9]", "", key.lower())
    return normalized in {"status", "state", "workflowstate", "stateid", "workflowstateid"}


def _has_research_prefix(title: str) -> bool:
    return title.strip().lower().startswith(TITLE_PREFIX.lower())


def _normalize_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    with_word_boundaries = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    words_only = re.sub(r"[^A-Za-z0-9]+", " ", with_word_boundaries)
    normalized = re.sub(r"\s+", " ", words_only).strip().lower()
    return normalized or None


def main() -> int:
    """Read a JSON payload from stdin and print the title update action, if any."""

    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
