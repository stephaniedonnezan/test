"""Build Linear issue title updates for the Cursor research status automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflow state", "workflow status"}
STATUS_CHANGE_TRIGGERS = {"status changed", "status change", "statuschanged"}
UPDATE_TRIGGERS = {"update", "updated", "issue updated", "updated issue"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to To Research.

    Cursor automation payloads are flat dictionaries under ``triggerContext``;
    Linear webhook payloads are often nested under ``data.issue``. The handler
    accepts both shapes and keeps external side effects out of this module.
    """

    if not isinstance(event, Mapping):
        return None

    flattened = _flatten_event(event)
    issue = _issue_payload(event)

    if not _is_status_change_event(flattened, event):
        return None

    new_status = _first_text(
        flattened.get("newStatus"),
        flattened.get("new_status"),
        flattened.get("status"),
        _name_from(flattened.get("state")),
        _name_from(flattened.get("workflowState")),
        _name_from(issue.get("state")),
        _name_from(issue.get("workflowState")),
        issue.get("status"),
    )
    if _normalize_words(new_status) != _normalize_words(TARGET_STATUS):
        return None

    issue_id = _first_text(
        issue.get("id"),
        issue.get("issueId"),
        issue.get("issue_id"),
        issue.get("identifier"),
        flattened.get("issueId"),
        flattened.get("issue_id"),
        flattened.get("identifier"),
        flattened.get("id"),
    )
    title = _first_text(issue.get("title"), flattened.get("title"))
    if issue_id is None or title is None:
        return None

    clean_title = title.strip()
    if not clean_title:
        return None

    updated_title = clean_title if _has_prefix(clean_title) else f"{TITLE_PREFIX}: {clean_title}"
    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": updated_title,
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge known envelope dictionaries, with outer fields taking precedence."""

    flattened: dict[str, Any] = {}
    for key in ("data", "issue", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            flattened.update(value)
    flattened.update(event)
    return flattened


def _issue_payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            return issue
        return data

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        return issue

    return event


def _is_status_change_event(flattened: Mapping[str, Any], event: Mapping[str, Any]) -> bool:
    trigger_values = (
        flattened.get("trigger"),
        flattened.get("webhookType"),
        flattened.get("action"),
        flattened.get("type"),
    )
    normalized_triggers = {_normalize_words(value) for value in trigger_values if value}
    if normalized_triggers & STATUS_CHANGE_TRIGGERS:
        return True

    if normalized_triggers & UPDATE_TRIGGERS:
        return (
            _updated_fields_include_status(flattened.get("updatedFields"))
            or _updated_fields_include_status(flattened.get("updated_fields"))
            or _updated_from_includes_status(flattened.get("updatedFrom"))
        )

    return _updated_from_includes_status(flattened.get("updatedFrom")) or (
        _normalize_words(event.get("webhookType")) == "issue"
        and _updated_fields_include_status(flattened.get("updatedFields"))
    )


def _updated_from_includes_status(updated_from: Any) -> bool:
    if isinstance(updated_from, Mapping):
        return any(_normalize_words(key) in STATUS_FIELDS for key in updated_from)
    return False


def _updated_fields_include_status(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        fields: Iterable[Any] = re.split(r"[\s,]+", value)
    elif isinstance(value, Mapping):
        fields = value.keys()
    elif isinstance(value, Iterable):
        fields = value
    else:
        return False

    return any(_normalize_words(field) in STATUS_FIELDS for field in fields)


def _name_from(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _first_text(value.get("name"), value.get("title"))
    return _first_text(value)


def _first_text(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[^a-z0-9]+", " ", separated.casefold()).strip()


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
