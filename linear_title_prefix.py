"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_contexts(event)
    if not _is_status_change(contexts):
        return None

    new_status = _first_status(contexts)
    if _normalize(new_status) != RESEARCH_STATUS:
        return None

    issue_id = _first_string(contexts, ("id", "issueId", "issue_id", "identifier", "key"))
    title = _first_string(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event.get("triggerContext"))
    add(event)
    add(event.get("data"))
    add(event.get("issue"))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("node"))

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("data"))
        add(trigger_context.get("issue"))

    return contexts


def _is_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    triggers = []
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            value = context.get(key)
            if isinstance(value, str):
                triggers.append(_normalize(value))

    if any(value in {"status changed", "status change", "statuschanged"} for value in triggers):
        return True

    if any(value in {"update", "updated", "issue updated", "updated issue"} for value in triggers):
        return _changed_status_field(contexts)

    return False


def _changed_status_field(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        updated_fields = context.get("updatedFields")
        if isinstance(updated_fields, list) and any(_is_status_field(field) for field in updated_fields):
            return True

        changes = context.get("changes")
        if isinstance(changes, Mapping) and any(_is_status_field(field) for field in changes):
            return True

        updated_from = context.get("updatedFrom")
        if isinstance(updated_from, Mapping) and any(_is_status_field(field) for field in updated_from):
            return True

    return False


def _first_status(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit_status = _first_string(
        contexts,
        (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "newWorkflowState",
            "new_workflow_state",
        ),
    )
    if explicit_status:
        return explicit_status

    for context in contexts:
        for key in ("status", "state", "workflowState"):
            value = context.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, Mapping):
                name = value.get("name")
                if isinstance(name, str):
                    return name

    changes = _first_mapping(contexts, ("changes",))
    if changes:
        for key in ("status", "state", "workflowState"):
            value = changes.get(key)
            status = _status_from_change(value)
            if status:
                return status

    return None


def _status_from_change(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if not isinstance(value, Mapping):
        return None

    for key in ("to", "after", "newValue", "new", "name"):
        candidate = value.get(key)
        if isinstance(candidate, str):
            return candidate
        if isinstance(candidate, Mapping):
            name = candidate.get("name")
            if isinstance(name, str):
                return name

    return None


def _first_string(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _first_mapping(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> Mapping[str, Any] | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, Mapping):
                return value
    return None


def _is_status_field(value: Any) -> bool:
    if not isinstance(value, str):
        return False

    normalized = _normalize(value)
    return normalized in STATUS_FIELDS or normalized.endswith("status") or normalized.endswith("state")


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return " ".join(value.lower().split())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is None:
        return 1

    json.dump(update, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
