"""Build title updates for Linear issues moved into research.

The automation runtime supplies webhook-like payloads in a few shapes. This
module keeps the decision pure and testable: callers pass the event payload and
receive the requested title update, or ``None`` when no update should happen.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action for status changes to research.

    The returned object is intentionally small so the calling automation can map
    it to the actual Linear API update step.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    status = _changed_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _issue_id(contexts)
    title = _issue_title(contexts)
    if not issue_id or not title:
        return None

    if title.lstrip().lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely metadata and issue containers from most to least specific."""

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield trigger_context

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            yield issue
        yield data

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue

    yield event


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    event_names = []
    for context in contexts:
        for key in ("trigger", "action", "type", "event", "eventType", "webhookType"):
            value = context.get(key)
            if isinstance(value, str):
                event_names.append(_normalize(value))

    if any(_is_direct_status_change_name(name) for name in event_names):
        return True

    if any(_is_generic_update_name(name) for name in event_names):
        return _has_status_changed_field(contexts)

    return False


def _is_direct_status_change_name(name: str) -> bool:
    words = set(name.split())
    return "changed" in words and ("status" in words or "state" in words)


def _is_generic_update_name(name: str) -> bool:
    return name in {"update", "updated", "issue update", "issue updated", "updated issue"}


def _has_status_changed_field(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
            "changes",
            "change",
        ):
            value = context.get(key)
            if _contains_status_field(value):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if _is_status_field(str(key)) or _contains_status_field(nested_value):
                return True
        return False

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _is_status_field(value: str) -> bool:
    normalized = _normalize(value)
    return normalized in {"status", "state", "workflow state", "workflow status"}


def _changed_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        status = _first_named_value(
            context,
            (
                "newStatus",
                "new_status",
                "toStatus",
                "to_status",
                "statusName",
                "stateName",
                "workflowStateName",
            ),
        )
        if status:
            return status

    for context in contexts:
        status = _status_from_change_map(context.get("changes"))
        if status:
            return status
        status = _status_from_change_map(context.get("change"))
        if status:
            return status

    for context in contexts:
        status = _first_named_value(context, ("status", "state", "workflowState", "workflow_state"))
        if status:
            return status

    return None


def _status_from_change_map(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for key, change in value.items():
        if not _is_status_field(str(key)):
            continue

        if isinstance(change, Mapping):
            for target_key in ("to", "new", "after", "current", "value"):
                status = _value_name(change.get(target_key))
                if status:
                    return status
        else:
            status = _value_name(change)
            if status:
                return status

    return None


def _first_named_value(context: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        if key in context:
            value = _value_name(context.get(key))
            if value:
                return value
    return None


def _value_name(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value"):
            nested = _value_name(value.get(key))
            if nested:
                return nested
        return None

    text = str(value).strip()
    return text or None


def _issue_id(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        issue_id = _first_named_value(context, ("issueId", "issue_id", "identifier", "key", "id"))
        if issue_id:
            return issue_id
    return None


def _issue_title(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        title = _first_named_value(context, ("title", "issueTitle", "issue_title"))
        if title:
            return title
    return None


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[_\-:/]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    result = build_issue_title_update(payload)
    print(json.dumps(result, indent=2, sort_keys=True) if result else "null")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
