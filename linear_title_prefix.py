"""Build Linear issue title updates for Cursor research automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
UPDATE_ACTION = "update_issue_title"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = frozenset({"status", "state", "workflowstate", "workflow_state"})


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update when a Linear issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    contexts = list(_mapping_candidates(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_value(new_status) != TARGET_STATUS:
        return None

    issue_contexts = list(_issue_mapping_candidates(event))
    issue_id = _first_text(issue_contexts, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(issue_contexts, ("title",))
    if issue_id is None or title is None:
        return None

    title = title.strip()
    if not title or title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _mapping_candidates(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield useful payload layers from outermost metadata to nested issue data."""
    yield event

    for key in ("triggerContext", "trigger_context", "webhook", "payload", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            yield from _mapping_candidates(value)


def _issue_mapping_candidates(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield nested issue-like payload layers before outer event metadata."""
    for key in ("triggerContext", "trigger_context", "data", "issue", "payload", "webhook"):
        value = event.get(key)
        if isinstance(value, Mapping):
            yield from _issue_mapping_candidates(value)

    yield event


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    event_markers: list[str] = []
    updated_fields: list[str] = []

    for context in contexts:
        for key in ("trigger", "webhookType", "webhook_type", "action", "type"):
            value = _text_value(context.get(key))
            if value is not None:
                event_markers.append(_normalize_value(value))

        fields = context.get("updatedFields", context.get("updated_fields"))
        updated_fields.extend(_normalized_field_names(fields))

    if any(marker in {"status changed", "status change", "status updated"} for marker in event_markers):
        return True

    if any(marker in {"update", "updated", "issue update", "issue updated", "updated issue"} for marker in event_markers):
        return any(field in STATUS_FIELD_NAMES for field in updated_fields)

    return False


def _extract_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    explicit = _first_text(contexts, explicit_keys)
    if explicit is not None:
        return explicit

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = context.get(key)
            if isinstance(value, Mapping):
                name = _text_value(value.get("name"))
                if name is not None:
                    return name
            else:
                text = _text_value(value)
                if text is not None:
                    return text

    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _text_value(context.get(key))
            if value is not None:
                return value
    return None


def _text_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value if value.strip() else None
    if isinstance(value, (int, float)):
        return str(value)
    return None


def _normalized_field_names(fields: Any) -> list[str]:
    if fields is None:
        return []
    if isinstance(fields, str):
        return [_normalize_field_name(fields)]
    if isinstance(fields, Mapping):
        return [_normalize_field_name(key) for key in fields.keys()]
    if isinstance(fields, Iterable):
        return [_normalize_field_name(field) for field in fields]
    return []


def _normalize_field_name(value: Any) -> str:
    text = _text_value(value)
    if text is None:
        return ""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _normalize_value(value: str | None) -> str | None:
    if value is None:
        return None

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    """Read a JSON event from stdin and print the title update action, if any."""
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
