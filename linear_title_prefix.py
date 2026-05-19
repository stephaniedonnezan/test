"""Build Linear issue title updates for Cursor research automation.

The module intentionally has no Linear client dependency.  It converts an
automation/webhook payload into a small action object that a caller can execute.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {
    "status",
    "state",
    "workflow_state",
    "workflow_status",
    "state_id",
    "status_id",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to to research."""

    if not isinstance(event, Mapping):
        return None

    context = _merged_context(event)
    if not _is_status_change_event(context):
        return None

    new_status = _extract_new_status(context)
    if _normalize_status(new_status) != _normalize_status(TARGET_STATUS):
        return None

    issue_id = _extract_issue_id(context)
    title = _extract_title(context)
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _merged_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common automation and Linear issue payload layers.

    Later updates win, so explicit top-level automation fields such as
    ``newStatus`` are preferred over nested issue state that may still be stale.
    """

    context: dict[str, Any] = {}

    for key in ("issue", "data"):
        value = event.get(key)
        if isinstance(value, Mapping):
            context.update(value)
            nested_issue = value.get("issue")
            if isinstance(nested_issue, Mapping):
                context.update(nested_issue)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        context.update(trigger_context)
        nested_issue = trigger_context.get("issue")
        if isinstance(nested_issue, Mapping):
            context.update(nested_issue)

    context.update(event)
    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        value
        for key in ("trigger", "webhookType", "action", "type")
        if (value := context.get(key)) is not None
    ]

    normalized_triggers = {_normalize_token(value) for value in trigger_values}
    if normalized_triggers & {"statuschanged", "statuschange", "statusupdated"}:
        return True

    if normalized_triggers & {"update", "updated", "issueupdated", "updatedissue"}:
        return _changed_fields_include_status(context)

    return False


def _changed_fields_include_status(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updatedFieldNames", "changedFields"):
        if _field_names_include_status(context.get(key)):
            return True

    updated_from = context.get("updatedFrom")
    if isinstance(updated_from, Mapping):
        return any(_normalize_field_name(field) in STATUS_FIELDS for field in updated_from)

    return False


def _field_names_include_status(value: Any) -> bool:
    if isinstance(value, str):
        fields: Iterable[Any] = re.split(r"[, ]+", value)
    elif isinstance(value, Mapping):
        fields = value.keys()
    elif isinstance(value, Iterable):
        fields = value
    else:
        return False

    return any(_normalize_field_name(field) in STATUS_FIELDS for field in fields)


def _extract_new_status(context: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "statusName",
        "stateName",
        "workflowStateName",
        "status",
    ):
        status = _as_name(context.get(key))
        if status:
            return status

    for key in ("state", "workflowState"):
        status = _as_name(context.get(key))
        if status:
            return status

    return None


def _extract_issue_id(context: Mapping[str, Any]) -> str | None:
    for key in ("issueId", "issue_id", "identifier", "id"):
        value = context.get(key)
        if value is None:
            continue
        issue_id = str(value).strip()
        if issue_id:
            return issue_id
    return None


def _extract_title(context: Mapping[str, Any]) -> str | None:
    value = context.get("title")
    if value is None:
        return None

    title = str(value).strip()
    return title or None


def _as_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title"):
            name = value.get(key)
            if name is not None and str(name).strip():
                return str(name).strip()
        return None

    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _normalize_status(value: Any) -> str:
    text = _camel_to_words(str(value or ""))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _normalize_token(value: Any) -> str:
    text = _camel_to_words(str(value or ""))
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _normalize_field_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9_]+", "", _camel_to_words(str(value or "")).lower()).replace(
        " ",
        "_",
    )


def _camel_to_words(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    """Read a JSON event from stdin and print the generated action, if any."""

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
