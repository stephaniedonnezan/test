"""Build Linear issue title updates for Cursor research automation.

The automation receives Linear webhook payloads in slightly different shapes
depending on whether they come from Cursor trigger context or directly from
Linear. This module keeps the title update decision pure and side-effect free:
it returns the update that should be applied, or ``None`` when the event should
be ignored.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflow state",
}
STATUS_VALUE_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "toStatus",
    "to_status",
    "toState",
    "to_state",
    "status",
    "state",
    "workflowState",
    "workflow_state",
)


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue-title update for status changes to "to research".

    The returned dictionary is intentionally generic so a caller can translate
    it to the concrete Linear API call:
    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _collect_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_text(new_status) != _normalize_text(TARGET_STATUS):
        return None

    issue_id = _extract_first_text(contexts, ("identifier", "key", "issueId", "issue_id", "id"))
    title = _extract_first_text(contexts, ("title", "issueTitle", "issue_title"))
    if issue_id is None or title is None:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": _prefix_title(title),
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Backward-compatible alias for callers using a handler-style name."""

    return build_issue_title_update(event)


def _collect_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        if value not in contexts:
            contexts.append(value)

    visit(event)
    visit(event.get("automation_trigger_info"))
    visit(event.get("automationTriggerInfo"))

    for key in ("triggerContext", "trigger_context"):
        value = event.get(key)
        visit(value)
        if isinstance(value, Mapping):
            visit(value.get("data"))
            visit(value.get("issue"))

    for root_key in ("automation_trigger_info", "automationTriggerInfo"):
        root = event.get(root_key)
        if isinstance(root, Mapping):
            for key in ("triggerContext", "trigger_context"):
                value = root.get(key)
                visit(value)
                if isinstance(value, Mapping):
                    visit(value.get("data"))
                    visit(value.get("issue"))

    for key in ("data", "issue"):
        value = event.get(key)
        visit(value)
        if isinstance(value, Mapping):
            visit(value.get("issue"))

    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    trigger_values = _extract_all_text(
        contexts,
        ("trigger", "action", "type", "event", "eventType", "event_type", "webhookType", "webhook_type"),
    )
    normalized_triggers = {_normalize_text(value) for value in trigger_values}

    if any(_is_direct_status_change_trigger(value) for value in normalized_triggers):
        return True

    is_update_event = any(_is_update_trigger(value) for value in normalized_triggers)
    return is_update_event and _has_status_change_marker(contexts)


def _is_direct_status_change_trigger(value: str) -> bool:
    return value in {
        "status changed",
        "state changed",
        "workflow state changed",
        "issue status changed",
        "issue state changed",
        "issue workflow state changed",
    }


def _is_update_trigger(value: str) -> bool:
    return value in {
        "update",
        "updated",
        "issue update",
        "issue updated",
        "updated issue",
    }


def _has_status_change_marker(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(context.get(key)):
                return True

        for key in ("changes", "change", "updatedFrom", "updated_from"):
            if _mapping_has_status_key(context.get(key)):
                return True

    return False


def _contains_status_field(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return _normalize_field_name(value) in STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        return any(
            _normalize_field_name(key) in STATUS_FIELD_NAMES
            or _contains_status_field(item)
            for key, item in value.items()
        )
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _mapping_has_status_key(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    return any(_normalize_field_name(key) in STATUS_FIELD_NAMES for key in value)


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> Any:
    for context in contexts:
        for key in STATUS_VALUE_KEYS:
            value = context.get(key)
            if value is not None:
                return _name_from_value(value)

        for key in ("changes", "change"):
            changed_status = _extract_status_from_change_map(context.get(key))
            if changed_status is not None:
                return changed_status

    return None


def _extract_status_from_change_map(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return None

    for key, change in value.items():
        if _normalize_field_name(key) not in STATUS_FIELD_NAMES:
            continue
        if isinstance(change, Mapping):
            for candidate_key in ("newValue", "new_value", "to", "after", "name"):
                candidate = change.get(candidate_key)
                if candidate is not None:
                    return _name_from_value(candidate)
        return _name_from_value(change)

    return None


def _name_from_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state"):
            if value.get(key) is not None:
                return _name_from_value(value[key])
        return None
    return value


def _extract_first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for key in keys:
        for context in contexts:
            value = context.get(key)
            text = _coerce_non_empty_text(value)
            if text is not None:
                return text
    return None


def _extract_all_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> list[str]:
    values: list[str] = []
    for context in contexts:
        for key in keys:
            text = _coerce_non_empty_text(context.get(key))
            if text is not None:
                values.append(text)
    return values


def _prefix_title(title: str) -> str:
    stripped_title = title.strip()
    if re.match(rf"^{re.escape(TITLE_PREFIX)}\b", stripped_title, flags=re.IGNORECASE):
        return stripped_title
    return f"{TITLE_PREFIX}: {stripped_title}"


def _normalize_text(value: Any) -> str:
    text = _coerce_non_empty_text(value)
    if text is None:
        return ""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def _normalize_field_name(value: Any) -> str:
    normalized = _normalize_text(value)
    return normalized.replace(" ", "") if normalized == "workflow state" else normalized


def _coerce_non_empty_text(value: Any) -> str | None:
    if value is None or isinstance(value, (Mapping, list, tuple, set)):
        return None
    text = str(value).strip()
    return text or None


def main() -> int:
    """Read a JSON event from stdin and print the title update or ``null``."""

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": f"invalid json: {exc}"}))
        return 1

    print(json.dumps(build_issue_title_update(payload), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
