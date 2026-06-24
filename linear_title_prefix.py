"""Build Linear issue title update actions for research status changes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_TOKENS = {"status", "state", "workflowstate"}
_DIRECT_STATUS_CHANGE_TOKENS = {
    "statuschange",
    "statuschanged",
    "statusupdated",
    "statechange",
    "statechanged",
    "workflowstatechange",
    "workflowstatechanged",
}
_ISSUE_UPDATE_TOKENS = {"issueupdate", "issueupdated", "updatedissue", "update"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action when an issue moves to research."""
    if not isinstance(event, Mapping) or not _is_status_change_event(event):
        return None

    new_status = _new_status(event)
    if _normalize_status(new_status) != TARGET_STATUS:
        return None

    issue_id = _issue_text(event, ("id", "issueId", "issue_id", "identifier", "key"))
    title = _issue_text(event, ("title",))
    if issue_id is None or title is None:
        return None

    issue_id = issue_id.strip()
    title = title.strip()
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_tokens = {
        token
        for context in _metadata_contexts(event)
        for token in (
            _normalize_token(context.get(key))
            for key in ("trigger", "action", "type", "webhookType", "webhook_type")
        )
        if token
    }

    if trigger_tokens & _DIRECT_STATUS_CHANGE_TOKENS:
        return True

    if trigger_tokens & _ISSUE_UPDATE_TOKENS:
        return _has_status_field_change(event)

    return _has_status_field_change(event)


def _has_status_field_change(value: Any, *, inspect_keys: bool = False) -> bool:
    if isinstance(value, str):
        return _normalize_token(value) in _STATUS_FIELD_TOKENS

    if isinstance(value, Mapping):
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
            "changes",
            "updatedFrom",
            "updated_from",
        ):
            if key in value and _has_status_field_change(value[key], inspect_keys=True):
                return True

        if inspect_keys and any(
            isinstance(key, str) and _normalize_token(key) in _STATUS_FIELD_TOKENS
            for key in value.keys()
        ):
            return True

        field = value.get("field") or value.get("name") or value.get("key")
        if isinstance(field, str) and _normalize_token(field) in _STATUS_FIELD_TOKENS:
            return True

        return False

    if isinstance(value, Iterable):
        return any(_has_status_field_change(item, inspect_keys=inspect_keys) for item in value)

    return False


def _new_status(event: Mapping[str, Any]) -> str | None:
    for context in _status_contexts(event):
        explicit = _first_text(
            context,
            (
                "newStatus",
                "new_status",
                "statusName",
                "status_name",
                "newState",
                "new_state",
                "newWorkflowState",
                "new_workflow_state",
            ),
        )
        if explicit:
            return explicit

    changed_status = _status_from_changes(event)
    if changed_status:
        return changed_status

    for context in _status_contexts(event):
        fallback = _first_text(
            context,
            ("status", "state", "workflowState", "workflow_state"),
            nested=(("status", "name"), ("state", "name"), ("workflowState", "name")),
        )
        if fallback:
            return fallback

    return None


def _status_from_changes(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, changed_value in value.items():
            if isinstance(key, str) and _normalize_token(key) in _STATUS_FIELD_TOKENS:
                if isinstance(changed_value, str):
                    return changed_value
                if isinstance(changed_value, Mapping):
                    changed_to = _first_text(
                        changed_value,
                        ("newValue", "new_value", "to", "after", "value", "name"),
                        nested=(("to", "name"), ("after", "name"), ("value", "name")),
                    )
                    if changed_to:
                        return changed_to

        field = value.get("field") or value.get("name") or value.get("key")
        if isinstance(field, str) and _normalize_token(field) in _STATUS_FIELD_TOKENS:
            changed_to = _first_text(
                value,
                (
                    "newValue",
                    "new_value",
                    "to",
                    "after",
                    "value",
                    "name",
                    "status",
                ),
                nested=(("to", "name"), ("after", "name"), ("value", "name")),
            )
            if changed_to:
                return changed_to

        for key in ("changes", "updatedFields", "updated_fields"):
            if key in value:
                changed_status = _status_from_changes(value[key])
                if changed_status:
                    return changed_status

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for item in value:
            changed_status = _status_from_changes(item)
            if changed_status:
                return changed_status

    return None


def _issue_text(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for context in _issue_contexts(event):
        value = _first_text(context, keys)
        if value:
            return value
    return None


def _issue_contexts(event: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    contexts: list[Mapping[str, Any]] = []
    _append_mapping(contexts, event.get("triggerContext"))
    _append_mapping(contexts, _nested_mapping(event, ("triggerContext", "issue")))
    _append_mapping(contexts, _nested_mapping(event, ("data", "issue")))
    _append_mapping(contexts, event.get("issue"))
    _append_mapping(contexts, event.get("data"))
    contexts.append(event)
    return tuple(contexts)


def _status_contexts(event: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    contexts: list[Mapping[str, Any]] = []
    for context in _issue_contexts(event):
        _append_mapping(contexts, context)
    return tuple(contexts)


def _metadata_contexts(event: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    contexts: list[Mapping[str, Any]] = [event]
    _append_mapping(contexts, event.get("triggerContext"))
    _append_mapping(contexts, event.get("data"))
    return tuple(contexts)


def _append_mapping(contexts: list[Mapping[str, Any]], value: Any) -> None:
    if isinstance(value, Mapping) and value not in contexts:
        contexts.append(value)


def _nested_mapping(event: Mapping[str, Any], path: tuple[str, ...]) -> Mapping[str, Any] | None:
    current: Any = event
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, Mapping) else None


def _first_text(
    payload: Mapping[str, Any],
    keys: tuple[str, ...],
    *,
    nested: tuple[tuple[str, str], ...] = (),
) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, Mapping):
            nested_name = value.get("name")
            if isinstance(nested_name, str):
                return nested_name

    for parent_key, child_key in nested:
        parent = payload.get(parent_key)
        if isinstance(parent, Mapping):
            value = parent.get(child_key)
            if isinstance(value, str):
                return value

    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    words = re.sub(r"[^a-zA-Z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", words)


def _normalize_token(value: Any) -> str | None:
    status = _normalize_status(value)
    return None if status is None else status.replace(" ", "")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a Linear issue title update action from a webhook payload."
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to a JSON payload file. Reads from stdin when omitted.",
    )
    args = parser.parse_args()

    raw_payload = (
        sys.stdin.read()
        if args.input is None
        else Path(args.input).read_text(encoding="utf-8")
    )
    event = json.loads(raw_payload)
    action = build_issue_title_update(event)
    print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
