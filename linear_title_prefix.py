"""Build Linear issue-title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any, Optional


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any]) -> Optional[dict[str, str]]:
    """Return a title-update action when an issue moves to To Research.

    The Cursor automation payload is usually a flat ``triggerContext`` object,
    while native Linear webhooks often nest the issue under ``data``. This
    function accepts both shapes and returns a small action object for the
    caller to apply through the Linear API.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _issue_payload(event)
    if payload is None:
        return None

    if not _is_status_change(event):
        return None

    if _normalise_text(_status_value(event, payload)) != TARGET_STATUS:
        return None

    issue_id = _string_value(payload, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _string_value(payload, ("title", "name"))
    if issue_id is None or title is None:
        return None

    title = title.strip()
    if not title or title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _issue_payload(event: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            return _merged(issue, data, event)
        return _merged(data, event)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        return _merged(issue, event)

    return event


def _merged(*sources: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for source in sources:
        merged.update(source)
    return merged


def _is_status_change(event: Mapping[str, Any]) -> bool:
    values = _event_type_values(event)
    if any(_normalise_text(value) in {"status changed", "status change"} for value in values):
        return True

    if not any(_normalise_text(value) in {"update", "updated", "issue updated", "updated issue"} for value in values):
        return False

    return _updated_status_fields(event)


def _event_type_values(event: Mapping[str, Any]) -> list[Any]:
    values: list[Any] = []
    for container in _candidate_containers(event):
        for key in ("trigger", "webhookType", "action", "type"):
            if key in container:
                values.append(container[key])
    return values


def _candidate_containers(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    containers: list[Mapping[str, Any]] = [event]
    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            containers.append(value)
            nested_issue = value.get("issue")
            if isinstance(nested_issue, Mapping):
                containers.append(nested_issue)
    return containers


def _updated_status_fields(event: Mapping[str, Any]) -> bool:
    for container in _candidate_containers(event):
        for key in ("updatedFields", "updated_fields"):
            if _contains_status_field(container.get(key)):
                return True

        changes = container.get("changes")
        if isinstance(changes, Mapping) and any(_is_status_field(field) for field in changes):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        return any(_is_status_field(field) for field in value)
    if isinstance(value, (list, tuple, set)):
        return any(_is_status_field(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    return isinstance(value, str) and _normalise_text(value) in STATUS_FIELDS


def _status_value(event: Mapping[str, Any], payload: Mapping[str, Any]) -> Any:
    for container in (*_candidate_containers(event), payload):
        value = _first_present(container, ("newStatus", "new_status", "statusName", "stateName", "workflowStateName"))
        if value is not None:
            return value

    changes_value = _status_change_value(event)
    if changes_value is not None:
        return changes_value

    for container in (payload, *_candidate_containers(event)):
        value = _first_present(container, ("status", "state", "workflowState"))
        if value is not None:
            return _name_or_value(value)

    return None


def _status_change_value(event: Mapping[str, Any]) -> Any:
    for container in _candidate_containers(event):
        changes = container.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for field, change in changes.items():
            if not _is_status_field(field):
                continue
            if isinstance(change, Mapping):
                return _name_or_value(_first_present(change, ("newValue", "new", "to", "after", "value", "name")))
            return _name_or_value(change)

    return None


def _first_present(container: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in container and container[key] is not None:
            return container[key]
    return None


def _name_or_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _first_present(value, ("name", "title", "value"))
    return value


def _string_value(container: Mapping[str, Any], keys: tuple[str, ...]) -> Optional[str]:
    value = _first_present(container, keys)
    if isinstance(value, str) and value.strip():
        return value
    return None


def _normalise_text(value: Any) -> str:
    value = _name_or_value(value)
    if not isinstance(value, str):
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
