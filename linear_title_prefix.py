"""Build Linear issue-title updates for research status transitions.

The automation host is responsible for applying the returned action to Linear.
This module only decides whether a webhook-like payload needs a title update.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS_TOKEN = "toresearch"
STATUS_FIELD_KEYS = ("status", "state", "workflowState", "workflow_state")
EXPLICIT_STATUS_KEYS = (
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
    "toWorkflowState",
    "to_workflow_state",
)
STATUS_CHANGE_KEYS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update action when an issue moves to to research.

    The returned shape is intentionally small so callers can translate it to
    their Linear client of choice:

    {"action": "update_issue_title", "issueId": "...", "title": "..."}
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if not _is_target_status(new_status):
        return None

    issue_id = _extract_issue_id(contexts)
    title = _extract_title(contexts)
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if not clean_title:
        return None

    if clean_title.casefold().startswith(PREFIX.casefold()):
        prefixed_title = clean_title
    else:
        prefixed_title = f"{PREFIX}: {clean_title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": prefixed_title,
    }


def _contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely metadata and issue objects from flat and nested payloads."""

    seen: set[int] = set()

    def add(value: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            yield value

    yield from add(event.get("triggerContext"))
    yield from add(event)
    yield from add(event.get("issue"))

    data = event.get("data")
    yield from add(data)
    if isinstance(data, Mapping):
        yield from add(data.get("issue"))

    webhook = event.get("webhook")
    yield from add(webhook)
    if isinstance(webhook, Mapping):
        yield from add(webhook.get("data"))
        issue = webhook.get("issue")
        yield from add(issue)


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = []
    for context in contexts:
        for key in ("trigger", "event", "eventType", "webhookType", "action", "type"):
            value = context.get(key)
            if isinstance(value, str):
                trigger_values.append(value)

    if any(_is_direct_status_change(value) for value in trigger_values):
        return True

    if _has_status_change_details(contexts):
        return any(_is_update_event(value) for value in trigger_values) or not trigger_values

    return False


def _is_direct_status_change(value: str) -> bool:
    token = _normalize_token(value)
    return any(
        marker in token
        for marker in (
            "statuschanged",
            "statuschange",
            "statechanged",
            "statechange",
            "workflowstatechanged",
            "workflowstatechange",
        )
    )


def _is_update_event(value: str) -> bool:
    token = _normalize_token(value)
    return token in {"update", "updated", "issueupdate", "issueupdated", "updatedissue"}


def _has_status_change_details(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        updated_fields = context.get("updatedFields", context.get("updated_fields"))
        if _contains_status_field(updated_fields):
            return True

        changes = context.get("changes")
        if _contains_status_field(changes):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in STATUS_CHANGE_KEYS

    if isinstance(value, Mapping):
        return any(_normalize_field_name(key) in STATUS_CHANGE_KEYS for key in value)

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _extract_new_status(contexts: list[Mapping[str, Any]]) -> Any:
    for context in contexts:
        for key in EXPLICIT_STATUS_KEYS:
            if key in context:
                return context[key]

    changed_status = _extract_status_from_changes(contexts)
    if changed_status is not None:
        return changed_status

    for context in contexts:
        for key in STATUS_FIELD_KEYS:
            if key in context:
                return context[key]

    return None


def _extract_status_from_changes(contexts: list[Mapping[str, Any]]) -> Any:
    for context in contexts:
        for container_key in ("changes", "updatedFields", "updated_fields"):
            container = context.get(container_key)
            if not isinstance(container, Mapping):
                continue

            for key, value in container.items():
                if _normalize_field_name(key) not in STATUS_CHANGE_KEYS:
                    continue

                if isinstance(value, Mapping):
                    for status_key in (
                        "to",
                        "new",
                        "after",
                        "newValue",
                        "new_value",
                        "toValue",
                        "to_value",
                        "name",
                    ):
                        if status_key in value:
                            return value[status_key]

                return value

    return None


def _extract_issue_id(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in ("issueId", "issue_id", "identifier", "key"):
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value

    for context in contexts:
        value = context.get("id")
        if isinstance(value, str) and value.strip() and "title" in context:
            return value

    return None


def _extract_title(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        value = context.get("title")
        if isinstance(value, str) and value.strip():
            return value

    return None


def _is_target_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key in ("name", "status", "title", "label"):
            if key in value and _is_target_status(value[key]):
                return True
        return False

    if isinstance(value, str):
        return _normalize_token(value) == TARGET_STATUS_TOKEN

    return False


def _normalize_token(value: str) -> str:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", "", spaced.casefold())


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _normalize_token(value)


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        json.dump(update, sys.stdout, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
