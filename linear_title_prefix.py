"""Build Linear issue title updates for research status transitions.

The automation runtime supplies webhook-like dictionaries. This module keeps the
decision pure so callers can apply the returned action through their Linear API
integration.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue-title update action for research status changes.

    The returned dictionary has the shape expected by the automation wrapper:
    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``.
    ``None`` means the event should be ignored.
    """

    if not isinstance(event, Mapping):
        return None

    payloads = _payloads(event)
    metadata = _merged_metadata(payloads)

    if not _is_status_change(metadata, payloads):
        return None

    new_status = _new_status(metadata, payloads)
    if _normalize_status(new_status) != TARGET_STATUS:
        return None

    issue_id = _issue_id(payloads)
    title = _issue_title(payloads)
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload mappings from outermost to innermost."""

    seen: set[int] = set()
    payloads: list[Mapping[str, Any]] = []

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        object_id = id(value)
        if object_id in seen:
            return
        seen.add(object_id)
        payloads.append(value)

        for key in ("triggerContext", "webhook", "data", "issue"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                visit(nested)

    visit(event)
    return payloads


def _merged_metadata(payloads: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Merge nested payloads first so outer event metadata has priority."""

    merged: dict[str, Any] = {}
    for payload in reversed(payloads):
        merged.update(payload)
    return merged


def _is_status_change(metadata: Mapping[str, Any], payloads: list[Mapping[str, Any]]) -> bool:
    event_words = [
        value
        for payload in payloads
        for key in ("trigger", "webhookType", "action", "type")
        if (value := payload.get(key)) is not None
    ]

    if any(_is_direct_status_change(value) for value in event_words):
        return True

    if any(_normalize_words(value) in {"issue updated", "updated issue", "update"} for value in event_words):
        return _updated_status_fields(metadata, payloads)

    return False


def _is_direct_status_change(value: Any) -> bool:
    normalized = _normalize_words(value)
    return normalized in {
        "status changed",
        "status change",
        "state changed",
        "state change",
        "workflow state changed",
        "workflow state change",
    }


def _updated_status_fields(metadata: Mapping[str, Any], payloads: list[Mapping[str, Any]]) -> bool:
    for payload in (metadata, *payloads):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = payload.get(key)
            if isinstance(fields, str):
                field_names = [fields]
            elif isinstance(fields, Mapping):
                field_names = fields.keys()
            elif isinstance(fields, list | tuple | set):
                field_names = fields
            else:
                continue

            for field in field_names:
                if _normalize_field_name(field) in STATUS_FIELDS:
                    return True

    return False


def _new_status(metadata: Mapping[str, Any], payloads: list[Mapping[str, Any]]) -> Any:
    for key in ("newStatus", "new_status", "toStatus", "to_status", "statusName", "status_name"):
        if metadata.get(key) is not None:
            return metadata[key]

    for payload in payloads:
        for key in ("newStatus", "new_status", "toStatus", "to_status", "statusName", "status_name", "status"):
            if payload.get(key) is not None:
                return payload[key]

    for payload in payloads:
        for key in ("state", "workflowState"):
            nested = payload.get(key)
            if isinstance(nested, Mapping) and nested.get("name") is not None:
                return nested["name"]

    return None


def _issue_id(payloads: list[Mapping[str, Any]]) -> str | None:
    # Prefer nested issue identifiers over outer webhook ids.
    for payload in reversed(payloads):
        for key in ("issueId", "issue_id", "identifier", "id"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _issue_title(payloads: list[Mapping[str, Any]]) -> str | None:
    for payload in reversed(payloads):
        value = payload.get("title")
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_status(value: Any) -> str:
    return _normalize_words(value)


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def _normalize_field_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _normalize_words(value))


def main() -> int:
    action = build_issue_title_update(json.load(sys.stdin))
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
