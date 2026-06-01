"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
_TRIGGER_KEYS = {"trigger", "action", "type", "webhooktype", "webhook_type"}
_UPDATED_FIELD_KEYS = {
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
    "updatedFrom",
    "updated_from",
}


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    candidates = _candidate_payloads(event)
    if not _is_status_change_event(candidates):
        return None

    new_status = _extract_new_status(candidates)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(candidates, ("id", "issueId", "issue_id", "identifier"))
    title = _extract_first_text(candidates, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Any) -> dict[str, str] | None:
    """Compatibility wrapper for snake_case callers."""

    return build_issue_title_update(event)


def handleIssueStatusChanged(event: Any) -> dict[str, str] | None:
    """Compatibility wrapper for camelCase callers."""

    return build_issue_title_update(event)


def _candidate_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload layers from most automation-specific to most nested."""

    candidates: list[Mapping[str, Any]] = []

    trigger_context = _mapping_at(event, "triggerContext")
    if trigger_context is not None:
        candidates.append(trigger_context)

    candidates.append(event)

    data = _mapping_at(event, "data")
    issue = _mapping_at(event, "issue")

    if data is not None:
        candidates.append(data)
        data_issue = _mapping_at(data, "issue")
        if data_issue is not None:
            candidates.append(data_issue)

    if issue is not None:
        candidates.append(issue)

    return candidates


def _is_status_change_event(candidates: list[Mapping[str, Any]]) -> bool:
    trigger_values: list[str] = []
    for payload in candidates:
        for key, value in payload.items():
            if _canonical_key(key) in _TRIGGER_KEYS:
                text = _text(value)
                if text:
                    trigger_values.append(_normalize_text(text))

    if any(value in {"status changed", "status change"} for value in trigger_values):
        return True

    has_issue_update = any(
        value in {"update", "updated", "issue updated", "updated issue"} for value in trigger_values
    )
    return has_issue_update and _updated_fields_include_status(candidates)


def _updated_fields_include_status(candidates: list[Mapping[str, Any]]) -> bool:
    for payload in candidates:
        for key, value in payload.items():
            if key in _UPDATED_FIELD_KEYS:
                if _field_collection_mentions_status(value):
                    return True
    return False


def _field_collection_mentions_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value)
    if isinstance(value, (list, tuple, set)):
        return any(_field_collection_mentions_status(item) for item in value)

    text = _text(value)
    return bool(text and _is_status_field(text))


def _is_status_field(value: str) -> bool:
    normalized = _canonical_key(value.split(".", 1)[0])
    return normalized in _STATUS_FIELDS


def _extract_new_status(candidates: list[Mapping[str, Any]]) -> str | None:
    status = _extract_first_text(
        candidates,
        (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "newWorkflowState",
            "new_workflow_state",
        ),
    )
    if status:
        return status

    for payload in candidates:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = payload.get(key)
            status = _text(value)
            if status:
                return status

    return None


def _extract_first_text(candidates: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for payload in candidates:
        for key in keys:
            value = payload.get(key)
            text = _text(value)
            if text:
                return text
    return None


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "id", "identifier"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested
    return None


def _mapping_at(payload: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    value = payload.get(key)
    return value if isinstance(value, Mapping) else None


def _normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    spaced = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return " ".join(spaced.lower().split())


def _canonical_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
