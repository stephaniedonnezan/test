"""Build Linear issue title updates for Cursor research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
DIRECT_STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statusupdated",
    "statusupdate",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}
GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}
TRIGGER_KEYS = ("trigger", "webhookType", "action", "type")
EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "statusName",
    "status_name",
    "newState",
    "new_state",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
ISSUE_ID_KEYS = ("identifier", "key", "issueId", "issue_id", "id")
TITLE_KEYS = ("title", "name")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    context = _merged_context(event)
    if not _is_status_change_event(context):
        return None

    new_status = _extract_new_status(context)
    if _normalize_token(new_status) != _normalize_token(TARGET_STATUS):
        return None

    issue_id = _extract_text(context, ISSUE_ID_KEYS)
    title = _extract_text(context, TITLE_KEYS)
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        prefixed_title = title
    else:
        prefixed_title = f"{PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": prefixed_title,
    }


def _merged_context(event: Mapping[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = {}
    for candidate in _candidate_mappings(event):
        context.update(candidate)
    return context


def _candidate_mappings(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely issue objects first and outer trigger metadata last."""

    for key in ("issue", "data", "triggerContext"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            yield from _candidate_mappings(nested)
            yield nested
    yield event


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = [_normalize_token(context.get(key)) for key in TRIGGER_KEYS]
    if any(value in DIRECT_STATUS_CHANGE_TRIGGERS for value in trigger_values):
        return True

    if any(value in GENERIC_UPDATE_TRIGGERS for value in trigger_values):
        return _status_field_changed(context)

    return False


def _status_field_changed(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if _contains_status_field(context.get(key)):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping) and any(_is_status_field(key) for key in changes):
        return True

    updated_from = context.get("updatedFrom") or context.get("updated_from")
    if isinstance(updated_from, Mapping) and any(_is_status_field(key) for key in updated_from):
        return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
        return any(_is_status_field(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    return _normalize_token(value) in STATUS_FIELDS


def _extract_new_status(context: Mapping[str, Any]) -> str | None:
    explicit = _extract_text(context, EXPLICIT_STATUS_KEYS)
    if explicit:
        return explicit

    for key in ("status", "state", "workflowState", "workflow_state"):
        status_value = context.get(key)
        text = _text_from_value(status_value)
        if text:
            return text

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _is_status_field(key):
                text = _text_from_value(value)
                if text:
                    return text

    return None


def _extract_text(context: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = context.get(key)
        text = _text_from_value(value)
        if text:
            return text
    return None


def _text_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "key", "id"):
            text = _text_from_value(value.get(key))
            if text:
                return text
    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_token(value: Any) -> str:
    text = _text_from_value(value)
    if text is None:
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    return re.sub(r"[^a-z0-9]+", "", spaced.casefold())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
