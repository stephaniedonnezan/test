"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

STATUS_KEYS = ("status", "state", "workflowState")
STATUS_CHANGE_FIELDS = frozenset(("status", "state", "workflowstate", "workflow_state"))
TRIGGER_KEYS = ("trigger", "webhookType", "action", "type")
STATUS_CHANGED_TRIGGERS = frozenset(("statuschanged", "statuschange", "statusupdated"))
ISSUE_UPDATED_TRIGGERS = frozenset(
    (
        "issueupdated",
        "updatedissue",
        "update",
        "updated",
    )
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research.

    The automation trigger payloads may be flat, nested under ``triggerContext``,
    or shaped like Linear webhook data. This function keeps the output small and
    side-effect free so callers can apply the returned action with their own
    Linear client.
    """

    if not isinstance(event, Mapping):
        return None

    context = _merge_context(event)
    if not _is_status_change_event(context):
        return None

    status = _new_status(context)
    if _normalize_status(status) != _normalize_status(TARGET_STATUS):
        return None

    title = _first_text(context, ("title", "name"))
    issue_id = _first_text(context, ("id", "issueId", "issue_id", "identifier"))
    if not title or not issue_id:
        return None

    trimmed_title = title.strip()
    if _has_title_prefix(trimmed_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {trimmed_title}",
    }


def _merge_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common automation/Linear wrappers without losing outer fields."""

    context: dict[str, Any] = {}
    for item in _iter_mappings(event):
        context.update(item)
    return context


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if not isinstance(value, Mapping):
        return

    # Yield nested issue data first so outer trigger metadata wins on conflicts.
    for key in ("issue", "data", "triggerContext", "trigger_context"):
        nested = value.get(key)
        if isinstance(nested, Mapping):
            yield from _iter_mappings(nested)

    yield value


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = [_normalize_token(value) for value in _values_for_keys(context, TRIGGER_KEYS)]
    if any(value in STATUS_CHANGED_TRIGGERS for value in trigger_values):
        return True

    if any(value in ISSUE_UPDATED_TRIGGERS for value in trigger_values):
        fields = _updated_fields(context)
        return any(field in STATUS_CHANGE_FIELDS for field in fields)

    return False


def _updated_fields(context: Mapping[str, Any]) -> set[str]:
    fields: set[str] = set()
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        value = context.get(key)
        if isinstance(value, str):
            fields.add(_normalize_token(value))
        elif isinstance(value, Iterable) and not isinstance(value, (bytes, str, Mapping)):
            for item in value:
                if isinstance(item, str):
                    fields.add(_normalize_token(item))
    return fields


def _new_status(context: Mapping[str, Any]) -> Any:
    for key in ("newStatus", "new_status", "statusName", "status_name"):
        value = context.get(key)
        if value:
            return _status_name(value)

    for key in STATUS_KEYS:
        value = context.get(key)
        status = _status_name(value)
        if status:
            return status

    return None


def _status_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        return value.get("name") or value.get("title") or value.get("status")
    return value


def _first_text(context: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _values_for_keys(context: Mapping[str, Any], keys: Iterable[str]) -> Iterable[Any]:
    for key in keys:
        value = context.get(key)
        if value is not None:
            yield value


def _normalize_status(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _normalize_words(value)


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", _split_camel_case(value).lower())


def _normalize_words(value: str) -> str:
    words = re.sub(r"[^a-z0-9]+", " ", _split_camel_case(value).lower()).strip()
    return re.sub(r"\s+", " ", words)


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def _has_title_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    """Read a JSON event from stdin and print the title update action if any."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
