"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
PREFIXED_TITLE = f"{PREFIX}: "
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}
EVENT_KEYS = ("trigger", "webhookType", "action", "type")
ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
TITLE_KEYS = ("title", "issueTitle", "issue_title")
EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "statusName",
    "status_name",
    "newState",
    "new_state",
    "stateName",
    "state_name",
    "newWorkflowState",
    "new_workflow_state",
    "workflowStateName",
    "workflow_state_name",
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    objects = list(_candidate_objects(event))
    if not _is_status_change_event(objects):
        return None

    new_status = _new_status(objects)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_string(objects, ISSUE_ID_KEYS)
    title = _first_string(objects, TITLE_KEYS)
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIXED_TITLE}{title}",
    }


def _candidate_objects(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield outer metadata before nested issue objects to preserve trigger context."""

    yield event

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield trigger_context

    data = event.get("data")
    if isinstance(data, Mapping):
        yield data

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue

    if isinstance(trigger_context, Mapping):
        nested_issue = trigger_context.get("issue")
        if isinstance(nested_issue, Mapping):
            yield nested_issue

    if isinstance(data, Mapping):
        nested_issue = data.get("issue")
        if isinstance(nested_issue, Mapping):
            yield nested_issue


def _is_status_change_event(objects: Iterable[Mapping[str, Any]]) -> bool:
    object_list = list(objects)
    markers = list(_event_marker_values(object_list))
    if any(_is_direct_status_change_marker(value) for value in markers):
        return True

    if _updated_fields_include_status(object_list) or _changes_include_status(object_list):
        return not markers or any(_is_update_marker(value) for value in markers)

    return False


def _event_marker_values(objects: Iterable[Mapping[str, Any]]) -> Iterable[Any]:
    for obj in objects:
        for key in EVENT_KEYS:
            value = obj.get(key)
            if value is not None:
                yield value


def _is_direct_status_change_marker(value: Any) -> bool:
    normalized = _normalize_text(value)
    compact = normalized.replace(" ", "")
    return "change" in normalized and (
        "status" in normalized or "state" in normalized or "workflowstate" in compact
    )


def _is_update_marker(value: Any) -> bool:
    normalized = _normalize_text(value)
    return normalized in {"update", "updated", "issue update", "issue updated", "updated issue"}


def _updated_fields_include_status(objects: Iterable[Mapping[str, Any]]) -> bool:
    for obj in objects:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = obj.get(key)
            if isinstance(fields, str):
                fields = [fields]
            if isinstance(fields, Iterable) and not isinstance(fields, (Mapping, str, bytes)):
                for field in fields:
                    if _is_status_field(field):
                        return True
    return False


def _changes_include_status(objects: Iterable[Mapping[str, Any]]) -> bool:
    for obj in objects:
        changes = obj.get("changes")
        if isinstance(changes, Mapping):
            for field in changes:
                if _is_status_field(field):
                    return True
    return False


def _new_status(objects: Iterable[Mapping[str, Any]]) -> str | None:
    object_list = list(objects)

    explicit = _first_string(object_list, EXPLICIT_STATUS_KEYS)
    if explicit:
        return explicit

    changed_status = _status_from_changes(object_list)
    if changed_status:
        return changed_status

    for obj in object_list:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = obj.get(key)
            text = _string_from_value(value)
            if text:
                return text

    return None


def _status_from_changes(objects: Iterable[Mapping[str, Any]]) -> str | None:
    for obj in objects:
        changes = obj.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for field, change in changes.items():
            if not _is_status_field(field):
                continue

            if isinstance(change, Mapping):
                for key in ("new", "to", "after", "current", "value"):
                    text = _string_from_value(change.get(key))
                    if text:
                        return text

            text = _string_from_value(change)
            if text:
                return text

    return None


def _first_string(objects: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for obj in objects:
        for key in keys:
            text = _string_from_value(obj.get(key))
            if text:
                return text
    return None


def _string_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "identifier", "key", "id"):
            text = _string_from_value(value.get(key))
            if text:
                return text

    return None


def _is_status_field(value: Any) -> bool:
    normalized = _normalize_text(value)
    compact = normalized.replace(" ", "")
    return normalized in STATUS_FIELDS or compact in STATUS_FIELDS


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_text(value: Any) -> str:
    text = _string_from_value(value)
    if not text:
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    """Read a JSON event from stdin and print the title update action, if any."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": f"invalid JSON: {exc.msg}"}), file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
