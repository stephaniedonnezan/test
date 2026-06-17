"""Build Linear issue-title updates for issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}
DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
UPDATE_EVENTS = {"update", "updated", "issue update", "issue updated", "updated issue"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue enters research.

    The Cursor automation payload is flat under ``triggerContext`` while raw
    Linear webhooks commonly nest issue fields under ``data.issue``. This
    function accepts both shapes and returns a serializable action for the
    automation runner to apply.
    """
    if not isinstance(event, Mapping):
        return None

    if not _is_status_update_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_status_update_event(event: Mapping[str, Any]) -> bool:
    event_names = {
        _normalize(value)
        for value in _walk_values_for_keys(event, {"trigger", "webhooktype", "action", "type"})
    }
    event_names.discard("")

    if event_names & DIRECT_STATUS_CHANGE_EVENTS:
        return True

    return bool(event_names & UPDATE_EVENTS) and _status_field_changed(event)


def _status_field_changed(event: Mapping[str, Any]) -> bool:
    changed_fields = set()

    for value in _walk_values_for_keys(event, {"updatedfields", "changedfields"}):
        changed_fields.update(_field_names_from(value))

    for value in _walk_values_for_keys(event, {"changes", "changed", "updatedfrom"}):
        if isinstance(value, Mapping):
            changed_fields.update(_normalize_field_name(key) for key in value)

    return bool(changed_fields & STATUS_FIELD_NAMES)


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "toStatus", "to_status", "status", "state", "workflowState"):
        value = _first_value_for_key(event, key)
        status = _status_name(value)
        if status:
            return status

    for value in _walk_values_for_keys(event, {"changes", "changed"}):
        status = _status_from_change_map(value)
        if status:
            return status

    issue = _nested_issue(event)
    if issue:
        for key in ("status", "state", "workflowState"):
            status = _status_name(issue.get(key))
            if status:
                return status

    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for key in ("issueId", "issue_id", "identifier", "key", "id"):
        value = _first_value_for_key(event, key)
        if _is_non_empty_scalar(value):
            return str(value).strip()
    return None


def _extract_title(event: Mapping[str, Any]) -> str | None:
    value = _first_value_for_key(event, "title")
    if _is_non_empty_scalar(value):
        return str(value).strip()
    return None


def _nested_issue(event: Mapping[str, Any]) -> Mapping[str, Any] | None:
    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            return issue
    issue = event.get("issue")
    if isinstance(issue, Mapping):
        return issue
    return None


def _status_from_change_map(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for key, change in value.items():
        if _normalize_field_name(key) not in STATUS_FIELD_NAMES:
            continue
        if isinstance(change, Mapping):
            for nested_key in ("to", "new", "after", "newValue", "value", "name"):
                status = _status_name(change.get(nested_key))
                if status:
                    return status
        status = _status_name(change)
        if status:
            return status

    return None


def _first_value_for_key(event: Mapping[str, Any], desired_key: str) -> Any:
    desired = _normalize_field_name(desired_key)

    for container in _candidate_containers(event):
        for key, value in container.items():
            if _normalize_field_name(key) == desired:
                return value
    return None


def _candidate_containers(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    containers: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        containers.append(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            containers.append(issue)
        containers.append(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        containers.append(issue)

    containers.append(event)
    return containers


def _walk_values_for_keys(value: Any, desired_keys: set[str]) -> list[Any]:
    values: list[Any] = []

    if isinstance(value, Mapping):
        for key, nested in value.items():
            if _normalize_field_name(key) in desired_keys:
                values.append(nested)
            values.extend(_walk_values_for_keys(nested, desired_keys))
    elif _is_sequence(value):
        for item in value:
            values.extend(_walk_values_for_keys(item, desired_keys))

    return values


def _field_names_from(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        names = set()
        for key, nested in value.items():
            names.add(_normalize_field_name(key))
            names.update(_field_names_from(nested))
        return names

    if _is_sequence(value):
        return {_normalize_field_name(item) for item in value if _is_non_empty_scalar(item)}

    if _is_non_empty_scalar(value):
        return {_normalize_field_name(value)}

    return set()


def _status_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "label", "title"):
            nested = value.get(key)
            if _is_non_empty_scalar(nested):
                return str(nested).strip()
        return None

    if _is_non_empty_scalar(value):
        return str(value).strip()

    return None


def _normalize(value: Any) -> str:
    if not _is_non_empty_scalar(value):
        return ""
    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _normalize_field_name(value: Any) -> str:
    return _normalize(value).replace(" ", "")


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _is_non_empty_scalar(value: Any) -> bool:
    return isinstance(value, (str, int, float)) and str(value).strip() != ""


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
