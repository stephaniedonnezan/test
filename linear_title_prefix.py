"""Build Linear issue-title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"
UPDATE_ACTION = "update_issue_title"

_CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]+")


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a title update action when an issue moves to To Research.

    The automation receives payloads from both Cursor's Linear trigger wrapper and
    native Linear webhooks. This function intentionally accepts the common shapes
    used by both sources and returns a side-effect-free action for the caller to
    apply.
    """

    if not isinstance(event, Mapping):
        return None

    maps = _collect_maps(event)
    if not _is_status_change_event(maps):
        return None

    status = _target_status(maps)
    if _normalize(status) != RESEARCH_STATUS:
        return None

    issue_id, title = _issue_identity(event)
    if not issue_id or not title:
        return None

    prefixed_title = _prefix_title(title)
    if prefixed_title == title:
        return None

    return {"action": UPDATE_ACTION, "issueId": issue_id, "title": prefixed_title}


def handle_issue_status_changed(event: Any) -> dict[str, str] | None:
    """Compatibility alias for automation runtimes expecting a handler name."""

    return build_issue_title_update(event)


def _collect_maps(root: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect mapping nodes breadth-first with wrapper contexts first."""

    maps: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            maps.append(value)

    for context in _preferred_contexts(root):
        add(context)

    index = 0
    while index < len(maps):
        current = maps[index]
        index += 1
        for value in current.values():
            if isinstance(value, Mapping):
                add(value)
            elif isinstance(value, list):
                for item in value:
                    add(item)

    return maps


def _preferred_contexts(root: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    for wrapper_key in ("automation_trigger_info", "automationTriggerInfo"):
        wrapper = root.get(wrapper_key)
        if isinstance(wrapper, Mapping):
            trigger_context = wrapper.get("triggerContext")
            if isinstance(trigger_context, Mapping):
                contexts.append(trigger_context)

    trigger_context = root.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)

    issue = root.get("issue")
    if isinstance(issue, Mapping):
        contexts.append(issue)

    data = root.get("data")
    if isinstance(data, Mapping):
        data_issue = data.get("issue")
        if isinstance(data_issue, Mapping):
            contexts.append(data_issue)
        contexts.append(data)

    contexts.append(root)
    return contexts


def _is_status_change_event(maps: Iterable[Mapping[str, Any]]) -> bool:
    maps = list(maps)

    for item in maps:
        for key in ("trigger", "webhookType", "action", "type"):
            value = item.get(key)
            normalized = _normalize(value)
            if normalized in {
                "status changed",
                "status change",
                "state changed",
                "state change",
                "workflow state changed",
                "workflow state change",
            }:
                return True

    update_seen = any(
        _normalize(item.get(key)) in {"update", "updated", "issue update", "issue updated", "updated issue"}
        for item in maps
        for key in ("trigger", "webhookType", "action", "type")
    )
    return update_seen and _mentions_status_field(maps)


def _mentions_status_field(maps: Iterable[Mapping[str, Any]]) -> bool:
    for item in maps:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            value = item.get(key)
            if _contains_status_field(value):
                return True

        for key in ("changes", "change", "updatedFrom", "updated_from"):
            value = item.get(key)
            if isinstance(value, Mapping) and any(_is_status_field(field) for field in value):
                return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
        return any(_contains_status_field(item) for item in value)
    return False


def _target_status(maps: Iterable[Mapping[str, Any]]) -> str | None:
    maps = list(maps)

    for key in (
        "newStatus",
        "new_status",
        "newStatusName",
        "new_status_name",
        "targetStatus",
        "target_status",
        "toStatus",
        "to_status",
        "newState",
        "new_state",
        "newStateName",
        "new_state_name",
        "targetState",
        "target_state",
        "workflowStateName",
        "workflow_state_name",
    ):
        value = _first_status_for_key(maps, key)
        if value:
            return value

    changed_status = _status_from_changes(maps)
    if changed_status:
        return changed_status

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _first_status_for_key(maps, key)
        if value:
            return value

    return None


def _first_status_for_key(maps: Iterable[Mapping[str, Any]], key: str) -> str | None:
    for item in maps:
        if key in item:
            value = _status_value(item.get(key))
            if value:
                return value
    return None


def _status_from_changes(maps: Iterable[Mapping[str, Any]]) -> str | None:
    for item in maps:
        for container_key in ("changes", "change"):
            container = item.get(container_key)
            if not isinstance(container, Mapping):
                continue

            for field, change in container.items():
                if not _is_status_field(field):
                    continue

                value = _status_value_from_change(change)
                if value:
                    return value

    return None


def _status_value_from_change(change: Any) -> str | None:
    if isinstance(change, str):
        return change.strip() or None

    if not isinstance(change, Mapping):
        return None

    for key in (
        "to",
        "after",
        "new",
        "newValue",
        "new_value",
        "toValue",
        "to_value",
        "toName",
        "to_name",
    ):
        value = _status_value(change.get(key))
        if value:
            return value

    return _status_value(change)


def _status_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested_value = value.get(key)
            if isinstance(nested_value, str) and nested_value.strip():
                return nested_value.strip()

    return None


def _is_status_field(value: Any) -> bool:
    normalized = _normalize(value)
    return normalized in {"status", "state", "workflow state", "workflowstate"}


def _issue_identity(event: Mapping[str, Any]) -> tuple[str | None, str | None]:
    for item in _issue_contexts(event):
        issue_id = _first_text(item, ("issueId", "issue_id", "identifier", "key", "id"))
        title = _first_text(item, ("title", "issueTitle", "issue_title"))
        if issue_id and title:
            return issue_id, title

    return None, None


def _issue_contexts(root: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    for context in _preferred_contexts(root):
        if _looks_like_issue(context):
            contexts.append(context)

    for context in _collect_maps(root):
        if _looks_like_issue(context) and context not in contexts:
            contexts.append(context)

    return contexts


def _looks_like_issue(item: Mapping[str, Any]) -> bool:
    has_title = any(key in item for key in ("title", "issueTitle", "issue_title"))
    has_id = any(key in item for key in ("issueId", "issue_id", "identifier", "key", "id"))
    return has_title and has_id


def _first_text(item: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _prefix_title(title: str) -> str:
    if title.lower().startswith(TITLE_PREFIX.lower()):
        return title
    return f"{TITLE_PREFIX}: {title}"


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = _CAMEL_CASE_BOUNDARY.sub(" ", str(value)).strip().lower()
    text = _NON_ALPHANUMERIC.sub(" ", text)
    return " ".join(text.split())


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print(f"Invalid JSON: {error}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update:
        print(json.dumps(update, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
