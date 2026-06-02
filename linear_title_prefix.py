"""Build Linear issue title updates for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "toStatus",
    "to_status",
    "newWorkflowState",
    "new_workflow_state",
)
_TITLE_KEYS = ("title", "name")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "id", "identifier")
_STATUS_FIELD_NAMES = {
    "status",
    "status id",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue enters research.

    Cursor automations may pass a compact ``triggerContext`` payload, while
    Linear webhooks often nest issue data under ``data`` or ``issue``. This
    function accepts those shapes and returns ``None`` unless the event is a
    status-change event whose new status normalizes to ``to research``.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(contexts)
    title = _extract_title(contexts)
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely event/issue containers in priority order."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")

    add(trigger_context)
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("issue"))
        add(trigger_context.get("data"))
        trigger_data = trigger_context.get("data")
        if isinstance(trigger_data, Mapping):
            add(trigger_data.get("issue"))

    if isinstance(data, Mapping):
        add(data.get("issue"))
    add(issue)
    add(data)
    add(event)

    return contexts


def _is_status_change_event(contexts: Sequence[Mapping[str, Any]]) -> bool:
    direct_markers = ("trigger", "webhookType", "webhook_type", "type", "event", "eventType")
    for context in contexts:
        for key in direct_markers:
            marker = _normalize_text(context.get(key))
            if marker in {"status changed", "status change", "status updated", "status update", "state changed", "state change"}:
                return True

    has_update_action = any(
        _normalize_text(context.get("action")) in {"update", "updated", "updated issue", "issue updated"}
        for context in contexts
    )
    if has_update_action:
        return any(_updated_fields_include_status(context) for context in contexts)

    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields", "updatedFrom", "updated_from"):
        fields = context.get(key)
        if fields is None:
            continue

        if isinstance(fields, Mapping):
            names = fields.keys()
        elif isinstance(fields, str):
            names = re.split(r"[\s,]+", fields)
        elif isinstance(fields, Sequence):
            names = fields
        else:
            continue

        if any(_normalize_text(name) in _STATUS_FIELD_NAMES for name in names):
            return True

    return False


def _extract_new_status(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    explicit_status = _first_nested_text(contexts, _NEW_STATUS_KEYS)
    if explicit_status:
        return explicit_status

    return _first_nested_text(contexts, _STATUS_KEYS)


def _extract_issue_id(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    return _first_nested_text(contexts, _ISSUE_ID_KEYS)


def _extract_title(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    return _first_nested_text(contexts, _TITLE_KEYS)


def _first_nested_text(contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for context in contexts:
        for key in keys:
            text = _coerce_text(context.get(key))
            if text:
                return text
    return None


def _coerce_text(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "id", "identifier"):
            text = _coerce_text(value.get(key))
            if text:
                return text

    return None


def _normalize_text(value: Any) -> str:
    text = _coerce_text(value)
    if not text:
        return ""

    split_camel = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    normalized = re.sub(r"[^a-z0-9]+", " ", split_camel.lower())
    return " ".join(normalized.split())


def main() -> int:
    """Read a JSON payload from stdin and print the requested update, if any."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
