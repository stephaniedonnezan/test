"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = frozenset({"status", "state", "workflowstate", "workflow_state"})


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update when a Linear issue moves to the research status.

    The automation trigger can provide either a flat Cursor ``triggerContext``
    payload or a nested Linear webhook payload. This function avoids depending on
    a single exact shape and instead extracts the relevant issue metadata from
    the known locations.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _payload(event)
    issue = _issue(payload)

    if not _is_status_change(payload):
        return None

    if _normalize_status(_new_status(payload)) != TARGET_STATUS:
        return None

    issue_id = _first_text(issue, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(issue, ("title", "name"))

    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context
    return event


def _issue(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    data = payload.get("data")
    if isinstance(data, Mapping):
        nested_issue = data.get("issue")
        if isinstance(nested_issue, Mapping):
            return _merged(payload, data, nested_issue)

        return _merged(payload, data)

    issue = payload.get("issue")
    if isinstance(issue, Mapping):
        return _merged(payload, issue)

    return payload


def _merged(*items: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for item in items:
        merged.update(item)
    return merged


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    if any(_is_direct_status_change(value) for value in _event_names(payload)):
        return True

    if any(_normalize_event_name(value) in {"update", "updated issue", "issue updated"} for value in _event_names(payload)):
        return _mentions_status_field(payload)

    return False


def _event_names(payload: Mapping[str, Any]) -> Iterable[Any]:
    for mapping in _relevant_mappings(payload):
        for key in ("trigger", "webhookType", "webhook_type", "action", "type"):
            if key in mapping:
                yield mapping[key]


def _is_direct_status_change(value: Any) -> bool:
    normalized = _normalize_event_name(value)
    return normalized in {
        "status changed",
        "status change",
        "state changed",
        "workflow state changed",
    }


def _mentions_status_field(payload: Mapping[str, Any]) -> bool:
    for mapping in _relevant_mappings(payload):
        for key in ("updatedFields", "updated_fields"):
            fields = mapping.get(key)
            if _field_list_mentions_status(fields):
                return True

        changes = mapping.get("changes")
        if isinstance(changes, Mapping) and any(_is_status_field(key) for key in changes):
            return True

    return False


def _field_list_mentions_status(fields: Any) -> bool:
    if isinstance(fields, str):
        return _is_status_field(fields)

    if isinstance(fields, Iterable) and not isinstance(fields, (bytes, bytearray, str, Mapping)):
        return any(_is_status_field(field) for field in fields)

    return False


def _is_status_field(value: Any) -> bool:
    normalized = _normalize_key(value)
    return normalized in STATUS_FIELDS


def _new_status(payload: Mapping[str, Any]) -> Any:
    for mapping in _relevant_mappings(payload):
        status = _first_value(
            mapping,
            (
                "newStatus",
                "new_status",
                "status",
                "state",
                "workflowState",
                "workflow_state",
            ),
        )
        if status is not None:
            return status

        changes = mapping.get("changes")
        if isinstance(changes, Mapping):
            for key in ("status", "state", "workflowState", "workflow_state"):
                change = changes.get(key)
                if isinstance(change, Mapping):
                    status = _first_value(change, ("newValue", "new_value", "to", "after", "name"))
                    if status is not None:
                        return status
                elif change is not None:
                    return change

    return None


def _relevant_mappings(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    mappings: list[Mapping[str, Any]] = [payload]

    trigger_context = payload.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        mappings.append(trigger_context)

    data = payload.get("data")
    if isinstance(data, Mapping):
        mappings.append(data)
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            mappings.append(issue)

    issue = payload.get("issue")
    if isinstance(issue, Mapping):
        mappings.append(issue)

    return mappings


def _first_value(mapping: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            return value
    return None


def _first_text(mapping: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    value = _first_value(mapping, keys)
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _normalize_status(value: Any) -> str:
    if isinstance(value, Mapping):
        nested = _first_value(value, ("name", "status", "state", "title"))
        if nested is not None:
            return _normalize_status(nested)

    return _normalize_text(value)


def _normalize_event_name(value: Any) -> str:
    if isinstance(value, Mapping):
        nested = _first_value(value, ("name", "type", "action"))
        if nested is not None:
            return _normalize_event_name(nested)

    return _normalize_text(value)


def _normalize_key(value: Any) -> str:
    return _normalize_text(value).replace(" ", "")


def _normalize_text(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def _has_prefix(title: str) -> bool:
    return title.strip().lower().startswith(PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
