"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when an issue moves to the research status.

    The automation payload can be a flat Cursor trigger context, a wrapper with a
    ``triggerContext`` object, or a nested Linear webhook payload. This function
    only builds the desired mutation; the caller is responsible for applying it
    to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    payloads = _payload_candidates(event)
    if not _is_status_change_event(payloads):
        return None

    if _normalize_words(_changed_status(payloads)) != TARGET_STATUS:
        return None

    issue_id = _first_string(payloads, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_string(payloads, ("title", "name"))
    if not issue_id or not title:
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": _prefixed_title(title),
    }


def _payload_candidates(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect useful flat and nested payload mappings in priority order."""

    candidates: list[Mapping[str, Any]] = []
    for key in ("triggerContext", "trigger_context"):
        _append_mapping(candidates, event.get(key))

    data = event.get("data")
    if isinstance(data, Mapping):
        _append_mapping(candidates, data.get("issue"))
        _append_mapping(candidates, data)

    _append_mapping(candidates, event.get("issue"))
    _append_mapping(candidates, event)
    return candidates


def _append_mapping(
    candidates: list[Mapping[str, Any]], value: Any
) -> None:
    if isinstance(value, Mapping) and value not in candidates:
        candidates.append(value)


def _is_status_change_event(payloads: list[Mapping[str, Any]]) -> bool:
    event_names = []
    for payload in payloads:
        for key in ("trigger", "webhookType", "webhook_type", "action", "type"):
            value = payload.get(key)
            if isinstance(value, str):
                event_names.append(_normalize_words(value))

    if any(name in {"status changed", "status change", "statuschanged"} for name in event_names):
        return True

    update_names = {
        "update",
        "updated",
        "issue update",
        "issue updated",
        "updated issue",
    }
    return any(name in update_names for name in event_names) and _has_status_update(payloads)


def _has_status_update(payloads: list[Mapping[str, Any]]) -> bool:
    for payload in payloads:
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
            "fields",
        ):
            if any(_is_status_field_name(field) for field in _field_names(payload.get(key))):
                return True

        for key in ("updatedFrom", "updated_from", "changes", "changed"):
            value = payload.get(key)
            if isinstance(value, Mapping) and any(
                _is_status_field_name(field) for field in value.keys()
            ):
                return True

    return False


def _changed_status(payloads: list[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "newState",
        "new_state",
        "statusName",
        "status_name",
    )
    for payload in payloads:
        value = _first_value(payload, explicit_keys)
        status = _status_name(value)
        if status:
            return status

    for payload in payloads:
        for key in ("changes", "changed"):
            value = payload.get(key)
            if not isinstance(value, Mapping):
                continue
            for field, field_change in value.items():
                if not _is_status_field_name(field):
                    continue
                status = _status_from_change(field_change)
                if status:
                    return status

    current_keys = ("status", "state", "workflowState", "workflow_state")
    for payload in payloads:
        value = _first_value(payload, current_keys)
        status = _status_name(value)
        if status:
            return status

    return None


def _status_from_change(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("new", "to", "after", "current", "value", "name"):
            status = _status_name(value.get(key))
            if status:
                return status
    return _status_name(value)


def _status_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state", "workflowState"):
            status = _status_name(value.get(key))
            if status:
                return status
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _first_string(payloads: list[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for payload in payloads:
        value = _first_value(payload, keys)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _first_value(payload: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def _field_names(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return [str(key) for key in value.keys()]
    if isinstance(value, Iterable):
        return [str(item) for item in value]
    return []


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_words(value)
    return "status" in normalized or "state" in normalized or "workflow" in normalized


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", words)


def _prefixed_title(title: str) -> str:
    if title.lower().startswith(TITLE_PREFIX.lower()):
        return title
    return f"{TITLE_PREFIX}: {title}"


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
