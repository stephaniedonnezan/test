"""Build Linear issue title updates for Cursor research automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research.

    The automation runtime passes webhook payloads from more than one shape:
    Cursor's flattened trigger context and Linear's nested issue update payloads.
    This function keeps the integration point pure so callers can decide how to
    execute the returned update action.
    """

    if not isinstance(event, Mapping):
        return None

    sources = _collect_mappings(event)
    if not _is_status_change_event(sources):
        return None

    if _normalize(_new_status(sources)) != TARGET_STATUS:
        return None

    issue_id = _issue_id(sources)
    title = _issue_title(sources)
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


def _collect_mappings(root: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping):
            return

        value_id = id(value)
        if value_id in seen:
            return

        seen.add(value_id)
        sources.append(value)

        for key in (
            "triggerContext",
            "trigger_context",
            "payload",
            "data",
            "issue",
            "node",
            "resource",
        ):
            visit(value.get(key))

    visit(root)
    return sources


def _is_status_change_event(sources: Sequence[Mapping[str, Any]]) -> bool:
    event_keys = (
        "trigger",
        "triggerType",
        "trigger_type",
        "webhookType",
        "webhook_type",
        "action",
        "type",
        "eventType",
        "event_type",
    )

    descriptors = {
        _normalize(source[key])
        for source in sources
        for key in event_keys
        if key in source
    }

    if any(_is_status_change_descriptor(descriptor) for descriptor in descriptors):
        return True

    update_descriptors = {
        "update",
        "updated",
        "issue update",
        "issue updated",
        "updated issue",
    }
    return bool(descriptors & update_descriptors) and _updated_fields_include_status(
        sources
    )


def _is_status_change_descriptor(descriptor: str) -> bool:
    words = set(descriptor.split())
    status_word = "status" in words or "state" in words
    change_word = bool(words & {"change", "changed", "update", "updated"})
    return status_word and change_word


def _updated_fields_include_status(sources: Sequence[Mapping[str, Any]]) -> bool:
    field_keys = (
        "updatedFields",
        "updated_fields",
        "changedFields",
        "changed_fields",
        "updatedFrom",
        "updated_from",
        "changes",
    )

    for source in sources:
        for key in field_keys:
            if key in source and _contains_status_field(source[key]):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        normalized = _normalize(value)
        return (
            "status" in normalized.split()
            or normalized in {"state", "state id", "workflow state", "workflow state id"}
        )

    if isinstance(value, Mapping):
        return any(
            _contains_status_field(key) or _contains_status_field(child)
            for key, child in value.items()
        )

    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return any(_contains_status_field(item) for item in value)

    return False


def _new_status(sources: Sequence[Mapping[str, Any]]) -> str | None:
    explicit_keys = ("newStatus", "new_status", "toStatus", "to_status")
    for source in sources:
        value = _first_string(source, explicit_keys)
        if value:
            return value

    direct_keys = (
        "status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    for source in sources:
        value = _first_string(source, direct_keys)
        if value:
            return value

        for key in ("state", "workflowState", "workflow_state"):
            value = _name_or_string(source.get(key))
            if value:
                return value

    return None


def _issue_id(sources: Sequence[Mapping[str, Any]]) -> str | None:
    for source in reversed(sources):
        value = _first_string(source, ("id", "issueId", "issue_id", "identifier"))
        if value:
            return value.strip()
    return None


def _issue_title(sources: Sequence[Mapping[str, Any]]) -> str | None:
    for source in reversed(sources):
        value = _first_string(source, ("title", "name"))
        if value:
            return value
    return None


def _first_string(source: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _name_or_string(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, Mapping):
        return _first_string(value, ("name", "title"))
    return None


def _has_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(PREFIX)}\b", title, re.IGNORECASE) is not None


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = value if isinstance(value, str) else str(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
