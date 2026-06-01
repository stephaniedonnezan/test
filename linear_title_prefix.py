"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when an issue moves to To Research.

    The automation trigger payload used by Cursor is flat inside
    ``triggerContext``. Linear webhooks can also wrap issue data under
    ``data``/``issue`` and represent status as ``state`` or ``workflowState``.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _primary_payload(event)
    if not _is_status_change_event(event):
        return None

    new_status = _new_status(event, payload)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, "issueId", "issue_id", "identifier", "id")
    title = _first_text(payload, "title", "name")
    if not issue_id or not title:
        return None

    cleaned_title = title.strip()
    if _has_prefix(cleaned_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {cleaned_title}",
    }


def _primary_payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    """Merge common Linear wrapper objects with nested issue fields prioritized."""

    merged: dict[str, Any] = dict(event)
    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            merged.update(value)
            nested_data = value.get("data")
            if isinstance(nested_data, Mapping):
                merged.update(nested_data)
            nested_issue = value.get("issue")
            if isinstance(nested_issue, Mapping):
                merged.update(nested_issue)
    return merged


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    payload = _primary_payload(event)
    for source in (event, _mapping(event.get("triggerContext")), payload):
        for key in ("trigger", "event", "action", "type", "webhookType"):
            normalized = _normalize_words(source.get(key))
            if normalized in {"status changed", "status change", "state changed"}:
                return True
            if normalized in {"issue updated", "updated issue", "update"}:
                return _updated_fields_include_status(event, payload)

    return _updated_fields_include_status(event, payload)


def _updated_fields_include_status(
    event: Mapping[str, Any], payload: Mapping[str, Any]
) -> bool:
    for source in (event, _mapping(event.get("triggerContext")), payload):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = source.get(key)
            if isinstance(fields, str):
                candidates = [fields]
            elif isinstance(fields, (list, tuple, set)):
                candidates = fields
            else:
                continue

            for field in candidates:
                if _normalize_words(field) in {"status", "state", "workflow state"}:
                    return True

    return False


def _new_status(event: Mapping[str, Any], payload: Mapping[str, Any]) -> str | None:
    for source in (event, _mapping(event.get("triggerContext")), payload):
        explicit = _first_text(
            source,
            "newStatus",
            "new_status",
            "status",
            "statusName",
            "stateName",
            "workflowStateName",
        )
        if explicit:
            return explicit

    for source in (event, _mapping(event.get("triggerContext")), payload):
        for key in ("state", "workflowState", "status"):
            value = source.get(key)
            if isinstance(value, Mapping):
                nested_name = _first_text(value, "name", "title")
                if nested_name:
                    return nested_name

    return None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _first_text(source: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
