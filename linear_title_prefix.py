"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflow_state",
    "workflow state",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to "to research".

    The automation trigger can arrive as Cursor's flat ``triggerContext`` payload
    or as a nested Linear webhook shape. This function is intentionally pure so
    callers can decide how to apply the returned update action.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_contexts(event)
    if not _is_status_change_event(event, contexts):
        return None

    status = _find_new_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    title = _find_string(contexts, ("title", "issueTitle", "issue_title", "name"))
    issue_id = _find_string(
        contexts, ("identifier", "key", "issueId", "issue_id", "id")
    )
    if not title or not issue_id:
        return None

    title = title.strip()
    if not title or title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping):
            contexts.append(value)

    trigger_context = event.get("triggerContext")
    add(trigger_context)
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("issue"))
    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("node"))
        add(data.get("object"))
    add(event)
    add(data)

    return contexts


def _is_status_change_event(
    event: Mapping[str, Any], contexts: Iterable[Mapping[str, Any]]
) -> bool:
    event_markers = []
    for context in contexts:
        event_markers.extend(
            _string_value(context.get(key))
            for key in ("trigger", "webhookType", "action", "type", "eventType")
        )

    normalized_markers = {_normalize(marker) for marker in event_markers if marker}
    if any(
        "status changed" in marker
        or "state changed" in marker
        or "workflow state changed" in marker
        for marker in normalized_markers
    ):
        return True

    is_generic_update = any("update" in marker for marker in normalized_markers)
    return is_generic_update and _updated_fields_include_status(event)


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for container in _candidate_contexts(event):
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
            "changes",
            "updatedFrom",
            "updated_from",
        ):
            if _field_names_include_status(container.get(key)):
                return True
    return False


def _field_names_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        names = value.keys()
    elif isinstance(value, str):
        names = (value,)
    elif isinstance(value, Iterable):
        names = []
        for item in value:
            if isinstance(item, Mapping):
                names.extend(
                    _string_value(item.get(key))
                    for key in ("field", "name", "key", "property", "id")
                )
            else:
                names.append(_string_value(item))
    else:
        return False

    return any(_is_status_field(name) for name in names if name)


def _is_status_field(name: Any) -> bool:
    normalized = _normalize(_string_value(name))
    compact = normalized.replace(" ", "")
    return normalized in _STATUS_FIELD_NAMES or compact in _STATUS_FIELD_NAMES


def _find_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    explicit_status = _find_string(
        contexts,
        (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "newWorkflowState",
            "new_workflow_state",
            "statusName",
            "status_name",
        ),
    )
    if explicit_status:
        return explicit_status

    for key in ("status", "state", "workflowState", "workflow_state"):
        status = _find_string(contexts, (key,))
        if status:
            return status
    return None


def _find_string(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _string_value(context.get(key))
            if value:
                return value
    return None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "key", "id"):
            nested_value = value.get(key)
            if isinstance(nested_value, str):
                return nested_value
    return None


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    alphanumeric = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return " ".join(alphanumeric.lower().split())


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
