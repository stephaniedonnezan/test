"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_CHANGE_FIELDS = frozenset({"status", "state", "workflowstate", "workflow_state"})
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
)
_FALLBACK_STATUS_KEYS = ("status",)
_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type")
_ISSUE_ID_KEYS = ("id", "issueId", "issue_id", "identifier")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research.

    The automation webhook can be flat, as in Cursor's ``triggerContext``, or a
    nested Linear payload. This function keeps the side-effect outside the
    handler so callers can execute the returned action with their own Linear
    client.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    status = _new_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    title = _string_value(_first_value(contexts, ("title",)))
    issue_id = _string_value(_first_value(contexts, _ISSUE_ID_KEYS))
    if not title or not issue_id:
        return None

    stripped_title = title.strip()
    if _has_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield payload mappings from outermost to innermost useful issue data."""

    yielded: set[int] = set()

    def walk(value: Any) -> Iterable[Mapping[str, Any]]:
        if not isinstance(value, Mapping):
            return

        value_id = id(value)
        if value_id not in yielded:
            yielded.add(value_id)
            yield value

        for key in ("triggerContext", "data", "issue"):
            child = value.get(key)
            if isinstance(child, Mapping):
                yield from walk(child)

    yield from walk(event)


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = [
        _normalize(context.get(key))
        for context in contexts
        for key in _TRIGGER_KEYS
        if context.get(key) is not None
    ]

    if any(value in {"status changed", "status change", "status updated"} for value in trigger_values):
        return True

    updated_fields = [_normalize(field) for context in contexts for field in _updated_fields(context)]
    has_status_field = any(field.replace(" ", "") in _STATUS_CHANGE_FIELDS for field in updated_fields)
    if has_status_field and any(value in {"update", "updated", "issue updated", "updated issue"} for value in trigger_values):
        return True

    return False


def _updated_fields(context: Mapping[str, Any]) -> Iterable[Any]:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        value = context.get(key)
        if isinstance(value, str):
            yield value
        elif isinstance(value, Iterable) and not isinstance(value, (bytes, str, Mapping)):
            yield from value


def _new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit = _first_value(contexts, _EXPLICIT_STATUS_KEYS)
    if explicit is not None:
        return _status_name(explicit)

    for context in contexts:
        for key in ("state", "workflowState", "workflow_state"):
            status = _status_name(context.get(key))
            if status:
                return status

    return _status_name(_first_value(contexts, _FALLBACK_STATUS_KEYS))


def _status_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _string_value(value.get("name"))

    return _string_value(value)


def _first_value(contexts: list[Mapping[str, Any]], keys: Iterable[str]) -> Any:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if value is not None:
                return value

    return None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    separated = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return " ".join(separated.casefold().split())


def main() -> int:
    """Read a JSON event from stdin and print the action as JSON."""

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(payload)
    if action is not None:
        print(json.dumps(action, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
