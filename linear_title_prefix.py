"""Build Linear issue title updates for Cursor research-status automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflow_state",
    "workflow status",
    "workflow_status",
}

_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow status changed",
}

_GENERIC_UPDATE_EVENTS = {
    "issue updated",
    "updated issue",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update when an issue moves to "to research".

    The handler accepts Cursor's flat ``triggerContext`` payload as well as
    common nested Linear webhook shapes. It is intentionally side-effect free:
    callers can send the returned action to the system that performs the
    Linear title update.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_contexts(event)
    all_mappings = list(_walk_mappings(event))

    if not _is_status_change_event(all_mappings):
        return None

    if not _status_matches_target(all_mappings):
        return None

    issue_id = _first_text(
        contexts,
        ("issueId", "issue_id", "identifier", "key", "id"),
        skip_root_id=True,
    )
    title = _first_text(contexts, ("title",))

    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely issue contexts from most to least specific."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    trigger_context = event.get("triggerContext") or event.get("trigger_context")
    add(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("node"))
        add(data)

    add(event.get("issue"))
    add(event.get("node"))
    add(event)

    return contexts


def _is_status_change_event(mappings: Iterable[Mapping[str, Any]]) -> bool:
    event_values = {
        _normalize_text(value)
        for mapping in mappings
        for key in ("trigger", "webhookType", "webhook_type", "action", "type", "eventType", "event")
        if (value := mapping.get(key)) is not None
    }

    if any(value in _STATUS_CHANGE_EVENTS for value in event_values):
        return True

    return any(value in _GENERIC_UPDATE_EVENTS for value in event_values) and _updated_fields_include_status(mappings)


def _updated_fields_include_status(mappings: Iterable[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(mapping.get(key)):
                return True

        changes = mapping.get("changes") or mapping.get("changed")
        if isinstance(changes, Mapping):
            if any(_is_status_field_name(str(field_name)) for field_name in changes):
                return True
        elif _contains_status_field(changes):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Mapping):
        name = value.get("name") or value.get("field") or value.get("fieldName") or value.get("key")
        return _contains_status_field(name) or any(_contains_status_field(item) for item in value.values())

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_contains_status_field(item) for item in value)

    return False


def _is_status_field_name(value: str) -> bool:
    normalized = _normalize_text(value)
    return normalized.replace(" ", "") in {
        field.replace(" ", "").replace("_", "")
        for field in _STATUS_FIELD_NAMES
    }


def _status_matches_target(mappings: Iterable[Mapping[str, Any]]) -> bool:
    status_values = list(_status_values(mappings))
    return bool(status_values) and any(_normalize_text(value) == TARGET_STATUS for value in status_values)


def _status_values(mappings: Iterable[Mapping[str, Any]]) -> Iterable[str]:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "toStatus",
        "to_status",
        "toState",
        "to_state",
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    for keys in (explicit_keys, fallback_keys):
        for mapping in mappings:
            for key in keys:
                if key in mapping:
                    text = _status_text(mapping[key])
                    if text:
                        yield text

            yield from _status_values_from_changes(mapping)


def _status_values_from_changes(mapping: Mapping[str, Any]) -> Iterable[str]:
    changes = mapping.get("changes") or mapping.get("changed")
    if not isinstance(changes, Mapping):
        return

    for field_name, change in changes.items():
        if not _is_status_field_name(str(field_name)):
            continue

        if isinstance(change, Mapping):
            for key in ("newValue", "new_value", "to", "after", "value", "name"):
                if key in change:
                    text = _status_text(change[key])
                    if text:
                        yield text
        else:
            text = _status_text(change)
            if text:
                yield text


def _status_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value"):
            text = _status_text(value.get(key))
            if text:
                return text

    return None


def _first_text(
    contexts: Iterable[Mapping[str, Any]],
    keys: Iterable[str],
    *,
    skip_root_id: bool = False,
) -> str | None:
    context_list = list(contexts)
    for key in keys:
        for index, context in enumerate(context_list):
            if skip_root_id and key == "id" and index == len(context_list) - 1:
                continue

            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value

    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_mappings(child)


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", normalized)


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
