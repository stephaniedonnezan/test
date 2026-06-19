"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status change",
    "status changed",
    "state change",
    "state changed",
    "workflow state change",
    "workflow state changed",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "state id",
    "state name",
    "workflow state",
    "workflow state id",
    "workflow state name",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters To Research.

    The automation runner passes a flattened ``triggerContext`` payload, while
    Linear webhooks often place issue data under ``data`` or ``issue``. This
    function accepts both shapes and returns ``None`` when no title update is
    needed.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _first_status(contexts, event)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    title = _first_string(contexts, ("title",))
    issue_id = _first_string(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    if not title or not issue_id:
        return None

    title = title.strip()
    issue_id = issue_id.strip()
    if not title or not issue_id or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = [event]

    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            contexts.append(value)

    for parent_key in ("triggerContext", "data", "issue"):
        parent = event.get(parent_key)
        if not isinstance(parent, Mapping):
            continue

        for child_key in ("data", "issue"):
            value = parent.get(child_key)
            if isinstance(value, Mapping):
                contexts.append(value)

    return _dedupe_mappings(contexts)


def _dedupe_mappings(contexts: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    seen: set[int] = set()
    unique: list[Mapping[str, Any]] = []
    for context in contexts:
        context_id = id(context)
        if context_id in seen:
            continue

        seen.add(context_id)
        unique.append(context)

    return unique


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    event_names = []
    for context in contexts:
        event_names.extend(
            _string_values(context, ("trigger", "action", "type", "webhookType", "event"))
        )

    normalized_events = {_normalize(name) for name in event_names}
    if normalized_events & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    if normalized_events & _GENERIC_UPDATE_EVENTS:
        return any(_status_field_changed(context) for context in contexts)

    return False


def _status_field_changed(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "changedFields"):
        fields = context.get(key)
        if isinstance(fields, str) and _normalize(fields) in _STATUS_FIELD_NAMES:
            return True

        if isinstance(fields, Iterable) and not isinstance(fields, (str, bytes, Mapping)):
            for field in fields:
                if _normalize(field) in _STATUS_FIELD_NAMES:
                    return True

    changes = context.get("changes") or context.get("updatedFrom")
    if isinstance(changes, Mapping):
        return any(_normalize(key) in _STATUS_FIELD_NAMES for key in changes)

    return False


def _first_status(contexts: Iterable[Mapping[str, Any]], event: Mapping[str, Any]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
    )
    status_keys = ("status", "state", "workflowState", "workflow_state")

    explicit = _first_string(contexts, explicit_keys)
    if explicit:
        return explicit

    changed_status = _changed_status(event)
    if changed_status:
        return changed_status

    return _first_string(contexts, status_keys)


def _changed_status(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for key in ("changes",):
        changes = value.get(key)
        if not isinstance(changes, Mapping):
            continue

        for field_name, change in changes.items():
            if _normalize(field_name) not in _STATUS_FIELD_NAMES:
                continue

            candidate = _change_new_value(change)
            if candidate:
                return candidate

    for child_key in ("triggerContext", "data", "issue"):
        candidate = _changed_status(value.get(child_key))
        if candidate:
            return candidate

    return None


def _change_new_value(change: Any) -> str | None:
    if isinstance(change, str):
        return change

    if not isinstance(change, Mapping):
        return None

    for key in (
        "to",
        "toValue",
        "new",
        "newValue",
        "value",
        "name",
    ):
        candidate = _string_from_value(change.get(key))
        if candidate:
            return candidate

    return None


def _first_string(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            candidate = _string_from_value(context.get(key))
            if candidate:
                return candidate

    return None


def _string_values(context: Mapping[str, Any], keys: Iterable[str]) -> list[str]:
    values = []
    for key in keys:
        candidate = _string_from_value(context.get(key))
        if candidate:
            values.append(candidate)

    return values


def _string_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            candidate = _string_from_value(value.get(key))
            if candidate:
                return candidate

    return None


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    spaced = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return re.sub(r"\s+", " ", spaced).strip().lower()


def _has_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(PREFIX)}\b", title, re.IGNORECASE) is not None


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
