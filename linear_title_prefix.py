"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {
    "status",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
    "workflow",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue enters research."""

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change(event):
        return None

    if _normalize(_new_status(event)) != TARGET_STATUS:
        return None

    issue_id = _first_text(_issue_id_values(event))
    title = _first_text(_title_values(event))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change(event: Mapping[str, Any]) -> bool:
    trigger_values = []
    for candidate in _event_metadata_candidates(event):
        trigger_values.extend(
            _values_for_keys(
                candidate,
                (
                    "trigger",
                    "webhookType",
                    "webhook_type",
                    "action",
                    "type",
                    "eventType",
                    "event_type",
                ),
            )
        )

    normalized_triggers = {_normalize(value) for value in trigger_values}
    if any(
        value in {"status changed", "status change", "state changed", "workflow state changed"}
        for value in normalized_triggers
    ):
        return True

    is_generic_update = any(
        value in {"update", "updated", "issue updated", "updated issue"}
        for value in normalized_triggers
    )
    return is_generic_update and _updated_fields_include_status(event)


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for candidate in _event_metadata_candidates(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            for field in _as_iterable(candidate.get(key)):
                if _is_status_field(field):
                    return True

        for key in ("changes", "changed", "updatedFrom", "updated_from"):
            value = candidate.get(key)
            if isinstance(value, Mapping):
                if any(_is_status_field(field) for field in value.keys()):
                    return True

    return False


def _new_status(event: Mapping[str, Any]) -> Any:
    explicit_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "newState",
        "new_state",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    for candidate in _status_candidates(event):
        for value in _values_for_keys(candidate, explicit_keys):
            if _text_from_status(value):
                return _text_from_status(value)

    for candidate in _status_candidates(event):
        for value in _values_for_keys(candidate, fallback_keys):
            if _text_from_status(value):
                return _text_from_status(value)

    return None


def _issue_id_values(event: Mapping[str, Any]) -> Iterable[Any]:
    keys = ("issueId", "issue_id", "identifier", "key", "id")
    for candidate in _issue_candidates(event):
        yield from _values_for_keys(candidate, keys)


def _title_values(event: Mapping[str, Any]) -> Iterable[Any]:
    for candidate in _issue_candidates(event):
        yield from _values_for_keys(candidate, ("title",))


def _status_candidates(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    yield from _mapping_candidates(event, include_issue=True)


def _issue_candidates(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    seen: set[int] = set()
    for path in (
        ("triggerContext",),
        ("data", "issue"),
        ("issue",),
        ("data",),
        (),
    ):
        candidate = _nested_mapping(event, path)
        if candidate is not None and id(candidate) not in seen:
            seen.add(id(candidate))
            yield candidate


def _event_metadata_candidates(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    yield from _mapping_candidates(event, include_issue=False)


def _mapping_candidates(
    event: Mapping[str, Any], *, include_issue: bool
) -> Iterable[Mapping[str, Any]]:
    seen: set[int] = set()
    paths = [
        (),
        ("triggerContext",),
        ("data",),
    ]
    if include_issue:
        paths.extend([("issue",), ("data", "issue")])

    for path in paths:
        candidate = _nested_mapping(event, path)
        if candidate is not None and id(candidate) not in seen:
            seen.add(id(candidate))
            yield candidate


def _nested_mapping(
    source: Mapping[str, Any], path: tuple[str, ...]
) -> Mapping[str, Any] | None:
    current: Any = source
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, Mapping) else None


def _values_for_keys(source: Mapping[str, Any], keys: Iterable[str]) -> Iterable[Any]:
    key_lookup = {_normalize_key(key): key for key in keys}
    for source_key, value in source.items():
        if _normalize_key(source_key) in key_lookup:
            yield value


def _as_iterable(value: Any) -> Iterable[Any]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Mapping):
        return value.keys()
    if isinstance(value, Iterable):
        return value
    return (value,)


def _text_from_status(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _first_text(_values_for_keys(value, (key,)))
            if text:
                return text
        return None
    return value if isinstance(value, str) else None


def _first_text(values: Iterable[Any]) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value
    return None


def _is_status_field(value: Any) -> bool:
    normalized = _normalize(value)
    return normalized in STATUS_FIELD_NAMES


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return re.sub(r"\s+", " ", words).strip().lower()


def main() -> int:
    """Read a JSON event from stdin and write the computed action as JSON."""

    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
