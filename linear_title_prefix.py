"""Build Linear issue title updates for Cursor research status changes.

The automation runtime can pass either a compact Cursor trigger context or a
more native Linear webhook payload. This module keeps the matching logic local
and returns a declarative action that the caller can execute against Linear.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate", "state id", "stateid"}
DIRECT_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflowstate changed",
    "workflow state change",
}
GENERIC_UPDATE_TRIGGERS = {"update", "updated", "issue update", "issue updated", "updated issue"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action for status changes to To Research.

    The result is intentionally side-effect free so the webhook runner can test
    the decision before applying the Linear mutation.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_target_status(event)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_string(event, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _extract_first_string(event, ("title", "name"))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if _has_research_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{RESEARCH_PREFIX}: {clean_title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility alias for webhook entrypoints."""

    return build_issue_title_update(event)


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_names = {_normalize_text(value) for value in _iter_named_values(event, ("trigger", "webhookType", "action", "type"))}
    trigger_names.discard("")

    if trigger_names & DIRECT_STATUS_CHANGE_TRIGGERS:
        return True

    if trigger_names & GENERIC_UPDATE_TRIGGERS:
        return _payload_mentions_status_change(event)

    return False


def _payload_mentions_status_change(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = _normalize_text(key)
            if normalized_key in {"updated fields", "updatedfields"}:
                if _contains_status_field_name(child):
                    return True
            if normalized_key in {"changes", "changed", "updated from", "updatedfrom"}:
                if _contains_status_field_name(child):
                    return True
            if isinstance(child, (Mapping, list, tuple)):
                if _payload_mentions_status_change(child):
                    return True
    elif _is_sequence(value):
        return any(_payload_mentions_status_change(item) for item in value)

    return False


def _contains_status_field_name(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if _is_status_field_name(key):
                return True
            if _contains_status_field_name(child):
                return True
    elif _is_sequence(value):
        return any(_contains_status_field_name(item) for item in value)
    elif isinstance(value, str):
        return _is_status_field_name(value)

    return False


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_text(value)
    return normalized in STATUS_FIELD_NAMES or normalized.endswith(" status") or normalized.endswith(" state")


def _extract_target_status(event: Mapping[str, Any]) -> str | None:
    explicit_status_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "statusName",
        "stateName",
        "workflowStateName",
    )
    for value in _iter_named_values(event, explicit_status_keys):
        status = _string_or_name(value)
        if status:
            return status

    for value in _iter_named_values(event, ("changes", "changed")):
        status = _extract_status_from_change_set(value)
        if status:
            return status

    for value in _iter_named_values(event, ("status", "state", "workflowState", "workflow_state")):
        status = _string_or_name(value)
        if status:
            return status

    return None


def _extract_status_from_change_set(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if _is_status_field_name(key):
                status = _string_or_name(child)
                if status:
                    return status

                if isinstance(child, Mapping):
                    for target_key in ("to", "toName", "new", "newValue", "after", "current", "name", "title"):
                        status = _string_or_name(child.get(target_key))
                        if status:
                            return status

            status = _extract_status_from_change_set(child)
            if status:
                return status
    elif _is_sequence(value):
        for item in value:
            status = _extract_status_from_change_set(item)
            if status:
                return status

    return None


def _extract_first_string(event: Mapping[str, Any], names: Sequence[str]) -> str | None:
    for value in _iter_named_values(event, names):
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)

    return None


def _iter_named_values(value: Any, names: Iterable[str]) -> Iterable[Any]:
    wanted = {_normalize_key(name) for name in names}
    yield from _iter_named_values_from(value, wanted)


def _iter_named_values_from(value: Any, wanted: set[str]) -> Iterable[Any]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if _normalize_key(key) in wanted:
                yield child
            if isinstance(child, (Mapping, list, tuple)):
                yield from _iter_named_values_from(child, wanted)
    elif _is_sequence(value):
        for item in value:
            yield from _iter_named_values_from(item, wanted)


def _string_or_name(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            child = value.get(key)
            if isinstance(child, str) and child.strip():
                return child
    return None


def _has_research_prefix(title: str) -> bool:
    return _normalize_text(title).startswith(RESEARCH_PREFIX.lower())


def _normalize_key(value: Any) -> str:
    return re.sub(r"[\W_]+", "", str(value)).lower()


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def main() -> int:
    """Read an event JSON document from stdin and print the update action."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2

    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
