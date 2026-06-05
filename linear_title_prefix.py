"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_CHANGE_NAMES = {"status changed", "status change"}
_UPDATE_EVENT_NAMES = {"update", "updated", "issue updated", "updated issue"}
_STATUS_FIELD_NAMES = {
    "status",
    "status id",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action for status changes to "to research"."""
    if not isinstance(event, Mapping):
        return None

    contexts = list(_iter_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    status = _find_status(contexts)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _find_string(contexts, ("id", "issueId", "issue_id", "identifier", "key"))
    title = _find_string(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _iter_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely metadata and issue containers from outermost to innermost."""
    yield event

    trigger_context = _mapping_value(event.get("triggerContext"))
    if trigger_context:
        yield trigger_context

    data = _mapping_value(event.get("data"))
    if data:
        yield data

    for container in (event, trigger_context, data):
        if not container:
            continue
        issue = _mapping_value(container.get("issue"))
        if issue:
            yield issue


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    event_names = {
        normalized
        for context in contexts
        for key in ("trigger", "webhookType", "webhook_type", "action", "type")
        if (normalized := _normalize_text(_string_value(context.get(key))))
    }

    if event_names & _STATUS_CHANGE_NAMES:
        return True

    if event_names & _UPDATE_EVENT_NAMES:
        return _has_status_field_change(contexts)

    return _has_status_field_change(contexts)


def _has_status_field_change(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
            "changes",
            "changed",
            "updatedFrom",
            "updated_from",
        ):
            if _contains_status_field(context.get(key)):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if _normalize_field_name(_string_value(key)) in _STATUS_FIELD_NAMES:
                return True
            if key in {"field", "name", "key"} and _contains_status_field(nested_value):
                return True
        return False

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _find_status(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "toStatus",
        "to_status",
        "status",
    )
    for key in explicit_keys:
        value = _find_status_value(contexts, key)
        if value:
            return value

    for key in ("state", "workflowState", "workflow_state"):
        value = _find_status_value(contexts, key)
        if value:
            return value

    return None


def _find_status_value(contexts: list[Mapping[str, Any]], key: str) -> str | None:
    for context in contexts:
        if key not in context:
            continue
        value = _status_string(context.get(key))
        if value:
            return value
    return None


def _status_string(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None

    mapping = _mapping_value(value)
    if mapping:
        return _find_string([mapping], ("name", "title", "status", "state"))

    return None


def _find_string(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _string_value(context.get(key))
            if value:
                return value
    return None


def _mapping_value(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _normalize_field_name(value: str | None) -> str:
    normalized = _normalize_text(value)
    if normalized.endswith("id") and normalized not in {"id", "issue id"}:
        normalized = f"{normalized[:-2].rstrip()} id"
    return normalized


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", words)
    return re.sub(r"\s+", " ", words).strip().lower()


def main() -> int:
    payload = json.load(sys.stdin)
    result = build_issue_title_update(payload)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
