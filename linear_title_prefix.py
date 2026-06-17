"""Build title-update actions for Linear issues entering research status."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_TOKENS = {"status", "state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters research status.

    The automation trigger can provide a flat Cursor `triggerContext` payload or
    a nested Linear webhook payload. This function accepts both and returns a
    small action dictionary that the automation runner can apply.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _context_chain(event)
    if not _is_status_change_event(contexts):
        return None

    status = _first_status_value(contexts)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    title = _first_text(contexts, ("title", "name"))
    issue_id = _first_text(
        contexts,
        ("identifier", "key", "issueId", "issue_id"),
        fallback_keys=("id",),
    )
    if not title or not issue_id:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _context_chain(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = [event]

    for key in ("triggerContext", "trigger_context", "data", "issue", "payload"):
        value = event.get(key)
        if isinstance(value, Mapping):
            contexts.append(value)

    for parent_key, child_key in (
        ("triggerContext", "data"),
        ("triggerContext", "issue"),
        ("data", "issue"),
        ("data", "node"),
        ("payload", "issue"),
        ("payload", "data"),
    ):
        parent = event.get(parent_key)
        if isinstance(parent, Mapping):
            child = parent.get(child_key)
            if isinstance(child, Mapping):
                contexts.append(child)

    deduped: list[Mapping[str, Any]] = []
    seen: set[int] = set()
    for context in contexts:
        context_id = id(context)
        if context_id not in seen:
            seen.add(context_id)
            deduped.append(context)
    return deduped


def _is_status_change_event(contexts: Sequence[Mapping[str, Any]]) -> bool:
    event_tokens: list[str] = []
    for context in contexts:
        for key in ("trigger", "webhookType", "webhook_type", "action", "type"):
            token = _normalize_token(context.get(key))
            if token:
                event_tokens.append(token)

    if any(token in {"statuschanged", "statuschange"} for token in event_tokens):
        return True

    if any(
        token in {"update", "updated", "issueupdate", "issueupdated", "updatedissue"}
        for token in event_tokens
    ):
        return _updated_fields_include_status(contexts)

    return False


def _updated_fields_include_status(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
        ):
            if _fields_include_status(context.get(key)):
                return True

        for key in ("changes", "updatedFrom", "updated_from"):
            value = context.get(key)
            if isinstance(value, Mapping) and any(
                _normalize_token(field) in STATUS_FIELD_TOKENS for field in value
            ):
                return True

    return False


def _fields_include_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_token(value) in STATUS_FIELD_TOKENS

    if isinstance(value, Mapping):
        return any(_normalize_token(key) in STATUS_FIELD_TOKENS for key in value)

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            if isinstance(item, Mapping):
                if _fields_include_status(item.keys()):
                    return True
                name = item.get("name") or item.get("field") or item.get("key")
                if _fields_include_status(name):
                    return True
            elif _fields_include_status(item):
                return True

    return False


def _first_status_value(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    for keys in (explicit_keys, fallback_keys):
        for context in contexts:
            for key in keys:
                value = _status_text(context.get(key))
                if value:
                    return value
            value = _status_from_changes(context)
            if value:
                return value

    return None


def _status_from_changes(context: Mapping[str, Any]) -> str | None:
    changes = context.get("changes")
    if not isinstance(changes, Mapping):
        return None

    for key, value in changes.items():
        if _normalize_token(key) not in STATUS_FIELD_TOKENS:
            continue

        if isinstance(value, Mapping):
            for new_key in ("newValue", "new_value", "to", "after", "new", "name"):
                text = _status_text(value.get(new_key))
                if text:
                    return text

        text = _status_text(value)
        if text:
            return text

    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _status_text(value.get(key))
            if text:
                return text

    return None


def _first_text(
    contexts: Sequence[Mapping[str, Any]],
    keys: Sequence[str],
    fallback_keys: Sequence[str] = (),
) -> str | None:
    for key_group in (keys, fallback_keys):
        for context in contexts:
            for key in key_group:
                value = context.get(key)
                if isinstance(value, str) and value.strip():
                    return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.strip().lower().startswith(TITLE_PREFIX.lower())


def _normalize_words(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    value = _split_camel_case(value)
    words = re.sub(r"[^a-zA-Z0-9]+", " ", value).strip().lower()
    return re.sub(r"\s+", " ", words) or None


def _normalize_token(value: Any) -> str | None:
    words = _normalize_words(str(value)) if value is not None else None
    return words.replace(" ", "") if words else None


def _split_camel_case(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", value)


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        json.dump(action, sys.stdout, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
