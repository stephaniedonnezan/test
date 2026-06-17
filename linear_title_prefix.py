"""Build Linear issue title updates for issues entering research.

The automation trigger provides issue status-change payloads in a few shapes:
Cursor's flat ``triggerContext`` data, raw Linear webhook data, or a wrapper
around either of those.  This module keeps the decision logic independent from
the delivery mechanism and returns a small action object for the caller to
apply through the Linear API.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {
    "status",
    "state",
    "stateid",
    "statename",
    "workflowstate",
    "workflowstateid",
    "workflowstatename",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when an issue moves to ``to research``.

    The returned action intentionally contains only the data needed by the
    surrounding automation layer:

    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    if _normalize(_first_status_value(contexts)) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    if title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely issue/metadata mappings in precedence order."""

    context: list[Mapping[str, Any]] = []

    trigger_context = _mapping_at(event, "triggerContext")
    if trigger_context:
        context.append(trigger_context)
        trigger_issue = _mapping_at(trigger_context, "issue")
        if trigger_issue:
            context.append(trigger_issue)

    issue = _mapping_at(event, "issue")
    if issue:
        context.append(issue)

    data = _mapping_at(event, "data")
    if data:
        data_issue = _mapping_at(data, "issue")
        if data_issue:
            context.append(data_issue)
        context.append(data)

    context.append(event)
    return context


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    event_names = []
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            value = _text(context.get(key))
            if value:
                event_names.append(_normalize(value))

    if any(name in {"status changed", "state changed", "workflow state changed"} for name in event_names):
        return True

    if any(name in {"issue updated", "updated issue", "update", "updated"} for name in event_names):
        return _status_field_was_updated(contexts)

    return False


def _status_field_was_updated(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "changedFields"):
            fields = context.get(key)
            if isinstance(fields, (list, tuple, set)):
                if any(_normalize_field_name(field) in STATUS_FIELD_NAMES for field in fields):
                    return True
            elif isinstance(fields, Mapping):
                if any(_normalize_field_name(field) in STATUS_FIELD_NAMES for field in fields):
                    return True

        for key in ("changes", "changed", "updatedFrom"):
            changes = context.get(key)
            if isinstance(changes, Mapping):
                if any(_normalize_field_name(field) in STATUS_FIELD_NAMES for field in changes):
                    return True

    return False


def _first_status_value(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "statusName",
        "stateName",
        "workflowStateName",
    )
    value = _first_text(contexts, explicit_keys)
    if value:
        return value

    for context in contexts:
        for key in ("status", "state", "workflowState"):
            value = context.get(key)
            if isinstance(value, Mapping):
                nested_name = _text(value.get("name"))
                if nested_name:
                    return nested_name
            text = _text(value)
            if text:
                return text

        changed_status = _status_value_from_changes(context)
        if changed_status:
            return changed_status

    return None


def _status_value_from_changes(context: Mapping[str, Any]) -> str | None:
    for container_key in ("changes", "changed"):
        changes = context.get(container_key)
        if not isinstance(changes, Mapping):
            continue

        for field, change in changes.items():
            if _normalize_field_name(field) not in STATUS_FIELD_NAMES:
                continue

            if isinstance(change, Mapping):
                for value_key in ("to", "toValue", "newValue", "new", "name"):
                    value = change.get(value_key)
                    if isinstance(value, Mapping):
                        nested_name = _text(value.get("name"))
                        if nested_name:
                            return nested_name
                    text = _text(value)
                    if text:
                        return text
            else:
                text = _text(change)
                if text:
                    return text

    return None


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _text(context.get(key))
            if value:
                return value
    return None


def _mapping_at(context: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    value = context.get(key)
    return value if isinstance(value, Mapping) else None


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _normalize(value: str | None) -> str:
    if not value:
        return ""

    with_camel_breaks = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", with_camel_breaks.casefold()).strip()


def _normalize_field_name(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]+", "", text.casefold())


def main() -> int:
    """Read an event JSON document from stdin and print the title action."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
