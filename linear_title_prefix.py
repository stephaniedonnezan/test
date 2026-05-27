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
    """Return a Linear title update when an issue moves to To Research.

    The automation runner passes slightly different payload shapes depending on
    the trigger source. This function accepts flat trigger contexts as well as
    nested Linear webhook payloads and returns a small action object for the
    caller to apply.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change(contexts):
        return None

    status = _extract_status(contexts)
    if not _is_research_status(status):
        return None

    issue_id = _extract_text(contexts, ("id", "issueId", "issue_id", "identifier"))
    title = _extract_text(contexts, ("title",))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if stripped_title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {stripped_title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event.get("triggerContext"))
    add(event)
    data = event.get("data")
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))
    add(event.get("issue"))

    return contexts


def _is_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "webhookType"):
            if _normalize(context.get(key)) in {"status changed", "status change"}:
                return True

        normalized_action = _normalize(context.get("action"))
        normalized_type = _normalize(context.get("type"))
        if normalized_action in {"update", "issue updated", "updated issue"}:
            if _has_status_updated_field(context):
                return True
        if normalized_type in {"issue updated", "updated issue", "status changed"}:
            if normalized_type == "status changed" or _has_status_updated_field(context):
                return True

    return False


def _has_status_updated_field(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = context.get(key)
        if isinstance(fields, str):
            field_values = [fields]
        elif isinstance(fields, list | tuple | set):
            field_values = fields
        else:
            continue

        for field in field_values:
            if _normalize(field) in STATUS_FIELDS:
                return True

    return any(
        key in context
        for key in (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "newWorkflowState",
            "new_workflow_state",
        )
    )


def _extract_status(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    for key_group in (explicit_keys, fallback_keys):
        for context in contexts:
            for key in key_group:
                value = context.get(key)
                text = _text_from_value(value)
                if text:
                    return text

    return None


def _extract_text(
    contexts: list[Mapping[str, Any]], keys: tuple[str, ...]
) -> str | None:
    for context in contexts:
        for key in keys:
            text = _text_from_value(context.get(key))
            if text:
                return text
    return None


def _text_from_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "id", "identifier"):
            text = _text_from_value(value.get(key))
            if text:
                return text
        return None

    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    return None


def _is_research_status(status: str | None) -> bool:
    return _normalize(status) == RESEARCH_STATUS


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", words)


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
