"""Build Linear issue title updates for Cursor research automation events."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters to research.

    The automation receives both flat Cursor trigger payloads and nested Linear
    webhook payloads. This function accepts either shape and returns a structured
    action for the caller to apply, or ``None`` when no title change is needed.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change(contexts):
        return None

    status = _first_text(
        contexts,
        (
            "newStatus",
            "new_status",
            "status",
            "state",
            "workflowState",
            "workflow_state",
        ),
    )
    if _normalize(status) != _normalize(TARGET_STATUS):
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "id", "identifier"))
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = [event]

    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            contexts.extend(_contexts(value))

    return contexts


def _is_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            if _is_direct_status_change_label(context.get(key)):
                return True
            if _is_issue_update_label(context.get(key)) and _mentions_status_field(
                context.get("updatedFields") or context.get("updated_fields")
            ):
                return True

        updated_fields = context.get("updatedFields") or context.get("updated_fields")
        if _mentions_status_field(updated_fields):
            return True

    return False


def _is_direct_status_change_label(value: Any) -> bool:
    normalized = _normalize(_text(value))
    if not normalized:
        return False

    return normalized in {
        "status changed",
        "status change",
        "statuschanged",
        "issue status changed",
    }


def _is_issue_update_label(value: Any) -> bool:
    return _normalize(_text(value)) in {"issue updated", "updated issue", "update"}


def _mentions_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_key(value) in STATUS_FIELDS

    if isinstance(value, Mapping):
        return any(_normalize_key(key) in STATUS_FIELDS for key in value)

    if isinstance(value, (list, tuple, set)):
        return any(_mentions_status_field(item) for item in value)

    return False


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        for context in contexts:
            value = context.get(key)
            text = _text(value)
            if text:
                return text
    return None


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "id", "identifier"):
            text = _text(value.get(key))
            if text:
                return text

    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize(value: str | None) -> str:
    if not value:
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[\W_]+", " ", spaced).strip().casefold()


def _normalize_key(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    return re.sub(r"[\W_]+", "", text).casefold()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is None:
        return 0

    print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
