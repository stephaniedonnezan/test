"""Build Linear issue-title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
PREFIXED_TITLE_TEMPLATE = f"{PREFIX}: {{title}}"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflowstatus",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when an issue moves to "to research"."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change(contexts):
        return None

    status = _new_status(contexts)
    if _normalize(status) != "toresearch":
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(contexts, ("title", "name"))
    if issue_id is None or title is None:
        return None

    title = title.strip()
    if not title or title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": PREFIXED_TITLE_TEMPLATE.format(title=title),
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely payload contexts from most to least specific."""

    contexts: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            contexts.append(issue)
        contexts.append(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        contexts.append(issue)

    contexts.append(event)
    return contexts


def _is_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    if _has_status_changed_trigger(contexts):
        return True

    if not _has_issue_update_trigger(contexts):
        return False

    return any(_updated_fields_include_status(context) for context in contexts)


def _has_status_changed_trigger(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            value = context.get(key)
            normalized = _normalize(value)
            if normalized in {"statuschanged", "statuschange", "statechanged", "statechange"}:
                return True
    return False


def _has_issue_update_trigger(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            normalized = _normalize(context.get(key))
            if normalized in {"issueupdated", "updatedissue", "update", "updated"}:
                return True
    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields")
    if isinstance(updated_fields, (list, tuple, set)):
        for field in updated_fields:
            if _normalize(field) in _STATUS_FIELD_NAMES:
                return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize(field) in _STATUS_FIELD_NAMES for field in changes)

    return False


def _new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    direct_status_keys = (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )

    direct = _first_text(contexts, direct_status_keys)
    if direct is not None:
        return direct

    changed = _status_from_changes(contexts)
    if changed is not None:
        return changed

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflowStatus"):
            value = context.get(key)
            text = _text_value(value)
            if text is not None:
                return text

    return None


def _status_from_changes(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        updated_fields = context.get("updatedFields")
        if isinstance(updated_fields, (list, tuple, set)):
            for field in updated_fields:
                if isinstance(field, Mapping) and _normalize(field.get("name")) in _STATUS_FIELD_NAMES:
                    value = field.get("newValue", field.get("to"))
                    text = _text_value(value)
                    if text is not None:
                        return text

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            for field, change in changes.items():
                if _normalize(field) not in _STATUS_FIELD_NAMES:
                    continue
                if isinstance(change, Mapping):
                    value = change.get("newValue", change.get("to", change.get("after")))
                else:
                    value = change
                text = _text_value(value)
                if text is not None:
                    return text

    return None


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            text = _text_value(context.get(key))
            if text is not None:
                return text
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "id", "identifier", "key"):
            text = _text_value(value.get(key))
            if text is not None:
                return text

    return None


def _normalize(value: Any) -> str:
    text = _text_value(value)
    if text is None:
        return ""

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def main() -> int:
    """Read a JSON event from stdin and write the action JSON, if any."""

    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
