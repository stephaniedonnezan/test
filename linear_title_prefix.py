"""Build Linear issue title updates for Cursor research automation."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


RESEARCHING_PREFIX = "Cursor researching"
TO_RESEARCH_STATUS = "to research"
TITLE_SEPARATOR = ": "
STATUS_FIELD_NAMES = frozenset(
    {
        "status",
        "state",
        "workflowstate",
        "workflowstatus",
    }
)
STATUS_CHANGE_TRIGGERS = frozenset(
    {
        "status changed",
        "status change",
        "status updated",
        "status update",
        "state changed",
        "state change",
        "workflow state changed",
        "workflow state change",
    }
)
GENERIC_UPDATE_TRIGGERS = frozenset(
    {
        "issue updated",
        "issue update",
        "updated issue",
        "update",
        "updated",
    }
)


def build_issue_title_update(payload: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue-title update action when an issue moves to research."""

    if not isinstance(payload, Mapping):
        return None

    event = _merge_event_context(payload)
    if not _is_research_status_change(event):
        return None

    issue_id = _find_issue_id(event)
    title = _find_title(event)
    if not issue_id or title is None:
        return None

    updated_title = add_researching_prefix(title)
    if updated_title == title:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": updated_title,
    }


def updated_title_for_status_change(payload: Mapping[str, Any]) -> str | None:
    """Compatibility helper that returns only the updated title."""

    update = build_issue_title_update(payload)
    if update is None:
        return None
    return update["title"]


def add_researching_prefix(title: Any) -> str:
    """Prefix a title with the Cursor research marker unless it is already present."""

    title_text = _string_or_none(title)
    if title_text is None:
        title_text = ""

    stripped_title = title_text.strip()
    if _has_researching_prefix(stripped_title):
        return stripped_title
    if not stripped_title or stripped_title == "[]":
        return RESEARCHING_PREFIX
    return f"{RESEARCHING_PREFIX}{TITLE_SEPARATOR}{stripped_title}"


def _merge_event_context(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Cursor/Linear wrappers while keeping top-level metadata."""

    merged: dict[str, Any] = {}
    _merge_issue_mapping(merged, _mapping_at(payload, ("data", "issue")))
    _merge_issue_mapping(merged, _mapping_at(payload, ("issue",)))
    _merge_issue_mapping(merged, _mapping_at(payload, ("triggerContext", "issue")))
    _merge_mapping(merged, _mapping_at(payload, ("triggerContext",)))
    _merge_mapping(merged, payload)
    return merged


def _merge_issue_mapping(target: dict[str, Any], source: Mapping[str, Any] | None) -> None:
    if source is not None:
        target.update(source)
        if "_issueId" not in target and isinstance(source.get("id"), str):
            target["_issueId"] = source["id"]


def _merge_mapping(target: dict[str, Any], source: Mapping[str, Any] | None) -> None:
    if source is not None:
        target.update(source)


def _mapping_at(payload: Mapping[str, Any], path: Sequence[str]) -> Mapping[str, Any] | None:
    current: Any = payload
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    if isinstance(current, Mapping):
        return current
    return None


def _is_research_status_change(event: Mapping[str, Any]) -> bool:
    if not _is_status_change_event(event):
        return False
    return _normalize_token(_find_new_status(event)) == TO_RESEARCH_STATUS


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_tokens = {
        _normalize_token(value)
        for key in ("trigger", "webhookType", "action", "type")
        if (value := _string_or_none(event.get(key))) is not None
    }
    event_tokens.discard("")

    if event_tokens & STATUS_CHANGE_TRIGGERS:
        return True

    if event_tokens & GENERIC_UPDATE_TRIGGERS:
        return _updated_fields_include_status(event)

    return False


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if _field_list_includes_status(event.get(key)):
            return True

    changes = event.get("changes")
    if isinstance(changes, Mapping):
        return any(_is_status_field_name(key) for key in changes)

    return False


def _field_list_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        return False

    return any(_is_status_field_name(item) for item in value)


def _is_status_field_name(value: Any) -> bool:
    field_name = _string_or_none(value)
    if field_name is None:
        return False
    return _normalize_key(field_name) in STATUS_FIELD_NAMES


def _find_new_status(event: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "status_name"):
        value = _string_or_none(event.get(key))
        if value:
            return value

    for key in ("state", "workflowState", "workflowStatus", "status"):
        value = _status_name_from_value(event.get(key))
        if value:
            return value

    changes = event.get("changes")
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _is_status_field_name(key):
                changed_status = _status_name_from_value(value)
                if changed_status:
                    return changed_status

    return None


def _status_name_from_value(value: Any) -> str | None:
    direct_value = _string_or_none(value)
    if direct_value:
        return direct_value

    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "to", "after", "name"):
            status_name = _status_name_from_value(value.get(key))
            if status_name:
                return status_name

    return None


def _find_issue_id(event: Mapping[str, Any]) -> str | None:
    for key in ("issueId", "issue_id", "identifier", "key", "_issueId", "id"):
        value = _string_or_none(event.get(key))
        if value:
            return value.strip()
    return None


def _find_title(event: Mapping[str, Any]) -> str | None:
    value = _string_or_none(event.get("title"))
    if value is None:
        return None
    return value.strip()


def _has_researching_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(RESEARCHING_PREFIX)}\b", title, re.IGNORECASE) is not None


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _normalize_token(value: Any) -> str:
    text = _string_or_none(value)
    if text is None:
        return ""
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def _string_or_none(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    return None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a Linear issue title update when status changes to to research.",
    )
    parser.add_argument(
        "--input",
        "-i",
        help="Path to a JSON payload file. Reads stdin when omitted.",
    )
    args = parser.parse_args(argv)

    try:
        if args.input:
            with open(args.input, encoding="utf-8") as payload_file:
                payload = json.load(payload_file)
        else:
            payload = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print(f"Invalid JSON payload: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"Unable to read payload: {error}", file=sys.stderr)
        return 2

    update = build_issue_title_update(payload)
    print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
