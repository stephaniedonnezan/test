"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters To Research."""
    if not isinstance(event, Mapping):
        return None

    contexts = _collect_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _new_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("id", "issueId", "issue_id", "identifier", "key"))
    title = _first_text(contexts, ("title", "name"))
    if issue_id is None or title is None:
        return None

    trimmed_title = title.strip()
    if not trimmed_title or _already_prefixed(trimmed_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {trimmed_title}",
    }


def _collect_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = [event]
    for key in ("triggerContext", "data", "issue"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            contexts.append(nested)
            if key != "issue":
                issue = nested.get("issue")
                if isinstance(issue, Mapping):
                    contexts.append(issue)
    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    signals = [
        value
        for context in contexts
        for key in ("trigger", "webhookType", "action", "type", "event")
        if (value := _text(context.get(key))) is not None
    ]

    if any(_normalize(signal) == "status changed" for signal in signals):
        return True

    if not any(_normalize(signal) in {"update", "updated", "issue update", "issue updated"} for signal in signals):
        return False

    return _has_status_changed_field(contexts)


def _has_status_changed_field(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        updated_fields = context.get("updatedFields") or context.get("changedFields")
        if isinstance(updated_fields, str):
            fields = [updated_fields]
        elif isinstance(updated_fields, list):
            fields = [_text(field) for field in updated_fields]
        else:
            fields = []

        if any(_normalize(field) in {"status", "state", "workflow state"} for field in fields if field):
            return True

        changes = context.get("changes") or context.get("changed")
        if isinstance(changes, Mapping):
            if any(_normalize(str(key)) in {"status", "state", "workflow state"} for key in changes):
                return True

    return False


def _new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit = _first_text(
        contexts,
        (
            "newStatus",
            "new_status",
            "statusName",
            "stateName",
            "workflowStateName",
            "toStatus",
            "toState",
        ),
    )
    if explicit is not None:
        return explicit

    for context in contexts:
        for key in ("status", "state", "workflowState"):
            value = context.get(key)
            if isinstance(value, Mapping):
                name = _text(value.get("name"))
                if name is not None:
                    return name
            text = _text(value)
            if text is not None:
                return text

    return None


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            text = _text(context.get(key))
            if text is not None:
                return text
    return None


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _normalize(value: str | None) -> str:
    if value is None:
        return ""
    spaced = _CAMEL_BOUNDARY_RE.sub(" ", value)
    lowered = spaced.lower()
    return _NON_ALNUM_RE.sub(" ", lowered).strip()


def _already_prefixed(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    if action is not None:
        print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
