"""Build Linear issue title updates for issues entering research.

The public entrypoint, :func:`build_issue_title_update`, is intentionally
side-effect free. Automation runners can use its return value to decide
whether to call Linear's issue update API.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
PREFIXED_TITLE_FORMAT = f"{PREFIX}: {{title}}"
ACTION = "update_issue_title"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflowstatus",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research.

    The automation payload shape differs between local tests, Cursor Cloud
    triggers, and Linear webhooks. This function accepts those variants while
    keeping the mutation itself explicit for the caller.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_walk_mappings(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_status(new_status) != TARGET_STATUS:
        return None

    issue = _extract_issue(contexts)
    if issue is None:
        return None

    issue_id, title = issue
    if _has_research_prefix(title):
        return None

    return {
        "action": ACTION,
        "issueId": issue_id,
        "title": PREFIXED_TITLE_FORMAT.format(title=title),
    }


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested in value.values():
            yield from _walk_mappings(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_mappings(item)


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    markers = []
    for context in contexts:
        for key in ("trigger", "triggerType", "webhookType", "action", "type", "eventType"):
            value = context.get(key)
            if isinstance(value, str):
                markers.append(_compact(value))

    if any(_is_direct_status_change_marker(marker) for marker in markers):
        return True

    if any(_is_issue_update_marker(marker) for marker in markers):
        return _has_status_updated_field(contexts) or _has_status_change_entry(contexts)

    return False


def _is_direct_status_change_marker(marker: str) -> bool:
    direct_markers = {
        "statuschanged",
        "statuschange",
        "statechanged",
        "statechange",
        "workflowstatechanged",
        "workflowstatechange",
        "workflowstatuschanged",
        "workflowstatuschange",
    }
    return marker in direct_markers


def _is_issue_update_marker(marker: str) -> bool:
    update_markers = {
        "update",
        "updated",
        "issueupdate",
        "issueupdated",
        "updatedissue",
    }
    return marker in update_markers


def _has_status_updated_field(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            value = context.get(key)
            fields = value if isinstance(value, list) else [value]
            for field in fields:
                if _is_status_field_name(field):
                    return True
    return False


def _has_status_change_entry(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        changes = context.get("changes") or context.get("changed")
        if isinstance(changes, Mapping):
            for key in changes:
                if _is_status_field_name(key):
                    return True
    return False


def _extract_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        explicit = _first_text_value(
            context,
            (
                "newStatus",
                "new_status",
                "newState",
                "new_state",
                "newWorkflowState",
                "new_workflow_state",
                "statusName",
                "status_name",
            ),
        )
        if explicit:
            return explicit

    changed_status = _extract_changed_status(contexts)
    if changed_status:
        return changed_status

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = _coerce_name(context.get(key))
            if value:
                return value

    return None


def _extract_changed_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        changes = context.get("changes") or context.get("changed")
        if not isinstance(changes, Mapping):
            continue

        for field_name, change in changes.items():
            if not _is_status_field_name(field_name):
                continue

            value = _extract_change_target(change)
            if value:
                return value

    return None


def _extract_change_target(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in (
            "to",
            "after",
            "new",
            "newValue",
            "new_value",
            "toValue",
            "to_value",
        ):
            value = _coerce_name(change.get(key))
            if value:
                return value

        nested = _first_text_value(change, ("name", "title"))
        if nested:
            return nested

    return _coerce_name(change)


def _extract_issue(contexts: list[Mapping[str, Any]]) -> tuple[str, str] | None:
    for context in contexts:
        title = _clean_text(context.get("title"))
        if not title:
            continue

        issue_id = _extract_issue_id([context]) or _extract_issue_id(contexts)
        if issue_id:
            return issue_id, title

    return None


def _extract_issue_id(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        issue_id = _first_text_value(context, ("issueId", "issue_id", "identifier", "key", "id"))
        if issue_id:
            return issue_id
    return None


def _first_text_value(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _clean_text(context.get(key))
        if value:
            return value
    return None


def _coerce_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _first_text_value(value, ("name", "title", "label"))
    return _clean_text(value)


def _clean_text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lstrip().lower().startswith(PREFIX.lower())


def _is_status_field_name(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return _compact(value) in _STATUS_FIELD_NAMES


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    return " ".join(_split_words(value))


def _compact(value: str) -> str:
    return "".join(_split_words(value))


def _split_words(value: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    return re.findall(r"[a-z0-9]+", spaced.lower())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
