"""Build Linear title updates for Cursor research automation triggers."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = frozenset({"status", "state", "workflowstate", "workflow_state"})


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    payload = _issue_payload(event)
    if not _is_status_change_event(event):
        return None

    status = _new_status(event)
    if _normalize_status(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, ("id", "issueId", "issue_id", "identifier", "key"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    if title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _issue_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge likely issue containers, giving outer trigger data final precedence."""

    merged: dict[str, Any] = {}
    for candidate in _candidate_mappings(event):
        if _looks_like_issue(candidate):
            merged.update(candidate)
    return merged


def _candidate_mappings(value: Any) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []

    def visit(item: Any) -> None:
        if not isinstance(item, Mapping):
            return

        candidates.append(item)
        for key in ("triggerContext", "data", "issue", "node", "object"):
            nested = item.get(key)
            if isinstance(nested, Mapping):
                visit(nested)

    visit(value)
    return candidates


def _looks_like_issue(value: Mapping[str, Any]) -> bool:
    has_id = any(_text(value.get(key)) for key in ("id", "issueId", "issue_id", "identifier", "key"))
    has_title = any(_text(value.get(key)) for key in ("title", "name"))
    return has_id or has_title


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_names = [
        _normalize_event_name(value)
        for candidate in _candidate_mappings(event)
        for value in (
            candidate.get("trigger"),
            candidate.get("webhookType"),
            candidate.get("action"),
            candidate.get("type"),
        )
    ]

    if any(name in {"statuschanged", "statuschange", "statuschangedevent"} for name in event_names):
        return True

    if not any(
        name in {"update", "updated", "issueupdated", "updatedissue", "issueupdate"}
        for name in event_names
    ):
        return False

    return _updated_status_fields(event)


def _updated_status_fields(event: Mapping[str, Any]) -> bool:
    for candidate in _candidate_mappings(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = candidate.get(key)
            if _sequence_has_status_field(fields):
                return True

        changes = candidate.get("changes")
        if isinstance(changes, Mapping):
            if any(_normalize_field_name(key) in STATUS_FIELDS for key in changes):
                return True
        elif _sequence_has_status_field(changes):
            return True

    return False


def _sequence_has_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in STATUS_FIELDS

    if not isinstance(value, Sequence):
        return False

    for item in value:
        if isinstance(item, str) and _normalize_field_name(item) in STATUS_FIELDS:
            return True
        if isinstance(item, Mapping):
            field_name = _first_text(item, ("field", "fieldName", "name", "key"))
            if _normalize_field_name(field_name) in STATUS_FIELDS:
                return True

    return False


def _new_status(event: Mapping[str, Any]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "statusName",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
    )
    fallback_keys = (
        "status",
        "state",
        "workflowState",
        "workflow_state",
    )

    for candidate in _candidate_mappings(event):
        status = _first_status_value(candidate, explicit_keys)
        if status:
            return status

    for candidate in _candidate_mappings(event):
        changes = candidate.get("changes")
        status = _status_from_changes(changes)
        if status:
            return status

    for candidate in _candidate_mappings(event):
        status = _first_status_value(candidate, fallback_keys)
        if status:
            return status

    return None


def _first_status_value(candidate: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        value = candidate.get(key)
        text = _status_text(value)
        if text:
            return text
    return None


def _status_from_changes(changes: Any) -> str | None:
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _normalize_field_name(key) in STATUS_FIELDS:
                text = _changed_to_status(value)
                if text:
                    return text

    if isinstance(changes, Sequence) and not isinstance(changes, str):
        for change in changes:
            if not isinstance(change, Mapping):
                continue

            field_name = _first_text(change, ("field", "fieldName", "name", "key"))
            if _normalize_field_name(field_name) not in STATUS_FIELDS:
                continue

            for key in ("to", "toValue", "newValue", "after", "value", "name"):
                text = _status_text(change.get(key))
                if text:
                    return text

    return None


def _changed_to_status(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "toValue", "newValue", "after", "value", "name"):
            text = _status_text(value.get(key))
            if text:
                return text

    return _status_text(value)


def _status_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _first_text(value, ("name", "title", "value", "label"))
    return _text(value)


def _first_text(mapping: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        text = _text(value)
        if text:
            return text
    return None


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r"(?<!^)(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized.lower()).strip()
    return re.sub(r"\s+", " ", normalized)


def _normalize_event_name(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _normalize_field_name(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is None:
        return 1

    json.dump(update, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
