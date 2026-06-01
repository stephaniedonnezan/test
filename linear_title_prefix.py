"""Build Linear issue title updates for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowState", "workflow_state"}
UPDATED_FIELD_NAMES = STATUS_FIELDS | {"statusId", "stateId", "workflowStateId"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to to research."""

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize_text(_first_status_value(event)) != TARGET_STATUS:
        return None

    issue_id = _first_text(_issue_sources(event), ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(_issue_sources(event), ("title", "name"))
    if issue_id is None or title is None:
        return None

    title = title.strip()
    if not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    for value in _metadata_values(event, ("trigger", "webhookType", "action", "type", "event")):
        normalized = _normalize_text(value)
        if normalized in {"status changed", "status change", "state changed", "workflow state changed"}:
            return True

    update_action = any(
        _normalize_text(value) in {"update", "updated", "issue updated", "updated issue"}
        for value in _metadata_values(event, ("action", "type", "trigger", "event"))
    )
    return update_action and _updated_fields_include_status(event)


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for value in _metadata_values(event, ("updatedFields", "updated_fields", "changedFields", "changed_fields")):
        if any(_normalize_field_name(field) in _normalized_updated_fields() for field in _as_iterable(value)):
            return True

    for value in _metadata_values(event, ("updatedFrom", "updated_from", "previousValues", "previous_values")):
        if isinstance(value, Mapping) and any(
            _normalize_field_name(field) in _normalized_updated_fields() for field in value
        ):
            return True

    return False


def _first_status_value(event: Mapping[str, Any]) -> Any:
    sources = _payload_sources(event)
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "toStatus",
        "to_status",
        "statusName",
        "stateName",
        "workflowStateName",
    )

    value = _first_value(sources, explicit_keys)
    if value is not None:
        return value

    for source in sources:
        for key in STATUS_FIELDS:
            value = _extract_value(source.get(key) if isinstance(source, Mapping) else None)
            if value is not None:
                return value

    return None


def _payload_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _dedupe_mappings(
        (
            event,
            event.get("triggerContext"),
            event.get("data"),
            event.get("issue"),
            _mapping_get(event.get("data"), "issue"),
            _mapping_get(event.get("triggerContext"), "data"),
            _mapping_get(event.get("triggerContext"), "issue"),
        )
    )


def _issue_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _dedupe_mappings(
        (
            event.get("triggerContext"),
            _mapping_get(event.get("triggerContext"), "issue"),
            event.get("issue"),
            _mapping_get(event.get("data"), "issue"),
            event.get("data"),
            event,
        )
    )


def _metadata_values(event: Mapping[str, Any], keys: Iterable[str]) -> Iterable[Any]:
    key_set = set(keys)
    stack: list[Any] = [event]
    while stack:
        current = stack.pop()
        if isinstance(current, Mapping):
            for key, value in current.items():
                if key in key_set:
                    yield value
                if key not in {"updatedFrom", "updated_from", "previousValues", "previous_values"}:
                    stack.append(value)
        elif isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
            stack.extend(current)


def _first_text(sources: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    value = _first_value(sources, keys)
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _first_value(sources: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> Any:
    for source in sources:
        for key in keys:
            if key in source:
                value = _extract_value(source[key])
                if value is not None:
                    return value
    return None


def _extract_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if nested is not None:
                return nested
        return None
    return value


def _as_iterable(value: Any) -> Iterable[Any]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Mapping):
        return value.keys()
    if isinstance(value, Sequence):
        return value
    return ()


def _dedupe_mappings(values: Iterable[Any]) -> list[Mapping[str, Any]]:
    seen: set[int] = set()
    mappings: list[Mapping[str, Any]] = []
    for value in values:
        if isinstance(value, Mapping) and id(value) not in seen:
            mappings.append(value)
            seen.add(id(value))
    return mappings


def _mapping_get(value: Any, key: str) -> Any:
    return value.get(key) if isinstance(value, Mapping) else None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def _normalize_field_name(value: Any) -> str:
    return _normalize_text(value).replace(" ", "")


def _normalized_updated_fields() -> set[str]:
    return {_normalize_field_name(field) for field in UPDATED_FIELD_NAMES}


def main() -> int:
    result = build_issue_title_update(json.load(sys.stdin))
    if result is not None:
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
