"""Build Linear issue title updates for research status transitions.

The automation receives slightly different payload shapes depending on whether
it is run from Cursor's automation trigger context or a raw Linear webhook. This
module keeps the public surface small: call ``build_issue_title_update`` with the
event payload and apply the returned action when it is not ``None``.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELDS = {
    "status",
    "state",
    "workflowstate",
    "workflow_state",
    "workflow status",
    "workflow_status",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to to-research.

    The returned payload is intentionally transport-agnostic so the caller can
    decide how to apply it to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_text(new_status) != _normalize_text(TARGET_STATUS):
        return None

    issue = _issue_payload(contexts)
    issue_id = _string_value(_first_present(issue, ("issueId", "issue_id", "id", "identifier", "key")))
    title = _string_value(_first_present(issue, ("title", "name", "summary")))

    if issue_id is None or title is None:
        return None

    stripped_title = title.strip()
    if not stripped_title or _has_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {stripped_title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely metadata/issue contexts from outermost to innermost."""

    contexts: list[Mapping[str, Any]] = [event]

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    trigger_context = event.get("automation_trigger_info")
    if isinstance(trigger_context, Mapping):
        add(trigger_context)
        add(trigger_context.get("triggerContext"))

    add(event.get("triggerContext"))
    add(event.get("data"))
    add(event.get("issue"))

    for context in list(contexts):
        add(context.get("data"))
        add(context.get("issue"))
        add(context.get("state"))
        add(context.get("workflowState"))

    return contexts


def _is_status_change_event(contexts: Sequence[Mapping[str, Any]]) -> bool:
    trigger_values: list[str] = []
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type", "eventType"):
            value = _string_value(context.get(key))
            if value is not None:
                trigger_values.append(value)

    normalized_triggers = {_normalize_compact(value) for value in trigger_values}
    if any(value in normalized_triggers for value in ("statuschanged", "statechanged", "workflowstatechanged")):
        return True

    if any(value in normalized_triggers for value in ("issueupdated", "updatedissue", "update")):
        return _updated_fields_include_status(contexts) or _has_status_change_object(contexts)

    return False


def _updated_fields_include_status(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = context.get(key)
            if isinstance(fields, str):
                values = [fields]
            elif isinstance(fields, Sequence) and not isinstance(fields, (str, bytes, bytearray)):
                values = list(fields)
            else:
                continue

            if any(_normalize_status_field(field) in _STATUS_FIELDS for field in values):
                return True

    return False


def _has_status_change_object(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        changes = context.get("changes") or context.get("changed") or context.get("updates")
        if not isinstance(changes, Mapping):
            continue

        for key in changes:
            if _normalize_status_field(key) in _STATUS_FIELDS:
                return True

    return False


def _extract_new_status(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in (
            "newStatus",
            "new_status",
            "statusName",
            "status_name",
            "stateName",
            "state_name",
            "workflowStateName",
            "workflow_state_name",
        ):
            value = _status_value(context.get(key))
            if value is not None:
                return value

    for context in contexts:
        changes = context.get("changes") or context.get("changed") or context.get("updates")
        if not isinstance(changes, Mapping):
            continue

        for key, change in changes.items():
            if _normalize_status_field(key) not in _STATUS_FIELDS:
                continue

            if isinstance(change, Mapping):
                for new_key in ("newValue", "new_value", "to", "after", "name"):
                    value = _status_value(change.get(new_key))
                    if value is not None:
                        return value
            else:
                value = _status_value(change)
                if value is not None:
                    return value

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = _status_value(context.get(key))
            if value is not None:
                return value

    return None


def _issue_payload(contexts: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    merged: dict[str, Any] = {}
    for context in reversed(contexts):
        if isinstance(context, Mapping):
            merged.update(context)
    return merged


def _first_present(context: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        value = context.get(key)
        if value is not None:
            return value
    return None


def _status_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "status", "state"):
            nested = _string_value(value.get(key))
            if nested is not None:
                return nested
        return None
    return _string_value(value)


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    return None


def _normalize_status_field(value: Any) -> str:
    return _normalize_text(_string_value(value) or "").replace(" ", "")


def _normalize_compact(value: str) -> str:
    return _normalize_text(value).replace(" ", "")


def _normalize_text(value: str | None) -> str:
    if value is None:
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", spaced).casefold().strip()
    return re.sub(r"\s+", " ", words)


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
