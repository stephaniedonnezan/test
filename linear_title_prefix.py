"""Build title update actions for Linear issues entering research.

The automation runtime is expected to apply the returned action to Linear.
This module keeps the decision logic small and testable.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_KEYS = {"status", "state", "workflowstate", "workflow_state"}
TRIGGER_KEYS = {"trigger", "webhooktype", "webhook_type", "action", "type"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue moves to research.

    The function accepts the flat Cursor automation trigger payload as well as
    nested Linear webhook-style payloads. Non-status changes, non-research
    statuses, missing issue data, and already-prefixed titles return ``None``.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts, event):
        return None

    new_status = _new_status(event, contexts)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    title = _issue_title(contexts)
    issue_id = _issue_id(contexts)
    if not title or not issue_id:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely metadata and issue mappings in useful lookup order."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event.get("triggerContext"))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data)

    add(event.get("issue"))
    add(event)

    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]], event: Mapping[str, Any]) -> bool:
    trigger_values = [
        value
        for context in contexts
        for key, value in context.items()
        if _key(key) in TRIGGER_KEYS
    ]

    if any(_looks_like_direct_status_change(value) for value in trigger_values):
        return True

    if any(_looks_like_issue_update(value) for value in trigger_values):
        return _mentions_status_field(event)

    # Cursor status-change triggers commonly include an explicit newStatus even
    # when trigger metadata is omitted in tests or replay payloads.
    return _explicit_new_status(contexts) is not None and _mentions_status_field(event)


def _looks_like_direct_status_change(value: Any) -> bool:
    normalized = _normalize(value)
    return "status" in normalized.split() and any(
        word in normalized.split() for word in ("changed", "change")
    )


def _looks_like_issue_update(value: Any) -> bool:
    normalized = _normalize(value)
    return normalized in {"update", "updated", "issue update", "issue updated", "updated issue"}


def _new_status(event: Mapping[str, Any], contexts: list[Mapping[str, Any]]) -> Any:
    explicit = _explicit_new_status(contexts)
    if explicit is not None:
        return explicit

    changed = _changed_status_value(event)
    if changed is not None:
        return changed

    for context in contexts:
        value = _lookup(context, ("status", "state", "workflowState", "workflow_state"))
        if value is not None:
            return _status_name(value)

    return None


def _explicit_new_status(contexts: list[Mapping[str, Any]]) -> Any:
    names = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "newState",
        "new_state",
        "toState",
        "to_state",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
    )
    for context in contexts:
        value = _lookup(context, names)
        if value is not None:
            return _status_name(value)
    return None


def _changed_status_value(event: Mapping[str, Any]) -> Any:
    for container_name in ("changes", "updatedFields", "updated_fields"):
        value = _find_by_key(event, container_name)
        changed = _status_value_from_change_container(value)
        if changed is not None:
            return changed
    return None


def _status_value_from_change_container(value: Any) -> Any:
    if isinstance(value, Mapping):
        field = _lookup(value, ("field", "name", "key"))
        if field is not None and _is_status_field(field):
            return _change_target(value)

        for key, nested_value in value.items():
            if _is_status_field(key):
                return _change_target(nested_value)

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for item in value:
            if isinstance(item, str) and _is_status_field(item):
                return None
            changed = _status_value_from_change_container(item)
            if changed is not None:
                return changed

    return None


def _change_target(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value

    for key in ("to", "after", "new", "newValue", "new_value", "value", "name"):
        target = _lookup(value, (key,))
        if target is not None:
            return _status_name(target)

    return None


def _mentions_status_field(event: Mapping[str, Any]) -> bool:
    for container_name in ("changes", "updatedFields", "updated_fields"):
        value = _find_by_key(event, container_name)
        if _container_mentions_status(value):
            return True
    return False


def _container_mentions_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        field = _lookup(value, ("field", "name", "key"))
        if field is not None and _is_status_field(field):
            return True
        return any(_is_status_field(key) for key in value)

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(
            _is_status_field(item)
            if isinstance(item, str)
            else _container_mentions_status(item)
            for item in value
        )

    return False


def _issue_title(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        value = _lookup(context, ("title",))
        if isinstance(value, str):
            title = value.strip()
            if title:
                return title
    return None


def _issue_id(contexts: list[Mapping[str, Any]]) -> str | None:
    preferred_keys = ("issueId", "issue_id", "identifier", "key")
    fallback_keys = ("id",)

    for keys in (preferred_keys, fallback_keys):
        for context in contexts:
            value = _lookup(context, keys)
            if isinstance(value, str):
                issue_id = value.strip()
                if issue_id:
                    return issue_id
    return None


def _status_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "status"):
            nested = _lookup(value, (key,))
            if nested is not None:
                return nested
    return value


def _find_by_key(value: Any, key_name: str) -> Any:
    expected = _key(key_name)
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if _key(key) == expected:
                return nested_value
            found = _find_by_key(nested_value, key_name)
            if found is not None:
                return found
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for item in value:
            found = _find_by_key(item, key_name)
            if found is not None:
                return found
    return None


def _lookup(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    expected = {_key(key) for key in keys}
    for key, value in mapping.items():
        if _key(key) in expected:
            return value
    return None


def _is_status_field(value: Any) -> bool:
    return _key(value) in STATUS_FIELD_KEYS


def _key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _normalize(value: Any) -> str:
    value = _status_name(value)
    text = "" if value is None else str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
