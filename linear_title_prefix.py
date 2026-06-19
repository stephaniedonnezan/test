"""Build issue-title update actions for Linear research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_SLUGS = {
    "statuschanged",
    "statechanged",
    "workflowstatechanged",
}
_GENERIC_UPDATE_SLUGS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}
_STATUS_FIELD_SLUGS = {
    "status",
    "state",
    "workflowstate",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue enters research.

    The automation trigger has appeared in both flat Cursor payloads and nested
    Linear webhook payloads, so this function accepts both shapes and extracts
    the same minimal fields from each.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_iter_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    status = _extract_new_status(contexts)
    if _normalized_words(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(contexts, ("title", "name"))
    if issue_id is None or title is None:
        return None

    if _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _iter_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely event and issue objects with outer metadata first."""

    trigger_context = _mapping_value(event, "triggerContext")
    if trigger_context is not None:
        yield trigger_context

    yield event

    data = _mapping_value(event, "data")
    if data is not None:
        yield data
        issue = _mapping_value(data, "issue")
        if issue is not None:
            yield issue

    issue = _mapping_value(event, "issue")
    if issue is not None:
        yield issue

    if trigger_context is not None:
        data = _mapping_value(trigger_context, "data")
        if data is not None:
            yield data
            issue = _mapping_value(data, "issue")
            if issue is not None:
                yield issue

        issue = _mapping_value(trigger_context, "issue")
        if issue is not None:
            yield issue


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    if any(_event_slug(context) in _DIRECT_STATUS_CHANGE_SLUGS for context in contexts):
        return True

    has_generic_update = any(_event_slug(context) in _GENERIC_UPDATE_SLUGS for context in contexts)
    return has_generic_update and any(_has_status_updated_field(context) for context in contexts)


def _event_slug(context: Mapping[str, Any]) -> str:
    for key in ("trigger", "webhookType", "webhook_type", "action", "type", "event", "eventType"):
        value = context.get(key)
        if value is not None:
            slug = _normalized_slug(value)
            if slug:
                return slug
    return ""


def _has_status_updated_field(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = context.get(key)
        if _contains_status_field(fields):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_is_status_field_name(key) for key in changes)

    return False


def _contains_status_field(fields: Any) -> bool:
    if isinstance(fields, str):
        return _is_status_field_name(fields)

    if isinstance(fields, Mapping):
        names = (
            fields.get("field"),
            fields.get("fieldName"),
            fields.get("name"),
            fields.get("key"),
        )
        return any(_is_status_field_name(name) for name in names)

    if isinstance(fields, Iterable):
        return any(_contains_status_field(field) for field in fields)

    return False


def _is_status_field_name(value: Any) -> bool:
    return _normalized_slug(value) in _STATUS_FIELD_SLUGS


def _extract_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit_status = _first_text(
        contexts,
        (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "newState",
            "new_state",
            "statusName",
            "status_name",
            "stateName",
            "state_name",
            "workflowStateName",
            "workflow_state_name",
        ),
    )
    if explicit_status is not None:
        return explicit_status

    changed_status = _status_from_changes(contexts)
    if changed_status is not None:
        return changed_status

    return _first_text(contexts, ("status", "state", "workflowState", "workflow_state"))


def _status_from_changes(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        changes = context.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for field_name, value in changes.items():
            if not _is_status_field_name(field_name):
                continue

            status = _text_from_change_value(value)
            if status is not None:
                return status

    return None


def _text_from_change_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("new", "to", "after", "newValue", "new_value", "value", "name", "title"):
            text = _text_value(value.get(key))
            if text is not None:
                return text
    return _text_value(value)


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        for context in contexts:
            text = _text_value(context.get(key))
            if text is not None:
                return text
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value", "id", "identifier"):
            text = _text_value(value.get(key))
            if text is not None:
                return text
        return None

    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _mapping_value(mapping: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else None


def _has_title_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(TITLE_PREFIX)}\b", title, re.IGNORECASE) is not None


def _normalized_words(value: Any) -> str:
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value or ""))
    words = re.sub(r"[^A-Za-z0-9]+", " ", words).strip().lower()
    return re.sub(r"\s+", " ", words)


def _normalized_slug(value: Any) -> str:
    return _normalized_words(value).replace(" ", "")


def main() -> int:
    """Read a JSON event from stdin and print the generated action, if any."""

    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
