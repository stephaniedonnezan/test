"""Build Linear issue title updates for issues moved to research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
RESEARCH_TITLE_PREFIX = f"{RESEARCH_PREFIX}: "

_TRIGGER_KEYS = ("trigger", "action", "type", "webhookType", "webhook_type")
_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "status",
    "state",
    "workflowState",
    "workflow_state",
)
_TITLE_KEYS = ("title",)
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "id")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
)
_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}
_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_ISSUE_UPDATE_TRIGGERS = {
    "issue updated",
    "updated issue",
    "issue update",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an update-title action when a Linear issue enters research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change(event, contexts):
        return None

    status = _first_string_or_name(contexts, _STATUS_KEYS)
    if _normalize(status) != "to research":
        return None

    issue_id = _first_string_or_name(contexts, _ISSUE_ID_KEYS)
    title = _first_string_or_name(contexts, _TITLE_KEYS)
    if issue_id is None or title is None:
        return None

    issue_id = issue_id.strip()
    title = title.strip()
    if not issue_id or not title or has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{RESEARCH_TITLE_PREFIX}{title}",
    }


def has_research_prefix(title: str) -> bool:
    """Return whether a title already starts with the Cursor research marker."""

    return title.lstrip().lower().startswith(RESEARCH_PREFIX.lower())


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    for key in ("triggerContext", "trigger_context"):
        context = event.get(key)
        if isinstance(context, Mapping):
            contexts.append(context)

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


def _is_status_change(
    event: Mapping[str, Any], contexts: Sequence[Mapping[str, Any]]
) -> bool:
    trigger_values = {_normalize(value) for value in _trigger_values(contexts)}
    if trigger_values & _DIRECT_STATUS_CHANGE_TRIGGERS:
        return True

    if trigger_values & _ISSUE_UPDATE_TRIGGERS:
        return _updated_fields_include_status(event, contexts)

    return False


def _trigger_values(contexts: Sequence[Mapping[str, Any]]) -> Iterable[str]:
    for context in contexts:
        for key in _TRIGGER_KEYS:
            value = context.get(key)
            if isinstance(value, str):
                yield value


def _updated_fields_include_status(
    event: Mapping[str, Any], contexts: Sequence[Mapping[str, Any]]
) -> bool:
    fields: list[str] = []

    for context in contexts:
        for key in _UPDATED_FIELD_KEYS:
            fields.extend(_field_names(context.get(key)))

    changes = event.get("changes")
    if isinstance(changes, Mapping):
        fields.extend(str(key) for key in changes.keys())

    return any(_normalize(field) in _STATUS_FIELD_NAMES for field in fields)


def _field_names(value: Any) -> list[str]:
    if value is None or isinstance(value, (str, bytes)):
        return [value] if isinstance(value, str) else []

    if isinstance(value, Mapping):
        names: list[str] = []
        for key, item in value.items():
            names.append(str(key))
            if isinstance(item, Mapping):
                for name_key in ("name", "field", "key"):
                    item_name = item.get(name_key)
                    if isinstance(item_name, str):
                        names.append(item_name)
        return names

    if isinstance(value, Sequence):
        names = []
        for item in value:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, Mapping):
                for name_key in ("name", "field", "key"):
                    item_name = item.get(name_key)
                    if isinstance(item_name, str):
                        names.append(item_name)
        return names

    return []


def _first_string_or_name(
    contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]
) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, Mapping):
                name = value.get("name")
                if isinstance(name, str):
                    return name
    return None


def _normalize(value: str | None) -> str:
    if not value:
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value).strip())
    return re.sub(r"[\s_-]+", " ", spaced).strip().lower()


def main() -> int:
    payload = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(payload), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
