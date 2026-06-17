"""Build Linear issue-title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflow state",
    "statusid",
    "stateid",
    "workflowstateid",
    "workflow state id",
}
_DIRECT_STATUS_TRIGGERS = {"status changed", "status change", "state changed", "state change"}
_GENERIC_UPDATE_TRIGGERS = {"update", "updated", "issue update", "issue updated", "updated issue"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action when the issue enters To Research.

    The automation payload can be a flat Cursor ``triggerContext`` object or a
    nested Linear webhook payload. Non-status changes, non-target statuses, and
    already-prefixed titles return ``None``.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _extract_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(contexts, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload layers in issue-field precedence order."""

    candidates: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        candidates.append(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            candidates.append(issue)
        candidates.append(data)

    candidates.append(event)

    unique: list[Mapping[str, Any]] = []
    seen: set[int] = set()
    for candidate in candidates:
        identity = id(candidate)
        if identity not in seen:
            unique.append(candidate)
            seen.add(identity)
    return unique


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    contexts = list(contexts)
    trigger_names = {
        _normalize(context[key])
        for context in contexts
        for key in ("trigger", "webhookType", "action", "type", "eventType", "event")
        if key in context
    }

    if trigger_names & _DIRECT_STATUS_TRIGGERS:
        return True

    if not trigger_names & _GENERIC_UPDATE_TRIGGERS:
        return False

    return any(_has_status_change_marker(context) for context in contexts)


def _has_status_change_marker(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "changedFields"):
        if key in context and _field_collection_mentions_status(context[key]):
            return True

    for key in ("changes", "updatedFrom", "previousValues", "changed"):
        if key in context and _change_payload_mentions_status(context[key]):
            return True

    return False


def _field_collection_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) for key in value)
    if isinstance(value, Iterable):
        return any(_field_collection_mentions_status(item) for item in value)
    return False


def _change_payload_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Mapping):
        field_name = _first_text_from_mapping(value, ("field", "fieldName", "name", "property", "key"))
        if field_name and _is_status_field_name(field_name):
            return True
        return any(_is_status_field_name(key) for key in value)

    if isinstance(value, Iterable):
        return any(_change_payload_mentions_status(item) for item in value)

    return False


def _extract_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        explicit = _first_text_from_mapping(
            context,
            (
                "newStatus",
                "new_status",
                "newState",
                "new_state",
                "statusName",
                "stateName",
                "workflowStateName",
            ),
        )
        if explicit:
            return explicit

    for context in contexts:
        status_from_changes = _status_from_change_payloads(context)
        if status_from_changes:
            return status_from_changes

    for context in contexts:
        fallback = _first_text_from_mapping(context, ("status", "state", "workflowState"))
        if fallback:
            return fallback

    return None


def _status_from_change_payloads(context: Mapping[str, Any]) -> str | None:
    for key in ("changes", "updatedFields", "changedFields", "changed"):
        status = _extract_new_status_value(context.get(key))
        if status:
            return status
    return None


def _extract_new_status_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for field_name, field_value in value.items():
            if _is_status_field_name(field_name):
                extracted = _text_from_change_value(field_value)
                if extracted:
                    return extracted

        field_name = _first_text_from_mapping(value, ("field", "fieldName", "name", "property", "key"))
        if field_name and _is_status_field_name(field_name):
            extracted = _text_from_change_value(value)
            if extracted:
                return extracted

        for nested in value.values():
            extracted = _extract_new_status_value(nested)
            if extracted:
                return extracted

    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            extracted = _extract_new_status_value(item)
            if extracted:
                return extracted

    return None


def _text_from_change_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "new", "newValue", "after", "value", "name"):
            extracted = _text_from_change_value(value.get(key))
            if extracted:
                return extracted
        return None
    return _as_text(value)


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for key in keys:
        for context in contexts:
            value = _first_text_from_mapping(context, (key,))
            if value:
                return value
    return None


def _first_text_from_mapping(context: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        if key in context:
            value = _as_text(context[key])
            if value:
                return value
    return None


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, Mapping):
        return _first_text_from_mapping(value, ("name", "title", "label", "identifier", "id"))
    if isinstance(value, (str, int, float)):
        text = str(value).strip()
        return text or None
    return None


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize(value)
    compact = normalized.replace(" ", "")
    return normalized in _STATUS_FIELD_NAMES or compact in _STATUS_FIELD_NAMES


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize(value: Any) -> str:
    text = _as_text(value)
    if not text:
        return ""
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update:
        json.dump(update, sys.stdout, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
