"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue enters research."""
    if not isinstance(event, Mapping):
        return None

    sources = list(_mapping_sources(event))
    if not _is_status_change_event(sources):
        return None

    new_status = _extract_status(sources)
    if _normalize_status(new_status) != _normalize_status(TARGET_STATUS):
        return None

    issue_id = _extract_issue_id(sources)
    title = _extract_title(sources)
    if not issue_id or not title:
        return None

    if title.casefold().startswith(TITLE_PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _mapping_sources(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield useful payload layers, with outer automation metadata first."""
    seen: set[int] = set()

    def visit(value: Any) -> Iterable[Mapping[str, Any]]:
        if not isinstance(value, Mapping):
            return

        value_id = id(value)
        if value_id in seen:
            return
        seen.add(value_id)
        yield value

        for key in ("triggerContext", "data", "issue", "webhook", "payload"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                yield from visit(nested)

    yield from visit(event)


def _is_status_change_event(sources: list[Mapping[str, Any]]) -> bool:
    event_names = [
        text
        for source in sources
        for key in ("trigger", "webhookType", "action", "type", "event", "eventType")
        if (text := _string_value(source.get(key)))
    ]
    normalized_names = {_normalize_token(name) for name in event_names}

    if any(
        name in {"statuschanged", "statuschange", "statechanged", "workflowstatechanged"}
        or name.endswith("statuschanged")
        or name.endswith("statechanged")
        for name in normalized_names
    ):
        return True

    is_update = any(
        name in {"update", "updated", "issueupdate", "issueupdated", "updatedissue"}
        or name.endswith("issueupdated")
        for name in normalized_names
    )
    return is_update and _changed_fields_include_status(sources)


def _changed_fields_include_status(sources: list[Mapping[str, Any]]) -> bool:
    for source in sources:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(source.get(key)):
                return True

        changes = source.get("changes")
        if isinstance(changes, Mapping):
            if any(_is_status_field(field) for field in changes):
                return True
        elif _contains_status_field(changes):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        if any(_is_status_field(field) for field in value):
            return True
        return any(_contains_status_field(item) for item in value.values())
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    return _normalize_token(_string_value(value)) in STATUS_FIELD_NAMES


def _extract_status(sources: list[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "newState",
        "new_state",
        "toState",
        "to_state",
        "newWorkflowState",
        "new_workflow_state",
    )
    for source in sources:
        if status := _first_string(source, explicit_keys):
            return status

    for source in sources:
        if status := _changed_status_value(source.get("changes")):
            return status

    for source in sources:
        for key in ("status", "state", "workflowState", "workflow_state"):
            if status := _status_name(source.get(key)):
                return status

    return None


def _changed_status_value(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for field, change in value.items():
        if not _is_status_field(field):
            continue
        if isinstance(change, Mapping):
            for key in ("to", "new", "after", "toStatus", "newStatus", "name"):
                if status := _status_name(change.get(key)):
                    return status
        elif status := _status_name(change):
            return status

    return None


def _extract_issue_id(sources: list[Mapping[str, Any]]) -> str | None:
    for keys in (
        ("issueId", "issue_id"),
        ("identifier", "key"),
        ("id",),
    ):
        for source in sources:
            if value := _first_string(source, keys):
                return value
    return None


def _extract_title(sources: list[Mapping[str, Any]]) -> str | None:
    return next(
        (
            title
            for source in sources
            if (title := _first_string(source, ("title", "issueTitle", "issue_title")))
        ),
        None,
    )


def _first_string(source: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        if value := _string_value(source.get(key)):
            return value
    return None


def _status_name(value: Any) -> str | None:
    if text := _string_value(value):
        return text
    if isinstance(value, Mapping):
        return _first_string(value, ("name", "title", "label"))
    return None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _normalize_status(value: str | None) -> str:
    return " ".join(_split_words(value or ""))


def _normalize_token(value: str | None) -> str:
    return "".join(_split_words(value or ""))


def _split_words(value: str) -> list[str]:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return [word.casefold() for word in re.findall(r"[A-Za-z0-9]+", spaced)]


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
