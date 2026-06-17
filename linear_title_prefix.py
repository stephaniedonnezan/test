"""Build Linear issue title updates for issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate"}
_DIRECT_STATUS_CHANGE_EVENTS = {
    "statuschanged",
    "statechanged",
    "workflowstatechanged",
    "issuestatuschanged",
    "issuestatechanged",
    "issueworkflowstatechanged",
}
_UPDATE_EVENTS = {"update", "updated", "issueupdate", "issueupdated", "updatedissue"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to "to research".

    The Cursor automation payload may wrap Linear fields in ``triggerContext``;
    raw Linear webhooks often put issue details under ``data.issue``. This
    function accepts both shapes and returns a serializable action for the
    caller that performs the actual Linear API update.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if not issue_id or not title:
        return None

    if _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_names = [
        _normalize_event_name(value)
        for source in _metadata_sources(event)
        for key in ("trigger", "action", "type", "webhookType", "eventType")
        if (value := source.get(key)) is not None
    ]

    if any(name in _DIRECT_STATUS_CHANGE_EVENTS for name in event_names):
        return True

    if any(name in _UPDATE_EVENTS for name in event_names):
        return _changed_fields_include_status(event)

    return False


def _changed_fields_include_status(event: Mapping[str, Any]) -> bool:
    for source in _metadata_sources(event):
        for key in ("updatedFields", "changedFields", "fields"):
            if _field_collection_includes_status(source.get(key)):
                return True

        field_name = _coerce_text(source.get("field"))
        if field_name and _is_status_field(field_name):
            return True

        changes = source.get("changes")
        if isinstance(changes, Mapping) and any(_is_status_field(key) for key in changes):
            return True

    return False


def _field_collection_includes_status(value: Any) -> bool:
    if value is None:
        return False

    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value)

    if isinstance(value, Iterable):
        return any(_is_status_field(item) for item in value)

    return False


def _is_status_field(value: Any) -> bool:
    text = _coerce_text(value)
    if not text:
        return False

    normalized = _normalize_event_name(text)
    return normalized in _STATUS_FIELD_NAMES or normalized.endswith("status")


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for source in _status_sources(event):
        for key in (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "statusName",
            "stateName",
            "workflowStateName",
        ):
            status = _coerce_text(source.get(key))
            if status:
                return status

    for source in _status_sources(event):
        status = _extract_status_from_changes(source.get("changes"))
        if status:
            return status

    for source in _status_sources(event):
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _coerce_text(source.get(key))
            if status:
                return status

    return None


def _extract_status_from_changes(changes: Any) -> str | None:
    if not isinstance(changes, Mapping):
        return None

    for field_name, change in changes.items():
        if not _is_status_field(field_name):
            continue

        if isinstance(change, Mapping):
            for key in ("to", "new", "newValue", "after", "toValue"):
                status = _coerce_text(change.get(key))
                if status:
                    return status

        status = _coerce_text(change)
        if status:
            return status

    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    sources = _issue_sources(event)

    for key in ("identifier", "issueId", "issue_id", "key"):
        for source in sources:
            issue_id = _coerce_text(source.get(key))
            if issue_id:
                return issue_id

    for source in sources:
        issue_id = _coerce_text(source.get("id"))
        if issue_id:
            return issue_id

    return None


def _extract_title(event: Mapping[str, Any]) -> str | None:
    for source in _issue_sources(event):
        title = _coerce_text(source.get("title"))
        if title:
            return title

    return None


def _metadata_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _dedupe_mappings(
        [
            event,
            _mapping_at(event, "triggerContext"),
            _mapping_at(event, "data"),
            _mapping_at(event, "payload"),
        ]
    )


def _status_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _dedupe_mappings(
        [
            _mapping_at(event, "triggerContext"),
            event,
            _mapping_at(event, "data"),
            _mapping_at(event, "payload"),
            _nested_mapping(event, ("data", "issue")),
            _mapping_at(event, "issue"),
            _nested_mapping(event, ("payload", "issue")),
        ]
    )


def _issue_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _dedupe_mappings(
        [
            _mapping_at(event, "triggerContext"),
            _nested_mapping(event, ("data", "issue")),
            _mapping_at(event, "issue"),
            _nested_mapping(event, ("payload", "issue")),
            _mapping_at(event, "data"),
            _mapping_at(event, "payload"),
            event,
        ]
    )


def _mapping_at(source: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    value = source.get(key)
    return value if isinstance(value, Mapping) else None


def _nested_mapping(source: Mapping[str, Any], path: tuple[str, ...]) -> Mapping[str, Any] | None:
    current: Any = source
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)

    return current if isinstance(current, Mapping) else None


def _dedupe_mappings(sources: Iterable[Mapping[str, Any] | None]) -> list[Mapping[str, Any]]:
    deduped: list[Mapping[str, Any]] = []
    seen: set[int] = set()
    for source in sources:
        if source is None:
            continue
        source_id = id(source)
        if source_id in seen:
            continue
        seen.add(source_id)
        deduped.append(source)

    return deduped


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, str):
        text = value.strip()
        return text or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "key", "label", "value", "id"):
            text = _coerce_text(value.get(key))
            if text:
                return text
        return None

    if isinstance(value, (int, float)):
        return str(value)

    return None


def _has_title_prefix(title: str) -> bool:
    return title.lstrip().lower().startswith(TITLE_PREFIX.lower())


def _normalize_words(value: Any) -> str | None:
    text = _coerce_text(value)
    if text is None:
        return None

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[_\-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _normalize_event_name(value: Any) -> str:
    text = _normalize_words(value)
    if text is None:
        return ""

    return re.sub(r"[^a-z0-9]", "", text)


def main() -> int:
    """Read a JSON event from stdin and print the update action, if any."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print(f"Invalid JSON payload: {error}", file=sys.stderr)
        return 1

    if not isinstance(event, Mapping):
        return 0

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
