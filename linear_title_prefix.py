"""Build Linear issue title update actions for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}
STATUS_TRIGGER_TOKENS = {"statuschanged", "statechanged", "workflowstatechanged"}
GENERIC_UPDATE_TOKENS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue moves to research.

    The automation payload can be either the flat Cursor trigger context or a
    nested Linear webhook payload. If the event is not a status-change transition
    to "to research", or the title is already prefixed, no action is returned.
    """

    if not isinstance(event, Mapping):
        return None

    candidates = list(_candidate_mappings(event))
    if not _is_status_change_event(event, candidates):
        return None

    new_status = _extract_new_status(event, candidates)
    if _normalize_label(new_status) != _normalize_label(TARGET_STATUS):
        return None

    issue_id = _first_text(candidates, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(candidates, ("title",))
    if issue_id is None or title is None:
        return None

    stripped_title = title.strip()
    if not stripped_title or _has_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {stripped_title}",
    }


def _candidate_mappings(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely payload contexts from most specific trigger data to issue data."""

    seen: set[int] = set()

    def emit(value: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            yield value

    for key in ("triggerContext", "trigger_context"):
        yield from emit(event.get(key))

    for key in ("data", "issue"):
        nested = event.get(key)
        yield from emit(nested)
        if isinstance(nested, Mapping):
            yield from emit(nested.get("issue"))
            yield from emit(nested.get("data"))

    yield from emit(event)


def _is_status_change_event(
    event: Mapping[str, Any], candidates: Iterable[Mapping[str, Any]]
) -> bool:
    event_tokens = {
        _normalize_token(value)
        for candidate in candidates
        for key in ("trigger", "webhookType", "webhook_type", "action", "type", "eventType")
        if isinstance((value := candidate.get(key)), str)
    }
    event_tokens.discard("")

    if event_tokens & STATUS_TRIGGER_TOKENS:
        return True

    if event_tokens & GENERIC_UPDATE_TOKENS:
        return _updated_fields_include_status(event)

    return False


def _updated_fields_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized_key = _normalize_token(str(key))
            if normalized_key in {"updatedfields", "changedfields"}:
                if _field_list_contains_status(item):
                    return True
            if normalized_key in {"changes", "updated", "changed"} and isinstance(item, Mapping):
                if any(_normalize_token(str(field)) in STATUS_FIELD_NAMES for field in item):
                    return True
            if _updated_fields_include_status(item):
                return True
    elif isinstance(value, list):
        return any(_updated_fields_include_status(item) for item in value)

    return False


def _field_list_contains_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_token(value) in STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        return any(_field_list_contains_status(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_field_list_contains_status(item) for item in value)
    return False


def _extract_new_status(
    event: Mapping[str, Any], candidates: Iterable[Mapping[str, Any]]
) -> str | None:
    status = _first_status_value(
        candidates,
        (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "newState",
            "new_state",
            "toState",
            "to_state",
            "newWorkflowState",
            "new_workflow_state",
        ),
    )
    if status is not None:
        return status

    changed_status = _extract_changed_status(event)
    if changed_status is not None:
        return changed_status

    return _first_status_value(
        candidates,
        ("status", "state", "workflowState", "workflow_state"),
    )


def _extract_changed_status(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized_key = _normalize_token(str(key))
            if normalized_key in STATUS_FIELD_NAMES:
                status = _change_value_to_text(item)
                if status is not None:
                    return status
            if normalized_key in {"changes", "updated", "changed"}:
                status = _extract_changed_status(item)
                if status is not None:
                    return status
        for item in value.values():
            status = _extract_changed_status(item)
            if status is not None:
                return status
    elif isinstance(value, list):
        for item in value:
            status = _extract_changed_status(item)
            if status is not None:
                return status

    return None


def _change_value_to_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in (
            "newValue",
            "new_value",
            "to",
            "after",
            "value",
            "name",
            "title",
        ):
            text = _value_to_text(value.get(key))
            if text is not None:
                return text
    return None


def _first_status_value(
    candidates: Iterable[Mapping[str, Any]], keys: tuple[str, ...]
) -> str | None:
    for candidate in candidates:
        for key in keys:
            text = _value_to_text(candidate.get(key))
            if text is not None:
                return text
    return None


def _first_text(
    candidates: Iterable[Mapping[str, Any]], keys: tuple[str, ...]
) -> str | None:
    for candidate in candidates:
        for key in keys:
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _value_to_text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _value_to_text(value.get(key))
            if text is not None:
                return text
    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_label(value: str | None) -> str:
    if value is None:
        return ""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _normalize_label(value))


def main() -> int:
    """Read a JSON event from stdin and print the update action, if any."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
