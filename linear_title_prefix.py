"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "statusAfter",
    "status_after",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
)
_STATUS_FALLBACK_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("id", "issueId", "issue_id", "identifier")
_TRIGGER_KEYS = (
    "trigger",
    "event",
    "action",
    "type",
    "webhookType",
    "webhook_type",
    "webhook",
)
_DIRECT_STATUS_CHANGE_EVENTS = {
    "statuschanged",
    "statuschange",
    "issuestatuschanged",
    "workflowstatechanged",
    "statechanged",
}
_ISSUE_UPDATE_EVENTS = {"update", "updated", "issueupdated", "updatedissue"}
_UPDATED_STATUS_FIELDS = {"status", "state", "workflowstate", "workflow"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters research.

    The automation trigger can provide a flat ``triggerContext`` payload, while
    direct Linear webhooks commonly nest issue fields under ``data`` or
    ``issue``. This function intentionally accepts both shapes.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_contexts(event)
    if not _is_status_change_event(event, contexts):
        return None

    status = _extract_status(contexts)
    if _normalize_status(status) != RESEARCH_STATUS:
        return None

    issue_id = _extract_first_string(contexts, _ISSUE_ID_KEYS)
    title = _extract_first_string(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if _has_title_prefix(clean_title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(mapping: Any) -> None:
        if isinstance(mapping, Mapping) and mapping not in contexts:
            contexts.append(mapping)

    def add_nested(mapping: Any) -> None:
        if not isinstance(mapping, Mapping):
            return
        add(mapping)
        for key in ("triggerContext", "data", "issue"):
            nested = mapping.get(key)
            if isinstance(nested, Mapping):
                add(nested)
        data = mapping.get("data")
        if isinstance(data, Mapping):
            add(data.get("issue"))
        trigger_context = mapping.get("triggerContext")
        if isinstance(trigger_context, Mapping):
            add(trigger_context.get("data"))
            add(trigger_context.get("issue"))
            trigger_data = trigger_context.get("data")
            if isinstance(trigger_data, Mapping):
                add(trigger_data.get("issue"))

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        add_nested(trigger_context)

    add_nested(event)
    return contexts


def _is_status_change_event(
    event: Mapping[str, Any], contexts: Sequence[Mapping[str, Any]]
) -> bool:
    for context in contexts:
        for key in _TRIGGER_KEYS:
            marker = _normalize_marker(context.get(key))
            if marker in _DIRECT_STATUS_CHANGE_EVENTS:
                return True
            if marker in _ISSUE_UPDATE_EVENTS and _updated_fields_include_status(event):
                return True
    return False


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    values = _collect_values_for_keys(event, ("updatedFields", "updated_fields"))
    for value in values:
        if isinstance(value, str) and _normalize_marker(value) in _UPDATED_STATUS_FIELDS:
            return True
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            for field in value:
                if _normalize_marker(field) in _UPDATED_STATUS_FIELDS:
                    return True
    return False


def _extract_status(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    for key_group in (_STATUS_KEYS, _STATUS_FALLBACK_KEYS):
        for context in contexts:
            status = _extract_status_value(context, key_group)
            if status:
                return status
    return None


def _extract_status_value(context: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        if key not in context:
            continue
        value = context.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, Mapping):
            nested = _extract_first_string((value,), ("name", "title", "id"))
            if nested:
                return nested
    return None


def _extract_first_string(
    contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]
) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _collect_values_for_keys(mapping: Mapping[str, Any], keys: Sequence[str]) -> list[Any]:
    values: list[Any] = []

    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, nested in value.items():
                if key in keys:
                    values.append(nested)
                walk(nested)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            for nested in value:
                walk(nested)

    walk(mapping)
    return values


def _normalize_status(value: str | None) -> str:
    if not value:
        return ""
    normalized = _split_camel_case(value)
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", normalized)
    return " ".join(normalized.lower().split())


def _normalize_marker(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", _split_camel_case(value).lower())


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def _has_title_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    json.dump(action, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
