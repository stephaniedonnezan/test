"""Build Linear issue title updates for Cursor research status changes.

The automation receives Cursor/Linear webhook payloads and returns a small
action object for the caller to apply. It intentionally performs no network
calls so it can be tested and reused by different webhook runners.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_WORD = re.compile(r"[^A-Za-z0-9]+")
_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}
_DIRECT_STATUS_CHANGE_MARKERS = {
    "status changed",
    "status change",
    "issue status changed",
    "issue status change",
}
_UPDATE_MARKERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue enters To Research.

    The returned dictionary is designed to be consumed by the surrounding
    automation runner:

    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``

    If the event is not a status transition to ``To Research`` or the issue
    title is already prefixed, ``None`` is returned.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue = _extract_issue(event)
    if issue is None:
        return None

    issue_id, title = issue
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    markers = [_normalize_text(value) for value in _event_marker_values(event)]
    if any(marker in _DIRECT_STATUS_CHANGE_MARKERS for marker in markers if marker):
        return True

    if any(marker in _UPDATE_MARKERS for marker in markers if marker):
        return _has_status_change_metadata(event)

    return _has_status_change_metadata(event) and _extract_new_status(event) is not None


def _event_marker_values(event: Mapping[str, Any]) -> Iterable[Any]:
    for container in _containers(event):
        for key in ("trigger", "webhookType", "action", "type", "event"):
            if key in container:
                yield container[key]


def _has_status_change_metadata(event: Mapping[str, Any]) -> bool:
    for container in _containers(event):
        if _updated_fields_include_status(container.get("updatedFields")):
            return True
        if _changes_include_status(container.get("changes")):
            return True

    return False


def _updated_fields_include_status(updated_fields: Any) -> bool:
    if isinstance(updated_fields, str):
        return _is_status_field_name(updated_fields)

    if not isinstance(updated_fields, Iterable) or isinstance(updated_fields, (bytes, bytearray, Mapping)):
        return False

    for field in updated_fields:
        if isinstance(field, Mapping):
            candidates = (field.get("field"), field.get("name"), field.get("key"), field.get("path"))
            if any(_is_status_field_name(candidate) for candidate in candidates):
                return True
        elif _is_status_field_name(field):
            return True

    return False


def _changes_include_status(changes: Any) -> bool:
    if not isinstance(changes, Mapping):
        return False

    return any(_is_status_field_name(key) for key in changes)


def _extract_new_status(event: Mapping[str, Any]) -> Any:
    for container in _containers(event):
        value = _first_present(
            container,
            (
                "newStatus",
                "new_status",
                "newState",
                "new_state",
                "toStatus",
                "to_status",
                "statusName",
                "stateName",
                "workflowStateName",
            ),
        )
        if value is not None:
            return _status_name(value)

    status_from_changes = _status_from_changes(event)
    if status_from_changes is not None:
        return status_from_changes

    for container in _containers(event):
        value = _first_present(container, ("status", "state", "workflowState"))
        if value is not None:
            return _status_name(value)

    return None


def _status_from_changes(event: Mapping[str, Any]) -> Any:
    for container in _containers(event):
        changes = container.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for key, value in changes.items():
            if not _is_status_field_name(key):
                continue

            if isinstance(value, Mapping):
                changed_value = _first_present(
                    value,
                    ("newValue", "new_value", "to", "after", "value", "name"),
                )
                if changed_value is not None:
                    return _status_name(changed_value)

            return _status_name(value)

    return None


def _extract_issue(event: Mapping[str, Any]) -> tuple[str, str] | None:
    for container in _issue_containers(event):
        title = _string_value(container.get("title"))
        issue_id = _issue_id(container)
        if issue_id and title:
            return issue_id, title

    return None


def _issue_id(container: Mapping[str, Any]) -> str | None:
    return _string_value(
        _first_present(container, ("issueId", "issue_id", "identifier", "key", "id"))
    )


def _issue_containers(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield from _issue_containers(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            yield issue
        yield data

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue

    yield event


def _containers(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    yield event

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield from _containers(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        yield data

        issue = data.get("issue")
        if isinstance(issue, Mapping):
            yield issue

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue


def _first_present(container: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in container:
            return container[key]
    return None


def _status_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _first_present(value, ("name", "title", "status", "state"))
    return value


def _string_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    stripped = value.strip()
    return stripped or None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_text(value)
    return normalized in _STATUS_FIELD_NAMES


def _normalize_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    value = _CAMEL_BOUNDARY.sub(" ", value.strip())
    value = _NON_WORD.sub(" ", value).strip().casefold()
    return re.sub(r"\s+", " ", value) or None


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
