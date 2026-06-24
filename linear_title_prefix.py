"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}
UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue-title update action when the status moves to research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _extract_contexts(event)
    if not _is_status_change(contexts):
        return None

    status = _first_text(
        _candidate_status_values(context) for context in contexts
    )
    if _normalize_label(status) != _normalize_label(TARGET_STATUS):
        return None

    issue_id = _first_text(_candidate_issue_ids(context) for context in contexts)
    title = _first_text(_candidate_titles(context) for context in contexts)
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _extract_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping):
            contexts.append(value)

    add(event)
    for key in (
        "automation_trigger_info",
        "automationTriggerInfo",
        "triggerContext",
        "trigger_context",
        "webhook",
        "data",
        "issue",
    ):
        add(event.get(key))

    automation_info = event.get("automation_trigger_info") or event.get(
        "automationTriggerInfo"
    )
    if isinstance(automation_info, Mapping):
        for key in ("triggerContext", "trigger_context", "data", "issue"):
            add(automation_info.get(key))

    trigger_context = event.get("triggerContext") or event.get("trigger_context")
    if isinstance(trigger_context, Mapping):
        for key in ("data", "issue"):
            add(trigger_context.get(key))

    if isinstance(automation_info, Mapping):
        trigger_context = automation_info.get("triggerContext") or automation_info.get(
            "trigger_context"
        )
        if isinstance(trigger_context, Mapping):
            for key in ("data", "issue"):
                add(trigger_context.get(key))

    data = event.get("data")
    if isinstance(data, Mapping):
        for key in ("issue", "state", "workflowState", "workflow_state"):
            add(data.get(key))

    issue = _nested_issue(event)
    add(issue)
    if isinstance(issue, Mapping):
        for key in ("state", "workflowState", "workflow_state"):
            add(issue.get(key))

    return contexts


def _nested_issue(event: Mapping[str, Any]) -> Mapping[str, Any] | None:
    for container_key in ("issue", "data", "triggerContext", "trigger_context"):
        container = event.get(container_key)
        if not isinstance(container, Mapping):
            continue
        if "title" in container or "identifier" in container:
            return container
        nested_issue = container.get("issue")
        if isinstance(nested_issue, Mapping):
            return nested_issue
    return None


def _is_status_change(contexts: Sequence[Mapping[str, Any]]) -> bool:
    trigger_values: list[str] = []
    for context in contexts:
        trigger_values.extend(
            _flatten_text_values(
                [
                    context.get(key)
                    for key in (
                        "trigger",
                        "webhookType",
                        "webhook_type",
                        "action",
                        "type",
                    )
                ]
            )
        )

    normalized_triggers = {_normalize_label(value) for value in trigger_values}
    if normalized_triggers & STATUS_CHANGE_TRIGGERS:
        return True

    has_update_trigger = bool(normalized_triggers & UPDATE_TRIGGERS)
    return has_update_trigger and _updated_fields_include_status(contexts)


def _updated_fields_include_status(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            values = _flatten_text_values([context.get(key)])
            if any(_normalize_label(value) in STATUS_FIELDS for value in values):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            if any(_normalize_label(str(key)) in STATUS_FIELDS for key in changes):
                return True
        elif isinstance(changes, Sequence) and not isinstance(changes, (str, bytes)):
            for change in changes:
                if isinstance(change, Mapping):
                    field = change.get("field") or change.get("name") or change.get("key")
                    if _normalize_label(field) in STATUS_FIELDS:
                        return True
                elif _normalize_label(change) in STATUS_FIELDS:
                    return True

    return False


def _candidate_status_values(context: Mapping[str, Any]) -> list[Any]:
    candidates: list[Any] = []
    for key in (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
        "status",
        "state",
        "workflowState",
        "workflow_state",
    ):
        candidates.append(context.get(key))

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for field, change in changes.items():
            if _normalize_label(str(field)) in STATUS_FIELDS:
                candidates.extend(_change_values(change))
    elif isinstance(changes, Sequence) and not isinstance(changes, (str, bytes)):
        for change in changes:
            if not isinstance(change, Mapping):
                continue
            field = change.get("field") or change.get("name") or change.get("key")
            if _normalize_label(field) in STATUS_FIELDS:
                candidates.extend(_change_values(change))

    return candidates


def _change_values(change: Any) -> list[Any]:
    if not isinstance(change, Mapping):
        return [change]
    return [
        change.get("newValue"),
        change.get("new_value"),
        change.get("to"),
        change.get("after"),
        change.get("name"),
        change.get("value"),
    ]


def _candidate_issue_ids(context: Mapping[str, Any]) -> list[Any]:
    return [
        context.get("issueId"),
        context.get("issue_id"),
        context.get("identifier"),
        context.get("key"),
        context.get("id"),
    ]


def _candidate_titles(context: Mapping[str, Any]) -> list[Any]:
    return [
        context.get("title"),
        context.get("issueTitle"),
        context.get("issue_title"),
        context.get("name"),
    ]


def _first_text(value_groups: Any) -> str | None:
    for values in value_groups:
        for value in _flatten_text_values(values):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _flatten_text_values(values: Any) -> list[str]:
    flattened: list[str] = []
    if isinstance(values, Mapping):
        for key in ("name", "title", "value", "label"):
            value = values.get(key)
            if isinstance(value, str):
                flattened.append(value)
    elif isinstance(values, Sequence) and not isinstance(values, (str, bytes)):
        for value in values:
            flattened.extend(_flatten_text_values(value))
    elif isinstance(values, str):
        flattened.append(values)
    return flattened


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_label(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", "", spaced.casefold())


def main() -> int:
    """Read an event JSON document from stdin and print the update action, if any."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
