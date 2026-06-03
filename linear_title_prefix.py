"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters "to research"."""
    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _first_matching_status(_event_contexts(event)) != TARGET_STATUS:
        return None

    issue_id = _first_string(_event_contexts(event), ("issueId", "issue_id", "identifier", "id"))
    title = _first_string(_event_contexts(event), ("title",))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if not clean_title or _has_research_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{RESEARCH_PREFIX}: {clean_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    contexts = list(_event_contexts(event))

    for context in contexts:
        for key in ("trigger", "webhookType"):
            value = _normalized_text(context.get(key))
            if value in {"status changed", "status change"}:
                return True

    if not _has_issue_update_action(contexts):
        return False

    updated_fields = _updated_fields(contexts)
    return bool(updated_fields & STATUS_FIELDS)


def _has_issue_update_action(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("action", "type", "webhookType", "trigger"):
            value = _normalized_text(context.get(key))
            if value in {"update", "updated", "issue update", "issue updated", "updated issue"}:
                return True
    return False


def _updated_fields(contexts: Iterable[Mapping[str, Any]]) -> set[str]:
    fields: set[str] = set()
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields.update(_normalized_field_names(context.get(key)))
        updated_from = context.get("updatedFrom") or context.get("updated_from")
        if isinstance(updated_from, Mapping):
            fields.update(_normalized_field_names(updated_from.keys()))
    return fields


def _first_matching_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    explicit_status_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "statusName",
        "stateName",
        "workflowStateName",
    )
    fallback_status_keys = ("status", "state", "workflowState", "workflow_state")

    context_list = list(contexts)
    for keys in (explicit_status_keys, fallback_status_keys):
        for context in context_list:
            for key in keys:
                status = _status_value(context.get(key))
                if status == TARGET_STATUS:
                    return status
    return None


def _event_contexts(event: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    contexts: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)

    automation_info = event.get("automation_trigger_info") or event.get("automationTriggerInfo")
    if isinstance(automation_info, Mapping):
        automation_trigger_context = automation_info.get("triggerContext")
        if isinstance(automation_trigger_context, Mapping):
            contexts.append(automation_trigger_context)
        contexts.append(automation_info)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            contexts.append(issue)
        contexts.append(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        contexts.append(issue)

    contexts.append(event)
    return tuple(contexts)


def _first_string(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _status_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _status_value(value.get("name") or value.get("title"))
    if isinstance(value, str):
        normalized = _normalized_text(value)
        if normalized:
            return normalized
    return None


def _normalized_field_names(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {_normalized_status_field(value)}
    if isinstance(value, Iterable) and not isinstance(value, (bytes, str)):
        return {_normalized_status_field(field) for field in value if isinstance(field, str)}
    return set()


def _normalized_status_field(value: str) -> str:
    normalized = _normalized_text(value)
    if normalized.endswith(" id"):
        normalized = normalized[:-3]
    return normalized


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(RESEARCH_PREFIX.lower())


def _normalized_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    camel_spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    separated = re.sub(r"[_\-.]+", " ", camel_spaced)
    return re.sub(r"\s+", " ", separated).strip().lower()


def main() -> int:
    """Read a JSON payload from stdin and print the computed action."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": f"invalid JSON: {exc.msg}"}), file=sys.stderr)
        return 1

    print(json.dumps(build_issue_title_update(event), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
