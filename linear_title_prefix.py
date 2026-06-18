"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"
ACTION_UPDATE_ISSUE_TITLE = "update_issue_title"
STATUS_FIELD_NAMES = frozenset({"status", "state", "workflowstate", "workflow_state"})


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research.

    The automation runner provides a flat ``triggerContext`` payload, while
    Linear webhooks often nest issue data under ``data`` or ``issue``. This
    function accepts both shapes and returns a side-effect-free action for the
    caller to execute.
    """

    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    status = _extract_new_status(context)
    if _normalize_words(status) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(context, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(context, ("title", "name", "summary"))
    if issue_id is None or title is None:
        return None

    trimmed_title = title.strip()
    if _has_research_prefix(trimmed_title):
        return None

    return {
        "action": ACTION_UPDATE_ISSUE_TITLE,
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {trimmed_title}",
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten likely Linear/Cursor payload containers into one context."""

    context: dict[str, Any] = {}
    for candidate in _walk_mappings(event):
        context.update(candidate)
    return context


def _walk_mappings(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, Mapping):
        return []

    mappings: list[Mapping[str, Any]] = [value]
    for key in ("triggerContext", "data", "issue", "node"):
        nested = value.get(key)
        if isinstance(nested, Mapping):
            mappings.extend(_walk_mappings(nested))
    return mappings


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize_words(context.get(key))
        for key in ("trigger", "webhookType", "action", "type", "eventType")
        if context.get(key) is not None
    ]

    if any("status changed" in value or "state changed" in value for value in trigger_values):
        return True

    if any(value in {"update", "issue updated", "updated issue"} for value in trigger_values):
        return _updated_fields_include_status(context)

    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields")
    changed_fields = context.get("changedFields")
    if _field_list_includes_status(updated_fields) or _field_list_includes_status(changed_fields):
        return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(key) in STATUS_FIELD_NAMES for key in changes)

    return False


def _field_list_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        fields = [value]
    elif isinstance(value, list | tuple | set):
        fields = list(value)
    else:
        return False

    return any(_normalize_field_name(field) in STATUS_FIELD_NAMES for field in fields)


def _extract_new_status(context: Mapping[str, Any]) -> str | None:
    explicit_status = _first_text(
        context,
        (
            "newStatus",
            "new_status",
            "statusName",
            "stateName",
            "workflowStateName",
            "workflow_state_name",
        ),
    )
    if explicit_status is not None:
        return explicit_status

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        changed_status = _status_from_changes(changes)
        if changed_status is not None:
            return changed_status

    for key in ("status", "state", "workflowState", "workflow_state"):
        status = _text_or_name(context.get(key))
        if status is not None:
            return status

    return None


def _status_from_changes(changes: Mapping[str, Any]) -> str | None:
    for key, value in changes.items():
        if _normalize_field_name(key) not in STATUS_FIELD_NAMES:
            continue

        if isinstance(value, Mapping):
            for value_key in ("newValue", "new", "to", "after", "name"):
                status = _text_or_name(value.get(value_key))
                if status is not None:
                    return status
        else:
            status = _text_or_name(value)
            if status is not None:
                return status

    return None


def _first_text(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _text_or_name(context.get(key))
        if value is not None and value.strip():
            return value
    return None


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        name = value.get("name")
        if isinstance(name, str):
            return name
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", words)


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^A-Za-z0-9]+", "", value).lower()


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is None:
        return 0

    json.dump(action, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
