"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    fields = _collect_fields(event)
    if not _is_status_change(event, fields):
        return None

    status = _first_text(
        fields,
        (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "status",
            "state",
            "workflowState",
            "workflow_state",
        ),
    )
    if _normalize(status) != TARGET_STATUS:
        return None

    title = _first_text(fields, ("title", "name", "issueTitle", "issue_title"))
    issue_id = _first_text(fields, ("issueId", "issue_id", "id", "identifier", "key"))
    if not title or not issue_id:
        return None

    if title.lower().startswith(PREFIX.lower()):
        new_title = title
    else:
        new_title = f"{PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": new_title,
    }


def _collect_fields(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Cursor/Linear webhook wrappers with outer fields winning."""
    fields: dict[str, Any] = {}
    for source in _iter_contexts(event):
        fields.update({key: value for key, value in source.items() if value is not None})
    return fields


def _iter_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    for key in ("issue",):
        value = event.get(key)
        if isinstance(value, Mapping):
            yield from _iter_contexts(value)
            yield value

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            yield from _iter_contexts(issue)
            yield issue
        yield data

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield from _iter_contexts(trigger_context)
        yield trigger_context

    yield event


def _is_status_change(event: Mapping[str, Any], fields: Mapping[str, Any]) -> bool:
    direct_event_names = (
        "status changed",
        "status change",
        "status updated",
        "state changed",
        "workflow state changed",
    )
    event_name_keys = ("trigger", "webhookType", "webhook_type", "action", "type")
    if any(_normalize(fields.get(key)) in direct_event_names for key in event_name_keys):
        return True

    generic_update_names = {"update", "updated", "issue update", "issue updated", "updated issue"}
    if any(_normalize(fields.get(key)) in generic_update_names for key in event_name_keys):
        return _updated_status_fields(fields) or _updated_status_fields(event)

    return False


def _updated_status_fields(source: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields"):
        value = source.get(key)
        if isinstance(value, str):
            if _normalize(value) in STATUS_FIELDS:
                return True
        elif isinstance(value, Iterable):
            for item in value:
                if _normalize(item) in STATUS_FIELDS:
                    return True

    changes = source.get("changes") or source.get("changedFields") or source.get("changed_fields")
    if isinstance(changes, Mapping):
        return any(_normalize(key) in STATUS_FIELDS for key in changes)

    return False


def _first_text(fields: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = fields.get(key)
        text = _text_value(value)
        if text:
            return text
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "id", "key"):
            text = _text_value(value.get(key))
            if text:
                return text
        return None

    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    return None


def _normalize(value: Any) -> str:
    text = _text_value(value)
    if not text:
        return ""
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    if result is not None:
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
