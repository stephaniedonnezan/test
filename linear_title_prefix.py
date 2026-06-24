"""Build Linear issue title updates for Cursor research automation.

The module is intentionally small: callers provide a webhook/automation payload,
and `build_issue_title_update` returns a structured title-update action when the
payload represents an issue moving to the "to research" status.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = frozenset({"status", "state", "workflowstate", "stateid", "workflowstateid"})
_DIRECT_STATUS_TRIGGERS = frozenset({"status changed", "statuschanged", "status change"})
_UPDATE_TRIGGERS = frozenset({"update", "updated", "issue updated", "updated issue"})


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action for Linear issues moved to "to research".

    The function accepts the flat Cursor automation trigger shape as well as
    nested Linear webhook-like payloads. It does not mutate the input payload.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(contexts)
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": _prefixed_title(title),
    }


def _contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield useful payload contexts from outermost to innermost."""

    yielded: list[int] = []

    def yield_once(value: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(value, Mapping) and id(value) not in yielded:
            yielded.append(id(value))
            yield value

    yield from yield_once(event)

    trigger_context = event.get("triggerContext")
    yield from yield_once(trigger_context)

    data = event.get("data")
    yield from yield_once(data)

    issue = event.get("issue")
    yield from yield_once(issue)

    if isinstance(data, Mapping):
        yield from yield_once(data.get("issue"))
    if isinstance(trigger_context, Mapping):
        yield from yield_once(trigger_context.get("issue"))


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        trigger_values = (
            context.get("trigger"),
            context.get("webhookType"),
            context.get("action"),
            context.get("type"),
            context.get("event"),
            context.get("eventType"),
        )
        normalized_values = {_normalize(value) for value in trigger_values if value is not None}
        if normalized_values & _DIRECT_STATUS_TRIGGERS:
            return True

        if normalized_values & _UPDATE_TRIGGERS and _mentions_status_field(context):
            return True

    return _mentions_status_field_in_changes(contexts)


def _mentions_status_field(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "changedFields", "fields"):
        fields = context.get(key)
        if _contains_status_field(fields):
            return True

    for key in ("changes", "changed", "updatedFrom", "previousValues"):
        changes = context.get(key)
        if isinstance(changes, Mapping) and any(_field_name_mentions_status(field) for field in changes):
            return True

    return False


def _mentions_status_field_in_changes(contexts: list[Mapping[str, Any]]) -> bool:
    return any(_mentions_status_field(context) for context in contexts)


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _field_name_mentions_status(value)
    if isinstance(value, Mapping):
        return any(_field_name_mentions_status(key) for key in value)
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _field_name_mentions_status(value: Any) -> bool:
    normalized = _normalize_key(value)
    return normalized in _STATUS_FIELD_NAMES


def _extract_new_status(contexts: list[Mapping[str, Any]]) -> Any:
    for context in contexts:
        for key in ("newStatus", "new_status", "toStatus", "to_status", "statusName", "stateName"):
            if key in context:
                return context[key]

    for context in contexts:
        status_from_changes = _status_from_changes(context)
        if status_from_changes is not None:
            return status_from_changes

    for context in contexts:
        for key in ("status", "state", "workflowState"):
            value = context.get(key)
            if value is not None:
                return _name_or_value(value)

    return None


def _status_from_changes(context: Mapping[str, Any]) -> Any:
    for key in ("changes", "changed", "updatedFields"):
        changes = context.get(key)
        if isinstance(changes, Mapping):
            for field, value in changes.items():
                if _field_name_mentions_status(field):
                    changed_to = _changed_to_value(value)
                    if changed_to is not None:
                        return changed_to

    return None


def _changed_to_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("to", "new", "newValue", "after", "value", "name"):
            if key in value:
                return _name_or_value(value[key])
    return _name_or_value(value)


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
    return None


def _extract_issue_id(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key"))
    if explicit_id:
        return explicit_id

    # Top-level webhook IDs are often delivery IDs; nested contexts are more
    # likely to represent the actual Linear issue.
    nested_id = _first_text(contexts[1:], ("id",))
    if nested_id:
        return nested_id

    return _first_text(contexts, ("id",))


def _name_or_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "value"):
            if key in value:
                return value[key]
    return value


def _prefixed_title(title: str) -> str:
    stripped = title.strip()
    if re.match(rf"^{re.escape(PREFIX)}\b", stripped, flags=re.IGNORECASE):
        return stripped
    return f"{PREFIX}: {stripped}"


def _normalize(value: Any) -> str:
    if isinstance(value, Mapping):
        value = _name_or_value(value)
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _normalize_key(value: Any) -> str:
    return _normalize(value).replace(" ", "")


def main() -> int:
    """Read a JSON event from stdin and print the title update action, if any."""

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2

    action = build_issue_title_update(payload)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
